"""Tests for backend/storage/extraction.py and the extraction tables in db.py
(extraction T4). Offline, temp DB per test, no clock sleeping. Content used in
rows is obviously synthetic."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from backend.ai.client.operations import Operation
from backend.ai.client.results import StructuredCallResult, to_audit_log_entry
from backend.storage import devices as devices_storage
from backend.storage import extraction as ex
from backend.storage.db import get_connection, init_schema

T0 = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "t4.db"


@pytest.fixture()
def conn(db_path):
    c = get_connection(db_path)
    yield c
    c.close()


def _device(conn) -> str:
    token = devices_storage.register_device(conn).device_token
    return devices_storage.verify_device_token(conn, token)


def _document(conn, device_id: str, name: str = "doc.pdf") -> str:
    import uuid

    document_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO documents (document_id, device_id, original_name, stored_filename, "
        "document_type, processing_state, page_count, content_hash, size_bytes, received_at) "
        "VALUES (?, ?, ?, ?, 'unspecified', 'RECEIVED', 1, 'h', 1, '2026-09-29T10:00:00Z')",
        (document_id, device_id, name, f"{document_id}.pdf"),
    )
    conn.commit()
    return document_id


def _running_job(conn, device_id, document_id) -> str:
    job = ex.create_job(conn, device_id=device_id, document_id=document_id, now=T0).job
    ex.update_job_status(
        conn, device_id=device_id, job_id=job.job_id, new_status=ex.JOB_RUNNING, now=T0
    )
    return job.job_id


def _ref(text="SYNTHETIC line") -> ex.NewSourceReference:
    return ex.NewSourceReference(page=0, bbox_pt=(40.0, 100.0, 300.0, 115.0), verbatim_text=text)


def _proposal(ref, **kw) -> ex.NewProposal:
    base = dict(
        proposed_type="MEDICATION",
        proposed_fields={"medicineName": "Tab. Sampledrug", "doseText": "10mg"},
        original_text="Medication: Tab. Sampledrug 10mg",
        source_reference_id=ref.source_reference_id,
        page=0,
        confidence=0.9,
        review_state="PROPOSED",
        verbatim_check="PASSED",
    )
    base.update(kw)
    return ex.NewProposal(**base)


def _count(conn, table) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# --- schema ------------------------------------------------------------------

_OLD_SCHEMA = [
    "CREATE TABLE devices (device_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, issued_at TEXT NOT NULL)",
    "CREATE TABLE pairing_codes (code_hash TEXT PRIMARY KEY, device_id TEXT NOT NULL, created_at TEXT NOT NULL, "
    "expires_at TEXT NOT NULL, FOREIGN KEY (device_id) REFERENCES devices (device_id))",
    "CREATE TABLE documents (document_id TEXT PRIMARY KEY, device_id TEXT NOT NULL, original_name TEXT NOT NULL, "
    "stored_filename TEXT NOT NULL UNIQUE, document_type TEXT NOT NULL, processing_state TEXT NOT NULL, "
    "page_count INTEGER NOT NULL, content_hash TEXT NOT NULL, size_bytes INTEGER NOT NULL, received_at TEXT NOT NULL, "
    "FOREIGN KEY (device_id) REFERENCES devices (device_id))",
]


def test_init_schema_is_idempotent(conn):
    before = conn.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall()
    init_schema(conn)
    init_schema(conn)
    assert conn.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall() == before
    names = {r[0] for r in before}
    assert {"devices", "pairing_codes", "documents", "extraction_jobs", "source_references",
            "proposals", "ai_request_log"} <= names


def test_preexisting_database_gains_new_tables_and_keeps_its_rows(tmp_path):
    path = tmp_path / "old.db"
    raw = sqlite3.connect(str(path))
    for ddl in _OLD_SCHEMA:
        raw.execute(ddl)
    raw.execute("INSERT INTO devices VALUES ('d1', 'hash', '2026-01-01T00:00:00Z')")
    raw.commit()
    raw.close()

    c = get_connection(path)  # runs init_schema over the old database
    try:
        assert c.execute("SELECT device_id FROM devices").fetchall() == [("d1",)]
        assert _count(c, "extraction_jobs") == 0
        assert _count(c, "proposals") == 0
    finally:
        c.close()


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO extraction_jobs (job_id, document_id, device_id, status, created_at) "
            "VALUES ('j', 'no-such-doc', 'no-such-device', 'PENDING', '2026-09-29T10:00:00Z')"
        )


def test_ai_request_log_has_exactly_the_content_free_columns(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(ai_request_log)")]
    assert set(cols) == {
        "log_id", "job_id", "regime", "operation", "schema_version", "model",
        "latency_ms", "validation_outcome", "retry_count", "error_class", "created_at",
    }
    for c in cols:
        assert not any(w in c for w in ("prompt", "response", "text", "body", "content", "output"))


# --- idempotency ---------------------------------------------------------------


def test_second_create_while_pending_returns_existing_job(conn):
    d = _device(conn)
    doc = _document(conn, d)
    first = ex.create_job(conn, device_id=d, document_id=doc, now=T0)
    second = ex.create_job(conn, device_id=d, document_id=doc, now=T0)
    assert first.created is True and first.job.status == ex.JOB_PENDING
    assert second.created is False
    assert second.job.job_id == first.job.job_id
    assert _count(conn, "extraction_jobs") == 1


def test_second_create_while_running_returns_existing_job(conn):
    d = _device(conn)
    doc = _document(conn, d)
    job_id = _running_job(conn, d, doc)
    again = ex.create_job(conn, device_id=d, document_id=doc)
    assert again.created is False and again.job.job_id == job_id
    assert again.job.status == ex.JOB_RUNNING


@pytest.mark.parametrize("terminal", [ex.JOB_COMPLETED, ex.JOB_FAILED])
def test_new_job_can_be_created_after_a_terminal_state(conn, terminal):
    d = _device(conn)
    doc = _document(conn, d)
    job_id = _running_job(conn, d, doc)
    ex.update_job_status(conn, device_id=d, job_id=job_id, new_status=terminal)
    fresh = ex.create_job(conn, device_id=d, document_id=doc)
    assert fresh.created is True and fresh.job.job_id != job_id
    assert _count(conn, "extraction_jobs") == 2


def test_jobs_for_different_documents_do_not_collide(conn):
    d = _device(conn)
    a, b = _document(conn, d), _document(conn, d)
    assert ex.create_job(conn, device_id=d, document_id=a).created
    assert ex.create_job(conn, device_id=d, document_id=b).created


def test_partial_unique_index_rejects_raw_duplicate_active_insert(conn):
    d = _device(conn)
    doc = _document(conn, d)
    ex.create_job(conn, device_id=d, document_id=doc)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO extraction_jobs (job_id, document_id, device_id, status, created_at) "
            "VALUES ('raw-dup', ?, ?, 'RUNNING', '2026-09-29T10:00:00Z')",
            (doc, d),
        )
    conn.rollback()


def test_partial_unique_index_allows_a_raw_insert_after_terminal(conn):
    d = _device(conn)
    doc = _document(conn, d)
    job_id = _running_job(conn, d, doc)
    ex.update_job_status(conn, device_id=d, job_id=job_id, new_status=ex.JOB_FAILED)
    conn.execute(
        "INSERT INTO extraction_jobs (job_id, document_id, device_id, status, created_at) "
        "VALUES ('raw-ok', ?, ?, 'PENDING', '2026-09-29T10:00:00Z')",
        (doc, d),
    )
    conn.commit()


def test_create_job_for_unknown_document_is_not_found(conn):
    d = _device(conn)
    with pytest.raises(ex.DocumentNotFoundError):
        ex.create_job(conn, device_id=d, document_id="nope")


# --- transitions -----------------------------------------------------------------


def test_legal_transition_chain_sets_timestamps_and_metadata(conn):
    d = _device(conn)
    doc = _document(conn, d)
    job = ex.create_job(conn, device_id=d, document_id=doc, now=T0).job
    assert job.started_at is None and job.finished_at is None

    running = ex.update_job_status(
        conn, device_id=d, job_id=job.job_id, new_status=ex.JOB_RUNNING, now=T0 + timedelta(seconds=1)
    )
    assert running.started_at == T0 + timedelta(seconds=1) and running.finished_at is None

    done = ex.update_job_status(
        conn, device_id=d, job_id=job.job_id, new_status=ex.JOB_FAILED,
        now=T0 + timedelta(seconds=5), error_class="SchemaValidationError",
        retry_count=2, model="m", schema_version="1.0.0",
    )
    assert done.status == ex.JOB_FAILED
    assert done.finished_at == T0 + timedelta(seconds=5)
    assert (done.error_class, done.retry_count, done.model, done.schema_version) == (
        "SchemaValidationError", 2, "m", "1.0.0")


def test_running_to_completed_is_legal(conn):
    d = _device(conn)
    job_id = _running_job(conn, d, _document(conn, d))
    assert ex.update_job_status(
        conn, device_id=d, job_id=job_id, new_status=ex.JOB_COMPLETED).status == ex.JOB_COMPLETED


def test_pending_to_failed_is_legal_for_a_job_that_never_started(conn):
    d = _device(conn)
    job = ex.create_job(conn, device_id=d, document_id=_document(conn, d)).job
    assert ex.update_job_status(
        conn, device_id=d, job_id=job.job_id, new_status=ex.JOB_FAILED).status == ex.JOB_FAILED


@pytest.mark.parametrize(
    "start,target",
    [
        (ex.JOB_PENDING, ex.JOB_COMPLETED),
        (ex.JOB_PENDING, ex.JOB_PENDING),
        (ex.JOB_RUNNING, ex.JOB_PENDING),
        (ex.JOB_RUNNING, ex.JOB_RUNNING),
        (ex.JOB_COMPLETED, ex.JOB_RUNNING),
        (ex.JOB_COMPLETED, ex.JOB_FAILED),
        (ex.JOB_FAILED, ex.JOB_RUNNING),
        (ex.JOB_FAILED, ex.JOB_COMPLETED),
        (ex.JOB_PENDING, "BOGUS"),
    ],
)
def test_illegal_transitions_are_refused_and_change_nothing(conn, start, target):
    d = _device(conn)
    doc = _document(conn, d)
    job_id = ex.create_job(conn, device_id=d, document_id=doc).job.job_id
    path = {
        ex.JOB_PENDING: [],
        ex.JOB_RUNNING: [ex.JOB_RUNNING],
        ex.JOB_COMPLETED: [ex.JOB_RUNNING, ex.JOB_COMPLETED],
        ex.JOB_FAILED: [ex.JOB_RUNNING, ex.JOB_FAILED],
    }[start]
    for step in path:
        ex.update_job_status(conn, device_id=d, job_id=job_id, new_status=step)

    with pytest.raises(ex.IllegalJobTransitionError):
        ex.update_job_status(conn, device_id=d, job_id=job_id, new_status=target)
    assert ex.get_job(conn, device_id=d, job_id=job_id).status == start


def test_update_unknown_job_is_not_found(conn):
    d = _device(conn)
    with pytest.raises(ex.JobNotFoundError):
        ex.update_job_status(conn, device_id=d, job_id="nope", new_status=ex.JOB_RUNNING)


# --- restart sweep -----------------------------------------------------------------


def test_sweep_fails_only_pending_and_running_jobs(conn):
    d1, d2 = _device(conn), _device(conn)
    doc_p, doc_r, doc_c, doc_f, doc_o = (_document(conn, d) for d in (d1, d1, d1, d1, d2))

    pending = ex.create_job(conn, device_id=d1, document_id=doc_p).job.job_id
    running = _running_job(conn, d1, doc_r)
    completed = _running_job(conn, d1, doc_c)
    ex.update_job_status(conn, device_id=d1, job_id=completed, new_status=ex.JOB_COMPLETED)
    failed = _running_job(conn, d1, doc_f)
    ex.update_job_status(conn, device_id=d1, job_id=failed, new_status=ex.JOB_FAILED, error_class="X")
    other_running = _running_job(conn, d2, doc_o)  # another device: swept too (process-level)

    changed = ex.sweep_interrupted_jobs(conn, now=T0 + timedelta(minutes=1))
    assert sorted(changed) == sorted([(pending, doc_p), (running, doc_r), (other_running, doc_o)])

    for jid, dev in ((pending, d1), (running, d1), (other_running, d2)):
        j = ex.get_job(conn, device_id=dev, job_id=jid)
        assert j.status == ex.JOB_FAILED and j.error_class == ex.ERROR_CLASS_SERVER_RESTART
        assert j.finished_at == T0 + timedelta(minutes=1)
    assert ex.get_job(conn, device_id=d1, job_id=completed).status == ex.JOB_COMPLETED
    assert ex.get_job(conn, device_id=d1, job_id=completed).error_class is None
    assert ex.get_job(conn, device_id=d1, job_id=failed).error_class == "X"
    assert ex.sweep_interrupted_jobs(conn) == []  # nothing left to sweep

    # A swept document can be extracted again.
    assert ex.create_job(conn, device_id=d1, document_id=doc_r).created


# --- atomic persist ----------------------------------------------------------------


def test_persist_writes_everything_and_completes_the_job(conn):
    d = _device(conn)
    doc = _document(conn, d)
    job_id = _running_job(conn, d, doc)
    r1, r2 = _ref("line one"), _ref("line two")
    p1 = _proposal(r1)
    p2 = _proposal(r2, review_state="UNCLEAR", verbatim_check="FAILED", source_status="CURRENT",
                   proposed_fields={"medicineName": "Tab. Other \u2013 x"})

    job = ex.persist_extraction_results(
        conn, device_id=d, job_id=job_id, source_references=[r1, r2], proposals=[p1, p2],
        model="m", schema_version="1.0.0", retry_count=1, now=T0 + timedelta(seconds=9),
    )
    assert job.status == ex.JOB_COMPLETED and job.finished_at == T0 + timedelta(seconds=9)
    assert (job.model, job.schema_version, job.retry_count) == ("m", "1.0.0", 1)

    got = ex.list_proposals(conn, device_id=d, document_id=doc)
    assert [p.proposal_id for p in got] == [p1.proposal_id, p2.proposal_id]
    assert got[0].proposed_fields == p1.proposed_fields and got[0].job_id == job_id
    assert got[1].review_state == "UNCLEAR" and got[1].source_status == "CURRENT"
    assert got[1].proposed_fields["medicineName"] == "Tab. Other \u2013 x"  # stored verbatim
    assert got[0].reviewed_at is None and got[0].edited_fields is None
    assert ex.get_proposal(conn, device_id=d, proposal_id=p1.proposal_id) == got[0]

    refs = ex.list_source_references(conn, device_id=d, document_id=doc)
    assert [r.verbatim_text for r in refs] == ["line one", "line two"]
    assert refs[0].bbox_pt == (40.0, 100.0, 300.0, 115.0) and refs[0].document_id == doc


def _assert_nothing_persisted(conn, d, job_id, status=ex.JOB_RUNNING):
    assert _count(conn, "proposals") == 0
    assert _count(conn, "source_references") == 0
    assert ex.get_job(conn, device_id=d, job_id=job_id).status == status
    assert ex.get_job(conn, device_id=d, job_id=job_id).finished_at is None


def test_failure_mid_write_rolls_everything_back_duplicate_id(conn):
    d = _device(conn)
    job_id = _running_job(conn, d, _document(conn, d))
    r = _ref()
    good = _proposal(r)
    dup = _proposal(r, proposal_id=good.proposal_id)  # 2nd insert violates the primary key
    with pytest.raises(sqlite3.IntegrityError):
        ex.persist_extraction_results(
            conn, device_id=d, job_id=job_id, source_references=[r], proposals=[good, dup])
    _assert_nothing_persisted(conn, d, job_id)


def test_failure_mid_write_rolls_everything_back_unserializable_field(conn):
    d = _device(conn)
    job_id = _running_job(conn, d, _document(conn, d))
    r = _ref()
    with pytest.raises(TypeError):
        ex.persist_extraction_results(
            conn, device_id=d, job_id=job_id, source_references=[r],
            proposals=[_proposal(r), _proposal(r, proposed_fields={"x": object()})])
    _assert_nothing_persisted(conn, d, job_id)


def test_failure_mid_write_rolls_everything_back_dangling_source_reference(conn):
    d = _device(conn)
    job_id = _running_job(conn, d, _document(conn, d))
    r = _ref()
    bad = _proposal(r, source_reference_id="not-a-real-ref")
    with pytest.raises(sqlite3.IntegrityError):
        ex.persist_extraction_results(
            conn, device_id=d, job_id=job_id, source_references=[r], proposals=[_proposal(r), bad])
    _assert_nothing_persisted(conn, d, job_id)


def test_persist_on_a_job_that_is_not_running_rolls_back(conn):
    d = _device(conn)
    job_id = ex.create_job(conn, device_id=d, document_id=_document(conn, d)).job.job_id  # PENDING
    r = _ref()
    with pytest.raises(ex.IllegalJobTransitionError):
        ex.persist_extraction_results(
            conn, device_id=d, job_id=job_id, source_references=[r], proposals=[_proposal(r)])
    _assert_nothing_persisted(conn, d, job_id, status=ex.JOB_PENDING)


def test_persist_can_be_retried_after_a_rolled_back_failure(conn):
    d = _device(conn)
    doc = _document(conn, d)
    job_id = _running_job(conn, d, doc)
    r = _ref()
    with pytest.raises(TypeError):
        ex.persist_extraction_results(
            conn, device_id=d, job_id=job_id, source_references=[r],
            proposals=[_proposal(r, proposed_fields={"x": object()})])
    ex.persist_extraction_results(
        conn, device_id=d, job_id=job_id, source_references=[r], proposals=[_proposal(r)])
    assert len(ex.list_proposals(conn, device_id=d, document_id=doc)) == 1


def test_persist_with_no_proposals_completes_the_job(conn):
    d = _device(conn)
    doc = _document(conn, d)
    job_id = _running_job(conn, d, doc)
    job = ex.persist_extraction_results(
        conn, device_id=d, job_id=job_id, source_references=[], proposals=[])
    assert job.status == ex.JOB_COMPLETED
    assert ex.list_proposals(conn, device_id=d, document_id=doc) == []


# --- device scoping --------------------------------------------------------------------


def test_every_read_and_write_is_device_scoped(conn):
    a, b = _device(conn), _device(conn)
    doc = _document(conn, a)
    job_id = _running_job(conn, a, doc)
    r = _ref()
    p = _proposal(r)
    ex.persist_extraction_results(
        conn, device_id=a, job_id=job_id, source_references=[r], proposals=[p])
    audit = to_audit_log_entry(_result())

    # Reads: invisible to device B.
    assert ex.get_job(conn, device_id=b, job_id=job_id) is None
    assert ex.get_active_job(conn, device_id=b, document_id=doc) is None
    assert ex.get_proposal(conn, device_id=b, proposal_id=p.proposal_id) is None
    assert ex.list_proposals(conn, device_id=b, document_id=doc) == []
    assert ex.get_source_reference(conn, device_id=b, source_reference_id=r.source_reference_id) is None
    assert ex.list_source_references(conn, device_id=b, document_id=doc) == []
    # ...and visible to the owner.
    assert ex.get_job(conn, device_id=a, job_id=job_id) is not None
    assert ex.get_proposal(conn, device_id=a, proposal_id=p.proposal_id) is not None
    assert ex.get_source_reference(conn, device_id=a, source_reference_id=r.source_reference_id) is not None

    # Writes: "not found", never "forbidden".
    with pytest.raises(ex.DocumentNotFoundError):
        ex.create_job(conn, device_id=b, document_id=doc)
    with pytest.raises(ex.JobNotFoundError):
        ex.update_job_status(conn, device_id=b, job_id=job_id, new_status=ex.JOB_FAILED)
    with pytest.raises(ex.JobNotFoundError):
        ex.persist_extraction_results(
            conn, device_id=b, job_id=job_id, source_references=[], proposals=[])
    with pytest.raises(ex.JobNotFoundError):
        ex.record_ai_request(conn, device_id=b, job_id=job_id, audit_entry=audit)
    with pytest.raises(ex.DocumentNotFoundError):
        ex.delete_document_extraction_data(conn, device_id=b, document_id=doc)

    # Device B's attempts changed nothing.
    assert ex.get_job(conn, device_id=a, job_id=job_id).status == ex.JOB_COMPLETED
    assert len(ex.list_proposals(conn, device_id=a, document_id=doc)) == 1
    assert _count(conn, "ai_request_log") == 0


def test_a_document_id_alone_does_not_expose_another_devices_active_job(conn):
    a, b = _device(conn), _device(conn)
    doc_a, doc_b = _document(conn, a), _document(conn, b)
    ex.create_job(conn, device_id=a, document_id=doc_a)
    assert ex.get_active_job(conn, device_id=b, document_id=doc_a) is None
    assert ex.create_job(conn, device_id=b, document_id=doc_b).created  # B's own doc is unaffected


# --- AI audit log ------------------------------------------------------------------------


def _result() -> StructuredCallResult:
    return StructuredCallResult(
        operation=Operation.ASSIST_DOCUMENT_STRUCTURING, schema_name="s", schema_version="1.0.0",
        model="m", output={"secret": "clinical text"}, validation_outcome="PASSED",
        retry_count=1, latency_ms=12.5, error_class=None)


def test_record_ai_request_stores_only_the_audit_projection(conn):
    d = _device(conn)
    job_id = _running_job(conn, d, _document(conn, d))
    ex.record_ai_request(
        conn, device_id=d, job_id=job_id, audit_entry=to_audit_log_entry(_result()), now=T0)
    row = conn.execute(
        "SELECT job_id, regime, operation, schema_version, model, latency_ms, "
        "validation_outcome, retry_count, error_class, created_at FROM ai_request_log").fetchone()
    assert row == (job_id, "ASSIST", "assist.document_structuring", "1.0.0", "m", 12.5,
                   "PASSED", 1, None, "2026-09-29T10:00:00Z")
    assert "clinical text" not in repr(conn.execute("SELECT * FROM ai_request_log").fetchall())


def test_record_ai_request_rejects_extra_or_missing_keys(conn):
    d = _device(conn)
    job_id = _running_job(conn, d, _document(conn, d))
    good = to_audit_log_entry(_result())
    with pytest.raises(ValueError):
        ex.record_ai_request(conn, device_id=d, job_id=job_id, audit_entry={**good, "prompt": "x"})
    missing = dict(good)
    missing.pop("model")
    with pytest.raises(ValueError):
        ex.record_ai_request(conn, device_id=d, job_id=job_id, audit_entry=missing)
    assert _count(conn, "ai_request_log") == 0


# --- cascade delete ------------------------------------------------------------------------


def _populate(conn, d, doc, n_proposals):
    job_id = _running_job(conn, d, doc)
    refs = [_ref(f"line {i}") for i in range(n_proposals)]
    ex.persist_extraction_results(
        conn, device_id=d, job_id=job_id, source_references=refs,
        proposals=[_proposal(r) for r in refs])
    ex.record_ai_request(
        conn, device_id=d, job_id=job_id, audit_entry=to_audit_log_entry(_result()))
    return job_id


def test_cascade_delete_removes_exactly_one_documents_rows(conn):
    d = _device(conn)
    doc1, doc2 = _document(conn, d), _document(conn, d)
    job1 = _populate(conn, d, doc1, 3)
    job2 = _populate(conn, d, doc2, 2)
    # A second (failed) job on doc1, so the job count is not trivially 1.
    failed = ex.create_job(conn, device_id=d, document_id=doc1).job.job_id
    ex.update_job_status(conn, device_id=d, job_id=failed, new_status=ex.JOB_FAILED)

    counts = ex.delete_document_extraction_data(conn, device_id=d, document_id=doc1)
    assert counts == ex.DeletionCounts(jobs=2, proposals=3, source_references=3)

    assert ex.get_job(conn, device_id=d, job_id=job1) is None
    assert ex.list_proposals(conn, device_id=d, document_id=doc1) == []
    assert ex.list_source_references(conn, device_id=d, document_id=doc1) == []

    assert ex.get_job(conn, device_id=d, job_id=job2).status == ex.JOB_COMPLETED
    assert len(ex.list_proposals(conn, device_id=d, document_id=doc2)) == 2
    assert len(ex.list_source_references(conn, device_id=d, document_id=doc2)) == 2
    # The documents rows themselves are not this function's business.
    assert _count(conn, "documents") == 2


def test_cascade_delete_keeps_content_free_ai_log_rows_unlinked(conn):
    d = _device(conn)
    doc = _document(conn, d)
    _populate(conn, d, doc, 1)
    ex.delete_document_extraction_data(conn, device_id=d, document_id=doc)
    assert _count(conn, "ai_request_log") == 1  # documented choice: retained, content-free
    assert conn.execute(
        "SELECT COUNT(*) FROM extraction_jobs WHERE job_id = (SELECT job_id FROM ai_request_log)"
    ).fetchone()[0] == 0  # ...and pointing at nothing


def test_cascade_delete_with_no_extraction_data_reports_zeros(conn):
    d = _device(conn)
    doc = _document(conn, d)
    assert ex.delete_document_extraction_data(
        conn, device_id=d, document_id=doc) == ex.DeletionCounts(0, 0, 0)


def test_cascade_delete_is_atomic(conn, monkeypatch):
    d = _device(conn)
    doc = _document(conn, d)
    _populate(conn, d, doc, 2)

    real = conn

    class _Boom:
        """Proxy connection that fails on the last DELETE (the jobs table)."""

        def __init__(self, inner):
            self._inner = inner

        def execute(self, sql, *a):
            if sql.startswith("DELETE FROM extraction_jobs"):
                raise sqlite3.OperationalError("injected")
            return self._inner.execute(sql, *a)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    with pytest.raises(sqlite3.OperationalError):
        ex.delete_document_extraction_data(_Boom(real), device_id=d, document_id=doc)
    assert _count(real, "proposals") == 2 and _count(real, "source_references") == 2
    assert _count(real, "extraction_jobs") == 1


def test_error_messages_carry_no_content(conn):
    d = _device(conn)
    doc = _document(conn, d, name="PATIENT-SECRET.pdf")
    job_id = _running_job(conn, d, doc)
    with pytest.raises(ex.IllegalJobTransitionError) as e1:
        ex.update_job_status(conn, device_id=d, job_id=job_id, new_status="SECRET-STATUS")
    with pytest.raises(ex.JobNotFoundError) as e2:
        ex.update_job_status(conn, device_id=d, job_id="SECRET-JOB", new_status=ex.JOB_FAILED)
    with pytest.raises(ValueError) as e3:
        ex.record_ai_request(conn, device_id=d, job_id=job_id, audit_entry={"SECRET-KEY": 1})
    for e in (e1, e2, e3):
        assert "SECRET" not in str(e.value)
