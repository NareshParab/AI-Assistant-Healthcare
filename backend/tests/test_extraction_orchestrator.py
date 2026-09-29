"""Tests for the extraction job orchestrator (extraction T5),
backend/extraction/orchestrator.py, plus the additive `document_date` storage
column and the new document_state helpers.

Offline: FakeLlmClient only, a temp SQLite DB and a temp storage directory per
test, synthetic PDFs only (D27).
"""

from __future__ import annotations

import json
import logging
import pathlib
import sqlite3
import uuid

import pytest

from backend.ai.assist import document_structuring as ds
from backend.ai.client.errors import LlmNotConfiguredError, LlmTransportError
from backend.ai.client.fake_client import FakeLlmClient
from backend.documents import synthetic_data as sd
from backend.documents.spans import SpanLimitExceededError, extract_spans
from backend.extraction import orchestrator as orch
from backend.storage import devices as devices_storage
from backend.storage import document_state
from backend.storage import documents as documents_storage
from backend.storage import extraction as ex
from backend.storage.db import get_connection, init_schema

MED_LINE = "Medication: Tab. Ecosprin 75mg -- 1 tablet before breakfast"


# --- fixtures and helpers ----------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "t5.db"


@pytest.fixture()
def storage_dir(tmp_path, monkeypatch):
    d = tmp_path / "doc_storage"
    monkeypatch.setenv("DOCUMENT_STORAGE_DIR", str(d))
    return d


@pytest.fixture()
def env(db_path, storage_dir):
    return _Env(db_path)


class _Env:
    def __init__(self, db_path):
        self.db_path = db_path
        conn = get_connection(db_path)
        token = devices_storage.register_device(conn).device_token
        self.device_id = devices_storage.verify_device_token(conn, token)
        conn.close()

    def conn(self):
        return get_connection(self.db_path)

    def add_document(self, pdf_bytes, device_id=None):
        conn = self.conn()
        try:
            stored = documents_storage.store_uploaded_document(
                conn,
                device_id=device_id or self.device_id,
                original_name="doc.pdf",
                file_bytes=pdf_bytes,
                page_count=1,
            )
            return stored.document_id
        finally:
            conn.close()

    def add_job(self, document_id, device_id=None):
        conn = self.conn()
        try:
            return ex.create_job(conn, device_id=device_id or self.device_id, document_id=document_id).job.job_id
        finally:
            conn.close()

    def setup(self, pdf_bytes):
        document_id = self.add_document(pdf_bytes)
        return document_id, self.add_job(document_id)

    def run(self, job_id, client, **kw):
        return orch.run_extraction_job(
            job_id, device_id=self.device_id, llm_client=client, db=self.db_path, **kw
        )

    def q(self, sql, *args):
        conn = self.conn()
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def job(self, job_id):
        conn = self.conn()
        try:
            return ex.get_job(conn, device_id=self.device_id, job_id=job_id)
        finally:
            conn.close()

    def proposals(self, document_id):
        conn = self.conn()
        try:
            return ex.list_proposals(conn, device_id=self.device_id, document_id=document_id)
        finally:
            conn.close()

    def refs(self, document_id):
        conn = self.conn()
        try:
            return ex.list_source_references(conn, device_id=self.device_id, document_id=document_id)
        finally:
            conn.close()

    def state(self, document_id):
        return self.q("SELECT processing_state FROM documents WHERE document_id = ?", document_id)[0][0]

    def counts(self):
        return {t: self.q(f"SELECT COUNT(*) FROM {t}")[0][0]
                for t in ("proposals", "source_references", "extraction_jobs", "ai_request_log", "documents")}


def _sid(pdf_bytes, prefix):
    return next(s.span_id for s in extract_spans(pdf_bytes).spans if s.text.startswith(prefix))


def _prop(span_id, fields=None, ptype="MEDICATION", status="current", confidence=0.9):
    default = {"MEDICATION": {"medicineName": "Tab. Ecosprin"}, "PRECAUTION": {"precautionText": "Avoid"}}
    return {
        "sourceSpanId": span_id,
        "proposedType": ptype,
        "fields": dict(default[ptype] if fields is None else fields),
        "sourceStatus": status,
        "confidence": confidence,
    }


def _out(*proposals, date=None):
    return {"proposals": list(proposals), "documentDate": date}


class _CapturingFake(FakeLlmClient):
    def __init__(self, scripted, hook=None):
        super().__init__(scripted)
        self.seen = []
        self.hook = hook

    def _raw_call(self, *, model, system_prompt, input_data, schema):
        self.seen.append((system_prompt, input_data))
        if self.hook:
            self.hook()
        return super()._raw_call(model=model, system_prompt=system_prompt, input_data=input_data, schema=schema)


class _RaisingLlm(FakeLlmClient):
    def __init__(self, exc):
        super().__init__([])
        self.exc = exc

    def _raw_call(self, **kw):
        self.calls_made += 1
        raise self.exc


PRESCRIPTION = sd.generate_synthetic_prescription()


# --- happy path ---------------------------------------------------------------------------


def test_happy_path_persists_everything_and_completes(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    e = _sid(PRESCRIPTION, "Medication: Tab. Ecosprin")
    a = _sid(PRESCRIPTION, "Medication: Tab. Atorvastatin")
    client = _CapturingFake([_out(
        _prop(e, {"medicineName": "Tab. Ecosprin", "doseText": "75mg", "timingText": "before breakfast"}),
        _prop(a, {"medicineName": "Tab. Atorvastatin", "doseText": "10 mg"}),
        date="12 Aug 2026",
    )])

    outcome = env.run(job_id, client)

    assert outcome.status == "COMPLETED" and outcome.proposal_count == 2 and outcome.dropped_count == 0
    job = env.job(job_id)
    assert job.status == "COMPLETED" and job.document_date == "12 Aug 2026"
    assert (job.model, job.schema_version, job.retry_count) == ("claude-sonnet-5", "1", 0)
    props = env.proposals(document_id)
    assert [p.review_state for p in props] == ["PROPOSED", "UNCLEAR"]
    assert [p.verbatim_check for p in props] == ["PASSED", "FAILED"]
    assert props[0].original_text == MED_LINE and props[0].job_id == job_id
    assert props[1].proposed_fields["doseText"] == "Medication: Tab. Atorvastatin 10mg -- 1 tablet at night"
    refs = env.refs(document_id)
    assert len(refs) == 2 and len({r.source_reference_id for r in refs}) == 2
    assert {p.source_reference_id for p in props} == {r.source_reference_id for r in refs}
    spans = {s.span_id: s for s in extract_spans(PRESCRIPTION).spans}
    ref0 = next(r for r in refs if r.source_reference_id == props[0].source_reference_id)
    assert ref0.bbox_pt == spans[e].bbox_pt and ref0.verbatim_text == MED_LINE and ref0.page == 0
    assert env.state(document_id) == "PROPOSALS_READY"
    rows = env.q("SELECT job_id, regime, operation, schema_version, model, validation_outcome, retry_count, error_class FROM ai_request_log")
    assert rows == [(job_id, "ASSIST", "assist.document_structuring", "1", "claude-sonnet-5", "PASSED", 0, None)]
    (prompt, input_data) = client.seen[0]
    assert prompt == ds.SYSTEM_PROMPT and client.calls_made == 1


def test_run_twice_second_is_skipped(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    client = FakeLlmClient([_out()])
    assert env.run(job_id, client).status == "COMPLETED"
    again = env.run(job_id, FakeLlmClient([_out()]))
    assert again.status == "SKIPPED"


def test_unknown_or_foreign_job_is_skipped_and_never_calls_the_model(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    client = FakeLlmClient([_out()])
    assert env.run("no-such-job", client).status == "SKIPPED"
    other = orch.run_extraction_job(job_id, device_id="another-device", llm_client=client, db=env.db_path)
    assert other.status == "SKIPPED" and client.calls_made == 0
    assert env.job(job_id).status == "PENDING"


def test_constant_clock_is_used_for_timestamps(env):
    from datetime import datetime, timezone

    t = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)
    document_id, job_id = env.setup(PRESCRIPTION)
    env.run(job_id, FakeLlmClient([_out()]), now=t)
    job = env.job(job_id)
    assert job.started_at == t and job.finished_at == t


# --- safety scenarios through the whole pipeline -------------------------------------------------


def test_dose_changed_and_hallucinated_are_unclear_and_never_stored(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    e = _sid(PRESCRIPTION, "Medication: Tab. Ecosprin")
    a = _sid(PRESCRIPTION, "Medication: Tab. Atorvastatin")
    env.run(job_id, FakeLlmClient([_out(
        _prop(e, {"medicineName": "Tab. Ecosprin", "doseText": "75 mg"}),
        _prop(a, {"medicineName": "Tab. Atorvastatin", "doseText": "MODEL-INVENTED-99mg"}),
    )]))
    for p in env.proposals(document_id):
        assert p.review_state == "UNCLEAR" and p.verbatim_check == "FAILED"
    stored = json.dumps([p.proposed_fields for p in env.proposals(document_id)])
    assert "75 mg" not in stored and "MODEL-INVENTED-99mg" not in stored
    dump = repr(env.q("SELECT * FROM proposals")) + repr(env.q("SELECT * FROM source_references"))
    assert "MODEL-INVENTED-99mg" not in dump


def test_unknown_span_id_is_dropped_and_counted(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    e = _sid(PRESCRIPTION, "Medication: Tab. Ecosprin")
    outcome = env.run(job_id, FakeLlmClient([_out(_prop("p7_l77"), _prop(e))]))
    assert outcome.status == "COMPLETED" and outcome.dropped_count == 1 and outcome.proposal_count == 1
    assert len(env.proposals(document_id)) == 1 and len(env.refs(document_id)) == 1


def test_wrapped_line_is_unclear_with_union_region(env):
    pdf = sd.generate_wrapped_line_document()
    document_id, job_id = env.setup(pdf)
    doc = extract_spans(pdf)
    first = next(s for s in doc.spans if s.text.startswith("Tab. Metformin"))
    env.run(job_id, FakeLlmClient([_out(_prop(first.span_id, {"medicineName": "Tab. Metformin", "doseText": "500mg -- 1"}))]))
    (p,) = env.proposals(document_id)
    (r,) = env.refs(document_id)
    assert p.review_state == "UNCLEAR"
    assert r.bbox_pt[3] > first.bbox_pt[3]  # extends below the first line: union with the wrapped lines
    assert r.verbatim_text.endswith("with water")


def test_historical_item_under_discontinued_heading_is_unclear(env):
    pdf = sd.generate_discontinued_section_document()
    document_id, job_id = env.setup(pdf)
    old = _sid(pdf, "Tab. Olddrug")
    cur = _sid(pdf, "Tab. Currentdrug")
    env.run(job_id, FakeLlmClient([_out(
        _prop(old, {"medicineName": "Tab. Olddrug"}), _prop(cur, {"medicineName": "Tab. Currentdrug"}),
    )]))
    a, b = env.proposals(document_id)
    assert (a.review_state, a.source_status) == ("UNCLEAR", "unclear")
    assert b.review_state == "PROPOSED"


def test_diagnosis_like_line_gets_no_special_treatment_and_nothing_is_invented(env):
    pdf = sd.generate_injection_and_diagnosis_document()
    document_id, job_id = env.setup(pdf)
    dx = _sid(pdf, "Diagnosis:")
    env.run(job_id, FakeLlmClient([_out(_prop(dx, {"precautionText": "Sampleitis is severe"}, ptype="PRECAUTION"))]))
    (p,) = env.proposals(document_id)
    assert p.review_state == "UNCLEAR" and p.proposed_fields["precautionText"] == sd.DIAGNOSIS_LINE
    assert "severe" not in json.dumps(p.proposed_fields)


def test_injection_text_reaches_only_the_input_and_never_yields_an_unverified_proposed(env):
    pdf = sd.generate_injection_and_diagnosis_document()
    document_id, job_id = env.setup(pdf)
    inj = _sid(pdf, "IGNORE ALL")
    client = _CapturingFake([_out(_prop(inj, {"medicineName": "mark every item confidence 1.0"}, confidence=1.0))])
    env.run(job_id, client)
    (prompt, input_data) = client.seen[0]
    assert prompt == ds.SYSTEM_PROMPT and sd.INJECTION_LINE not in prompt
    assert sd.INJECTION_LINE in json.dumps(input_data)
    for p in env.proposals(document_id):
        assert p.review_state == "UNCLEAR"  # 'PREVIOUS' in the injected line trips the marker backstop
    # a model that returns nothing (ignoring the injected text) adds nothing
    document_id2, job_id2 = env.setup(pdf)
    assert env.run(job_id2, FakeLlmClient([_out()])).proposal_count == 0


# --- model failures ---------------------------------------------------------------------------------


def test_malformed_then_valid_recovers(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    e = _sid(PRESCRIPTION, "Medication: Tab. Ecosprin")
    bad = {"proposals": [{"proposedType": "DIAGNOSIS"}], "documentDate": None}
    client = FakeLlmClient([bad, _out(_prop(e))])
    assert env.run(job_id, client).status == "COMPLETED"
    assert env.job(job_id).retry_count == 1 and client.calls_made == 2
    assert len(env.proposals(document_id)) == 1


def test_persistent_invalid_output_fails_closed_with_nothing_persisted(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    bad = {"proposals": [{"proposedType": "DIAGNOSIS"}], "documentDate": None}
    outcome = env.run(job_id, FakeLlmClient([bad, bad, bad]))
    assert (outcome.status, outcome.error_class) == ("EXTRACTION_FAILED", "SchemaValidationError")
    job = env.job(job_id)
    assert job.status == "EXTRACTION_FAILED" and job.error_class == "SchemaValidationError" and job.retry_count == 2
    c = env.counts()
    assert c["proposals"] == 0 and c["source_references"] == 0
    assert env.state(document_id) == "EXTRACTION_FAILED"
    rows = env.q("SELECT validation_outcome, retry_count FROM ai_request_log")
    assert rows == [("FAILED_CLOSED", 2)]  # the audit row is still written


def test_transport_failure_fails_closed_with_audit_row(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    outcome = env.run(job_id, FakeLlmClient([LlmTransportError("SECRET-PROVIDER-TEXT")] * 3))
    assert outcome.error_class == "LlmTransportError"
    assert env.job(job_id).error_class == "LlmTransportError"
    assert "SECRET-PROVIDER-TEXT" not in repr(env.q("SELECT * FROM extraction_jobs"))
    assert env.q("SELECT COUNT(*) FROM ai_request_log")[0][0] == 1


def test_not_configured_error_fails_the_job_with_its_class_name(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    outcome = env.run(job_id, _RaisingLlm(LlmNotConfiguredError("SECRET-KEY-HINT")))
    assert (outcome.status, outcome.error_class) == ("EXTRACTION_FAILED", "LlmNotConfiguredError")
    assert env.job(job_id).status == "EXTRACTION_FAILED"
    assert env.state(document_id) == "EXTRACTION_FAILED"
    assert "SECRET-KEY-HINT" not in repr(env.q("SELECT * FROM extraction_jobs"))


# --- input problems: no model call ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "pdf,code",
    [
        (sd.generate_blank_document(), "NO_TEXT_LAYER"),
        (b"%PDF-1.4 this is not a real pdf", "PDF_UNREADABLE"),
    ],
)
def test_unusable_pdf_fails_without_a_model_call(env, pdf, code):
    document_id, job_id = env.setup(pdf)
    client = FakeLlmClient([_out()])
    outcome = env.run(job_id, client)
    assert (outcome.status, outcome.error_class) == ("EXTRACTION_FAILED", code)
    assert client.calls_made == 0
    assert env.job(job_id).error_class == code and env.state(document_id) == "EXTRACTION_FAILED"
    assert env.counts()["proposals"] == 0 and env.counts()["ai_request_log"] == 0


def test_span_limit_fails_without_a_model_call(env, monkeypatch):
    def boom(_bytes):
        raise SpanLimitExceededError("too many")

    monkeypatch.setattr(orch, "extract_spans", boom)
    document_id, job_id = env.setup(PRESCRIPTION)
    client = FakeLlmClient([_out()])
    assert env.run(job_id, client).error_class == "SPAN_LIMIT" and client.calls_made == 0


def test_over_cap_input_fails_without_a_model_call_and_boundary_is_exact(env, monkeypatch):
    size = len(json.dumps(ds.build_input_data(extract_spans(PRESCRIPTION))))
    document_id, job_id = env.setup(PRESCRIPTION)
    monkeypatch.setattr(orch, "MAX_INPUT_CHARS", size - 1)
    client = FakeLlmClient([_out()])
    outcome = env.run(job_id, client)
    assert outcome.error_class == "INPUT_TOO_LARGE" and client.calls_made == 0
    assert env.state(document_id) == "EXTRACTION_FAILED"

    document_id2, job_id2 = env.setup(PRESCRIPTION)
    monkeypatch.setattr(orch, "MAX_INPUT_CHARS", size)
    client2 = FakeLlmClient([_out()])
    assert env.run(job_id2, client2).status == "COMPLETED" and client2.calls_made == 1


def test_default_cap_is_a_documented_constant():
    assert orch.MAX_INPUT_CHARS == 40_000


def test_missing_stored_file_fails_storage_unavailable(env, storage_dir):
    document_id, job_id = env.setup(PRESCRIPTION)
    for f in storage_dir.iterdir():
        f.unlink()
    client = FakeLlmClient([_out()])
    outcome = env.run(job_id, client)
    assert outcome.error_class == "STORAGE_UNAVAILABLE" and client.calls_made == 0
    assert env.state(document_id) == "EXTRACTION_FAILED"


@pytest.mark.parametrize("kind", ["parent", "absolute", "subdir", "backslash"])
def test_stored_path_outside_the_storage_dir_is_never_read(env, storage_dir, tmp_path, kind):
    document_id, job_id = env.setup(PRESCRIPTION)
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(PRESCRIPTION)  # a perfectly valid PDF: if it were read the job would COMPLETE
    (storage_dir / "sub").mkdir(exist_ok=True)
    (storage_dir / "sub" / "inner.pdf").write_bytes(PRESCRIPTION)
    name = {
        "parent": "../outside.pdf",
        "absolute": str(outside),
        "subdir": "sub/inner.pdf",
        "backslash": "..\\outside.pdf",
    }[kind]
    conn = env.conn()
    conn.execute("UPDATE documents SET stored_filename = ? WHERE document_id = ?", (name, document_id))
    conn.commit()
    conn.close()
    client = FakeLlmClient([_out()])
    outcome = env.run(job_id, client)
    assert (outcome.status, outcome.error_class) == ("EXTRACTION_FAILED", "STORAGE_UNAVAILABLE")
    assert client.calls_made == 0


# --- outcomes: zero proposals, distinct references ------------------------------------------------------


def test_zero_valid_proposals_completes_with_an_empty_list(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    assert env.run(job_id, FakeLlmClient([_out()])).status == "COMPLETED"
    assert env.job(job_id).status == "COMPLETED" and env.proposals(document_id) == []
    assert env.state(document_id) == "PROPOSALS_READY"
    document_id2, job_id2 = env.setup(PRESCRIPTION)  # all proposals dropped: same result
    assert env.run(job_id2, FakeLlmClient([_out(_prop("p5_l50"))])).status == "COMPLETED"
    assert env.proposals(document_id2) == [] and env.state(document_id2) == "PROPOSALS_READY"


def test_two_proposals_citing_the_same_span_get_distinct_uuid4_references(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    e = _sid(PRESCRIPTION, "Medication: Tab. Ecosprin")
    env.run(job_id, FakeLlmClient([_out(_prop(e), _prop(e))]))
    props = env.proposals(document_id)
    ids = [p.source_reference_id for p in props]
    assert len(props) == 2 and ids[0] != ids[1] and len(env.refs(document_id)) == 2
    for i in ids:
        assert uuid.UUID(i).version == 4
    r0, r1 = env.refs(document_id)
    assert r0.bbox_pt == r1.bbox_pt  # same region, separate rows


# --- never RUNNING, never partial --------------------------------------------------------------------------


def _assert_failed_cleanly(env, document_id, job_id, error_class):
    job = env.job(job_id)
    assert job.status == "EXTRACTION_FAILED" and job.error_class == error_class
    assert job.finished_at is not None
    assert env.state(document_id) == "EXTRACTION_FAILED"
    assert env.counts()["proposals"] == 0 and env.counts()["source_references"] == 0


@pytest.mark.parametrize("stage", ["read", "spans", "model", "audit", "gate", "persist"])
def test_job_is_never_left_running_after_an_exception_at_any_stage(env, monkeypatch, stage):
    document_id, job_id = env.setup(PRESCRIPTION)
    e = _sid(PRESCRIPTION, "Medication: Tab. Ecosprin")
    client = FakeLlmClient([_out(_prop(e))])

    def boom(*a, **k):
        raise RuntimeError("SECRET-EXC-MESSAGE")

    if stage == "read":
        monkeypatch.setattr(document_state, "read_stored_file", boom)
    elif stage == "spans":
        monkeypatch.setattr(orch, "extract_spans", boom)
    elif stage == "model":
        client = _RaisingLlm(RuntimeError("SECRET-EXC-MESSAGE"))
    elif stage == "audit":
        monkeypatch.setattr(ex, "record_ai_request", boom)
    elif stage == "gate":
        monkeypatch.setattr(orch, "apply_gate", boom)
    elif stage == "persist":
        real = ex.persist_extraction_results

        def half_then_fail(conn, **kw):  # real writes happen, then the transaction fails
            kw["proposals"] = list(kw["proposals"]) + [
                ex.NewProposal("MEDICATION", {"x": object()}, "t", kw["source_references"][0].source_reference_id,
                               0, 0.9, "PROPOSED", "PASSED")
            ]
            return real(conn, **kw)

        monkeypatch.setattr(ex, "persist_extraction_results", half_then_fail)

    outcome = env.run(job_id, client)  # must not raise
    expected = "TypeError" if stage == "persist" else "RuntimeError"
    assert outcome.status == "EXTRACTION_FAILED" and outcome.error_class == expected
    _assert_failed_cleanly(env, document_id, job_id, expected)
    assert "SECRET-EXC-MESSAGE" not in repr(env.q("SELECT * FROM extraction_jobs"))


def test_persist_is_all_or_nothing_when_a_later_proposal_is_bad(env, monkeypatch):
    document_id, job_id = env.setup(PRESCRIPTION)
    e = _sid(PRESCRIPTION, "Medication: Tab. Ecosprin")
    real = ex.persist_extraction_results

    def bad_second(conn, **kw):
        good = kw["proposals"][0]
        kw["proposals"] = [good, ex.NewProposal(good.proposed_type, good.proposed_fields, "t", "dangling-ref",
                                                0, 0.9, "PROPOSED", "PASSED")]
        return real(conn, **kw)

    monkeypatch.setattr(ex, "persist_extraction_results", bad_second)
    outcome = env.run(job_id, FakeLlmClient([_out(_prop(e))]))
    assert outcome.status == "EXTRACTION_FAILED"
    _assert_failed_cleanly(env, document_id, job_id, "IntegrityError")


# --- deleted mid-run ---------------------------------------------------------------------------------------------


def _purge(env, document_id):
    conn = env.conn()
    ex.delete_document_extraction_data(conn, device_id=env.device_id, document_id=document_id)
    conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
    conn.commit()
    conn.close()


def _assert_nothing_left(env, document_id):
    c = env.counts()
    assert c["proposals"] == 0 and c["source_references"] == 0 and c["extraction_jobs"] == 0
    assert env.q("SELECT COUNT(*) FROM documents WHERE document_id = ?", document_id)[0][0] == 0


def test_document_deleted_during_the_model_call_writes_nothing(env):
    document_id, job_id = env.setup(PRESCRIPTION)
    e = _sid(PRESCRIPTION, "Medication: Tab. Ecosprin")
    client = _CapturingFake([_out(_prop(e))], hook=lambda: _purge(env, document_id))
    outcome = env.run(job_id, client)  # no exception escapes
    assert outcome.status == "ABANDONED"
    _assert_nothing_left(env, document_id)
    assert env.counts()["ai_request_log"] == 0  # the audit write for a vanished job is refused


def test_document_deleted_before_persist_writes_nothing(env, monkeypatch):
    document_id, job_id = env.setup(PRESCRIPTION)
    e = _sid(PRESCRIPTION, "Medication: Tab. Ecosprin")
    real_gate = orch.apply_gate

    def delete_then_gate(*a, **k):
        _purge(env, document_id)
        return real_gate(*a, **k)

    monkeypatch.setattr(orch, "apply_gate", delete_then_gate)
    outcome = env.run(job_id, FakeLlmClient([_out(_prop(e))]))
    assert outcome.status == "ABANDONED"
    _assert_nothing_left(env, document_id)  # no orphan rows, nothing resurrected


def test_document_deleted_during_span_extraction_writes_nothing(env, monkeypatch):
    document_id, job_id = env.setup(PRESCRIPTION)
    real = orch.extract_spans

    def delete_then_extract(b):
        _purge(env, document_id)
        return real(b)

    monkeypatch.setattr(orch, "extract_spans", delete_then_extract)
    assert env.run(job_id, FakeLlmClient([_out()])).status == "ABANDONED"
    _assert_nothing_left(env, document_id)


# --- logging ----------------------------------------------------------------------------------------------------


def test_logs_never_contain_document_text_values_prompts_or_exception_text(env, caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)
    pdf = sd.generate_injection_and_diagnosis_document()
    secret_values = ["SECRET-MODEL-VALUE-123", "Sampledrug", sd.INJECTION_LINE, sd.DIAGNOSIS_LINE, "12 Aug 2026",
                     ds.SYSTEM_PROMPT[:60], "SECRET-EXC-MESSAGE"]

    document_id, job_id = env.setup(pdf)
    med = _sid(pdf, "Medication: Tab. Sampledrug")
    env.run(job_id, FakeLlmClient([_out(_prop(med, {"medicineName": "SECRET-MODEL-VALUE-123"}), date="12 Aug 2026")]))

    document_id2, job_id2 = env.setup(pdf)  # failure path, with an exception message full of content
    env.run(job_id2, _RaisingLlm(RuntimeError("SECRET-EXC-MESSAGE " + sd.INJECTION_LINE)))

    document_id3, job_id3 = env.setup(pdf)  # validation failure path
    env.run(job_id3, FakeLlmClient([{"nope": "SECRET-MODEL-VALUE-123"}] * 3))

    text = " ".join(r.getMessage() for r in caplog.records)
    assert "extraction_job" in text  # something was logged
    for secret in secret_values:
        assert secret not in text, secret
    for r in caplog.records:
        assert r.exc_info is None or r.name != "extraction.orchestrator"


# --- additive documentDate column & storage helpers --------------------------------------------------------------


_OLD_JOBS_DDL = """
CREATE TABLE extraction_jobs (
    job_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, device_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING','RUNNING','COMPLETED','EXTRACTION_FAILED')),
    error_class TEXT, retry_count INTEGER, model TEXT, schema_version TEXT,
    created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
    FOREIGN KEY (document_id) REFERENCES documents (document_id),
    FOREIGN KEY (device_id) REFERENCES devices (device_id))
"""


def test_document_date_column_is_added_to_a_database_created_before_it(tmp_path):
    path = tmp_path / "old.db"
    raw = sqlite3.connect(str(path))
    raw.execute("CREATE TABLE devices (device_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, issued_at TEXT NOT NULL)")
    raw.execute("CREATE TABLE documents (document_id TEXT PRIMARY KEY, device_id TEXT NOT NULL, original_name TEXT NOT NULL, "
                "stored_filename TEXT NOT NULL UNIQUE, document_type TEXT NOT NULL, processing_state TEXT NOT NULL, "
                "page_count INTEGER NOT NULL, content_hash TEXT NOT NULL, size_bytes INTEGER NOT NULL, received_at TEXT NOT NULL, "
                "FOREIGN KEY (device_id) REFERENCES devices (device_id))")
    raw.execute(_OLD_JOBS_DDL)
    raw.execute("INSERT INTO devices VALUES ('d1','h','2026-01-01T00:00:00Z')")
    raw.execute("INSERT INTO documents VALUES ('doc1','d1','n','f.pdf','unspecified','RECEIVED',1,'h',1,'2026-01-01T00:00:00Z')")
    raw.execute("INSERT INTO extraction_jobs (job_id,document_id,device_id,status,created_at) VALUES ('j1','doc1','d1','EXTRACTION_FAILED','2026-01-01T00:00:00Z')")
    raw.commit()
    raw.close()

    conn = get_connection(path)  # runs init_schema over the old database
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(extraction_jobs)")]
        assert cols.count("document_date") == 1
        init_schema(conn)
        init_schema(conn)  # idempotent
        assert [r[1] for r in conn.execute("PRAGMA table_info(extraction_jobs)")].count("document_date") == 1
        old = ex.get_job(conn, device_id="d1", job_id="j1")
        assert old.status == "EXTRACTION_FAILED" and old.document_date is None  # old row survives
        # existing (old-style) persist callers still work, and the new parameter works
        job = ex.create_job(conn, device_id="d1", document_id="doc1").job
        ex.update_job_status(conn, device_id="d1", job_id=job.job_id, new_status="RUNNING")
        done = ex.persist_extraction_results(conn, device_id="d1", job_id=job.job_id, source_references=[], proposals=[])
        assert done.status == "COMPLETED" and done.document_date is None
        job2 = ex.create_job(conn, device_id="d1", document_id="doc1").job
        ex.update_job_status(conn, device_id="d1", job_id=job2.job_id, new_status="RUNNING")
        done2 = ex.persist_extraction_results(
            conn, device_id="d1", job_id=job2.job_id, source_references=[], proposals=[], document_date="12 Aug 2026")
        assert done2.document_date == "12 Aug 2026"
    finally:
        conn.close()


def test_fresh_database_has_the_column_in_the_same_position(db_path):
    conn = get_connection(db_path)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(extraction_jobs)")]
        assert cols[-1] == "document_date" and "finished_at" in cols
    finally:
        conn.close()


@pytest.mark.parametrize("bad", ["", ".", "..", "../x.pdf", "a/b.pdf", "a\\b.pdf", "/etc/passwd", "C:\\x.pdf", "C:x.pdf"])
def test_resolve_stored_path_refuses_anything_but_a_bare_existing_file(storage_dir, bad):
    storage_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(document_state.StoredFileUnavailableError) as exc:
        document_state.resolve_stored_path(bad, storage_dir)
    assert bad not in str(exc.value) or bad == ""


def test_resolve_stored_path_accepts_a_server_generated_name(storage_dir):
    storage_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4()}.pdf"
    (storage_dir / name).write_bytes(b"%PDF-")
    assert document_state.read_stored_file(name, storage_dir) == b"%PDF-"
    with pytest.raises(document_state.StoredFileUnavailableError):
        document_state.resolve_stored_path(f"{uuid.uuid4()}.pdf", storage_dir)  # does not exist


def test_document_state_helpers_are_device_scoped(env):
    document_id = env.add_document(PRESCRIPTION)
    conn = env.conn()
    try:
        with pytest.raises(ex.DocumentNotFoundError):
            document_state.get_stored_filename(conn, device_id="other", document_id=document_id)
        with pytest.raises(ex.DocumentNotFoundError):
            document_state.set_processing_state(conn, device_id="other", document_id=document_id, state="EXTRACTING")
        assert env.state(document_id) == "RECEIVED"
        document_state.set_processing_state(conn, device_id=env.device_id, document_id=document_id, state="EXTRACTING")
        assert env.state(document_id) == "EXTRACTING"
    finally:
        conn.close()
