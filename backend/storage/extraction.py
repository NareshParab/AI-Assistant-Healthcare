"""Extraction storage: jobs, source references, proposals, AI audit log.

Plain functions over a sqlite3 connection (no ORM), following
backend/storage/devices.py and documents.py. Pre-confirmation, server-owned
data only (D6): nothing here is, or can become, a confirmed care instruction
(SAFE-1800/1801) -- that lives on the device.

Scoping: every function takes `device_id` and can only see or touch that
device's rows. Another device's data is indistinguishable from data that does
not exist ("not found", never "forbidden"). `source_references` has no
device column; it is scoped through its document's owner.

D26/PRIV-1650: nothing here logs, and no exception message contains a field
value, document text or extracted content. Messages are fixed strings.

Job transitions (contract section 7):
    PENDING -> RUNNING -> COMPLETED | EXTRACTION_FAILED
    PENDING -> EXTRACTION_FAILED   (a job that never started, e.g. the
                                    restart sweep; see sweep_interrupted_jobs)
COMPLETED and EXTRACTION_FAILED are terminal.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.storage.devices import to_iso_string

JOB_PENDING = "PENDING"
JOB_RUNNING = "RUNNING"
JOB_COMPLETED = "COMPLETED"
JOB_FAILED = "EXTRACTION_FAILED"

_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    JOB_PENDING: frozenset({JOB_RUNNING, JOB_FAILED}),
    JOB_RUNNING: frozenset({JOB_COMPLETED, JOB_FAILED}),
    JOB_COMPLETED: frozenset(),
    JOB_FAILED: frozenset(),
}

ERROR_CLASS_SERVER_RESTART = "SERVER_RESTART"

# Keys of backend.ai.client.results.to_audit_log_entry(), and nothing else.
_AUDIT_KEYS = frozenset(
    {
        "regime",
        "operation",
        "schemaVersion",
        "model",
        "latencyMs",
        "validationOutcome",
        "retryCount",
        "errorClass",
    }
)


class DocumentNotFoundError(Exception):
    """No such document for this device."""


class JobNotFoundError(Exception):
    """No such job for this device."""


class IllegalJobTransitionError(Exception):
    """The requested job status change is not allowed from the current status."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts: str | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    document_id: str
    device_id: str
    status: str
    error_class: str | None
    retry_count: int | None
    model: str | None
    schema_version: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True)
class CreateJobResult:
    job: JobRecord
    created: bool  # False: an active (PENDING/RUNNING) job already existed


@dataclass(frozen=True)
class NewSourceReference:
    page: int
    bbox_pt: tuple[float, float, float, float]
    verbatim_text: str
    source_reference_id: str = field(default_factory=_new_id)  # UUID v4 (contract section 6)


@dataclass(frozen=True)
class NewProposal:
    proposed_type: str
    proposed_fields: dict[str, Any]
    original_text: str
    source_reference_id: str
    page: int
    confidence: float
    review_state: str
    verbatim_check: str
    source_status: str | None = None
    proposal_id: str = field(default_factory=_new_id)


@dataclass(frozen=True)
class SourceReferenceRecord:
    source_reference_id: str
    document_id: str
    page: int
    bbox_pt: tuple[float, float, float, float]
    verbatim_text: str


@dataclass(frozen=True)
class ProposalRecord:
    proposal_id: str
    document_id: str
    job_id: str
    device_id: str
    proposed_type: str
    proposed_fields: dict[str, Any]
    original_text: str
    source_reference_id: str
    page: int
    confidence: float
    review_state: str
    verbatim_check: str
    source_status: str | None
    originally_proposed_fields: dict[str, Any] | None
    edited_fields: dict[str, Any] | None
    edit_reason: str | None
    reviewed_at: datetime | None
    plain_language_text: str | None
    plain_language_is_verbatim_fallback: bool | None
    created_at: datetime


@dataclass(frozen=True)
class DeletionCounts:
    jobs: int
    proposals: int
    source_references: int


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

_JOB_COLUMNS = (
    "job_id, document_id, device_id, status, error_class, retry_count, model, "
    "schema_version, created_at, started_at, finished_at"
)


def _job_from_row(row: tuple) -> JobRecord:
    return JobRecord(
        job_id=row[0],
        document_id=row[1],
        device_id=row[2],
        status=row[3],
        error_class=row[4],
        retry_count=row[5],
        model=row[6],
        schema_version=row[7],
        created_at=_parse(row[8]),
        started_at=_parse(row[9]),
        finished_at=_parse(row[10]),
    )


def _require_document(conn: sqlite3.Connection, device_id: str, document_id: str) -> None:
    row = conn.execute(
        "SELECT 1 FROM documents WHERE document_id = ? AND device_id = ?",
        (document_id, device_id),
    ).fetchone()
    if row is None:
        raise DocumentNotFoundError("document not found")


def get_job(conn: sqlite3.Connection, *, device_id: str, job_id: str) -> JobRecord | None:
    row = conn.execute(
        f"SELECT {_JOB_COLUMNS} FROM extraction_jobs WHERE job_id = ? AND device_id = ?",
        (job_id, device_id),
    ).fetchone()
    return _job_from_row(row) if row else None


def get_active_job(
    conn: sqlite3.Connection, *, device_id: str, document_id: str
) -> JobRecord | None:
    """The document's PENDING/RUNNING job, if any (at most one exists)."""

    row = conn.execute(
        f"SELECT {_JOB_COLUMNS} FROM extraction_jobs "
        "WHERE document_id = ? AND device_id = ? AND status IN ('PENDING','RUNNING')",
        (document_id, device_id),
    ).fetchone()
    return _job_from_row(row) if row else None


def create_job(
    conn: sqlite3.Connection,
    *,
    device_id: str,
    document_id: str,
    now: datetime | None = None,
) -> CreateJobResult:
    """Create a PENDING job, or return the document's existing active job.

    Idempotency (contract section 1) is enforced by the partial unique index,
    so it holds even under concurrent callers: the loser of a race catches
    the index violation and returns the winner's job. After a job is
    COMPLETED or EXTRACTION_FAILED a new one can be created.
    Raises DocumentNotFoundError if the document is not this device's.
    """

    _require_document(conn, device_id, document_id)
    now = now or _utc_now()
    job_id = _new_id()
    try:
        conn.execute(
            "INSERT INTO extraction_jobs (job_id, document_id, device_id, status, created_at) "
            "VALUES (?, ?, ?, 'PENDING', ?)",
            (job_id, document_id, device_id, to_iso_string(now)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        existing = get_active_job(conn, device_id=device_id, document_id=document_id)
        if existing is None:
            raise
        return CreateJobResult(job=existing, created=False)

    job = get_job(conn, device_id=device_id, job_id=job_id)
    return CreateJobResult(job=job, created=True)


def _apply_transition(
    conn: sqlite3.Connection,
    *,
    device_id: str,
    job_id: str,
    new_status: str,
    now: datetime,
    error_class: str | None = None,
    retry_count: int | None = None,
    model: str | None = None,
    schema_version: str | None = None,
) -> None:
    """Validate and write one transition WITHOUT committing (callers own the
    transaction). Never called with a status outside the four job states."""

    row = conn.execute(
        "SELECT status FROM extraction_jobs WHERE job_id = ? AND device_id = ?",
        (job_id, device_id),
    ).fetchone()
    if row is None:
        raise JobNotFoundError("job not found")
    if new_status not in _ALLOWED_TRANSITIONS[row[0]]:
        raise IllegalJobTransitionError("illegal job status transition")

    ts = to_iso_string(now)
    conn.execute(
        """
        UPDATE extraction_jobs
        SET status = ?,
            error_class = COALESCE(?, error_class),
            retry_count = COALESCE(?, retry_count),
            model = COALESCE(?, model),
            schema_version = COALESCE(?, schema_version),
            started_at = CASE WHEN ? = 'RUNNING' THEN ? ELSE started_at END,
            finished_at = CASE WHEN ? IN ('COMPLETED','EXTRACTION_FAILED') THEN ? ELSE finished_at END
        WHERE job_id = ? AND device_id = ?
        """,
        (
            new_status,
            error_class,
            retry_count,
            model,
            schema_version,
            new_status,
            ts,
            new_status,
            ts,
            job_id,
            device_id,
        ),
    )


def update_job_status(
    conn: sqlite3.Connection,
    *,
    device_id: str,
    job_id: str,
    new_status: str,
    now: datetime | None = None,
    error_class: str | None = None,
    retry_count: int | None = None,
    model: str | None = None,
    schema_version: str | None = None,
) -> JobRecord:
    """Move a job along the allowed transitions; refuse anything else.

    Raises JobNotFoundError, or IllegalJobTransitionError (also for an
    unknown status). Metadata arguments left as None do not overwrite.
    """

    if new_status not in _ALLOWED_TRANSITIONS:
        raise IllegalJobTransitionError("illegal job status transition")
    try:
        _apply_transition(
            conn,
            device_id=device_id,
            job_id=job_id,
            new_status=new_status,
            now=now or _utc_now(),
            error_class=error_class,
            retry_count=retry_count,
            model=model,
            schema_version=schema_version,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_job(conn, device_id=device_id, job_id=job_id)


def sweep_interrupted_jobs(
    conn: sqlite3.Connection, *, now: datetime | None = None
) -> list[tuple[str, str]]:
    """Startup-sweep primitive: fail every PENDING/RUNNING job with
    error_class SERVER_RESTART, across ALL devices (a process-level operation,
    not a per-device one). Terminal jobs are untouched. Returns
    (job_id, document_id) for each job changed, so the caller can update
    document state. Not wired into startup here.
    """

    ts = to_iso_string(now or _utc_now())
    try:
        rows = conn.execute(
            "SELECT job_id, document_id FROM extraction_jobs "
            "WHERE status IN ('PENDING','RUNNING') ORDER BY created_at, rowid"
        ).fetchall()
        conn.execute(
            "UPDATE extraction_jobs SET status = 'EXTRACTION_FAILED', error_class = ?, "
            "finished_at = ? WHERE status IN ('PENDING','RUNNING')",
            (ERROR_CLASS_SERVER_RESTART, ts),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return [(r[0], r[1]) for r in rows]


# ---------------------------------------------------------------------------
# Atomic persist of results
# ---------------------------------------------------------------------------


def persist_extraction_results(
    conn: sqlite3.Connection,
    *,
    device_id: str,
    job_id: str,
    source_references: list[NewSourceReference],
    proposals: list[NewProposal],
    model: str | None = None,
    schema_version: str | None = None,
    retry_count: int | None = None,
    now: datetime | None = None,
) -> JobRecord:
    """Insert source references and proposals AND flip the job RUNNING ->
    COMPLETED in ONE transaction: all or nothing (D24: no partial proposals).

    Any failure -- a bad row, a non-serializable field, a constraint, an
    illegal job state -- rolls everything back, leaving no proposals, no
    source references and the job status unchanged, then re-raises.
    """

    now = now or _utc_now()
    ts = to_iso_string(now)
    try:
        row = conn.execute(
            "SELECT document_id FROM extraction_jobs WHERE job_id = ? AND device_id = ?",
            (job_id, device_id),
        ).fetchone()
        if row is None:
            raise JobNotFoundError("job not found")
        document_id = row[0]

        for ref in source_references:
            conn.execute(
                "INSERT INTO source_references (source_reference_id, document_id, page, "
                "x0, y0, x1, y1, verbatim_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ref.source_reference_id,
                    document_id,
                    ref.page,
                    *ref.bbox_pt,
                    ref.verbatim_text,
                ),
            )
        for p in proposals:
            conn.execute(
                "INSERT INTO proposals (proposal_id, document_id, job_id, device_id, "
                "proposed_type, proposed_fields_json, original_text, source_reference_id, "
                "page, confidence, review_state, verbatim_check, source_status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    p.proposal_id,
                    document_id,
                    job_id,
                    device_id,
                    p.proposed_type,
                    json.dumps(p.proposed_fields, ensure_ascii=False),
                    p.original_text,
                    p.source_reference_id,
                    p.page,
                    p.confidence,
                    p.review_state,
                    p.verbatim_check,
                    p.source_status,
                    ts,
                ),
            )
        _apply_transition(
            conn,
            device_id=device_id,
            job_id=job_id,
            new_status=JOB_COMPLETED,
            now=now,
            retry_count=retry_count,
            model=model,
            schema_version=schema_version,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_job(conn, device_id=device_id, job_id=job_id)


# ---------------------------------------------------------------------------
# Reads (always device-scoped)
# ---------------------------------------------------------------------------

_PROPOSAL_COLUMNS = (
    "proposal_id, document_id, job_id, device_id, proposed_type, proposed_fields_json, "
    "original_text, source_reference_id, page, confidence, review_state, verbatim_check, "
    "source_status, originally_proposed_fields_json, edited_fields_json, edit_reason, "
    "reviewed_at, plain_language_text, plain_language_is_verbatim_fallback, created_at"
)


def _loads(text: str | None) -> dict[str, Any] | None:
    return None if text is None else json.loads(text)


def _proposal_from_row(r: tuple) -> ProposalRecord:
    return ProposalRecord(
        proposal_id=r[0],
        document_id=r[1],
        job_id=r[2],
        device_id=r[3],
        proposed_type=r[4],
        proposed_fields=json.loads(r[5]),
        original_text=r[6],
        source_reference_id=r[7],
        page=r[8],
        confidence=r[9],
        review_state=r[10],
        verbatim_check=r[11],
        source_status=r[12],
        originally_proposed_fields=_loads(r[13]),
        edited_fields=_loads(r[14]),
        edit_reason=r[15],
        reviewed_at=_parse(r[16]),
        plain_language_text=r[17],
        plain_language_is_verbatim_fallback=None if r[18] is None else bool(r[18]),
        created_at=_parse(r[19]),
    )


def get_proposal(
    conn: sqlite3.Connection, *, device_id: str, proposal_id: str
) -> ProposalRecord | None:
    row = conn.execute(
        f"SELECT {_PROPOSAL_COLUMNS} FROM proposals WHERE proposal_id = ? AND device_id = ?",
        (proposal_id, device_id),
    ).fetchone()
    return _proposal_from_row(row) if row else None


def list_proposals(
    conn: sqlite3.Connection, *, device_id: str, document_id: str
) -> list[ProposalRecord]:
    """A document's proposals in insertion order; empty for another device's
    document (indistinguishable from none)."""

    rows = conn.execute(
        f"SELECT {_PROPOSAL_COLUMNS} FROM proposals "
        "WHERE document_id = ? AND device_id = ? ORDER BY rowid",
        (document_id, device_id),
    ).fetchall()
    return [_proposal_from_row(r) for r in rows]


def _source_reference_from_row(r: tuple) -> SourceReferenceRecord:
    return SourceReferenceRecord(
        source_reference_id=r[0],
        document_id=r[1],
        page=r[2],
        bbox_pt=(r[3], r[4], r[5], r[6]),
        verbatim_text=r[7],
    )


_SOURCE_REF_SELECT = (
    "SELECT sr.source_reference_id, sr.document_id, sr.page, sr.x0, sr.y0, sr.x1, sr.y1, "
    "sr.verbatim_text FROM source_references sr "
    "JOIN documents d ON d.document_id = sr.document_id "
)


def get_source_reference(
    conn: sqlite3.Connection, *, device_id: str, source_reference_id: str
) -> SourceReferenceRecord | None:
    row = conn.execute(
        _SOURCE_REF_SELECT + "WHERE sr.source_reference_id = ? AND d.device_id = ?",
        (source_reference_id, device_id),
    ).fetchone()
    return _source_reference_from_row(row) if row else None


def list_source_references(
    conn: sqlite3.Connection, *, device_id: str, document_id: str
) -> list[SourceReferenceRecord]:
    rows = conn.execute(
        _SOURCE_REF_SELECT + "WHERE sr.document_id = ? AND d.device_id = ? ORDER BY sr.rowid",
        (document_id, device_id),
    ).fetchall()
    return [_source_reference_from_row(r) for r in rows]


# ---------------------------------------------------------------------------
# AI audit log (PRIV-1652: content-free by construction)
# ---------------------------------------------------------------------------


def record_ai_request(
    conn: sqlite3.Connection,
    *,
    device_id: str,
    job_id: str,
    audit_entry: dict[str, Any],
    now: datetime | None = None,
) -> None:
    """Record one AIRequestLog row from backend.ai.client.results.
    to_audit_log_entry(). The entry's keys must be exactly that projection --
    an extra key is rejected, so free text cannot be smuggled in. The job must
    belong to `device_id` (device_id itself is not stored on the row).
    """

    if set(audit_entry) != _AUDIT_KEYS:
        raise ValueError("audit entry does not match the content-free audit shape")
    if get_job(conn, device_id=device_id, job_id=job_id) is None:
        raise JobNotFoundError("job not found")
    try:
        conn.execute(
            "INSERT INTO ai_request_log (job_id, regime, operation, schema_version, model, "
            "latency_ms, validation_outcome, retry_count, error_class, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                job_id,
                audit_entry["regime"],
                audit_entry["operation"],
                audit_entry["schemaVersion"],
                audit_entry["model"],
                audit_entry["latencyMs"],
                audit_entry["validationOutcome"],
                audit_entry["retryCount"],
                audit_entry["errorClass"],
                to_iso_string(now or _utc_now()),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Deletion (PRIV-1612)
# ---------------------------------------------------------------------------


def delete_document_extraction_data(
    conn: sqlite3.Connection, *, device_id: str, document_id: str
) -> DeletionCounts:
    """Delete one document's jobs, proposals and source references in ONE
    transaction and report the counts. DB-only: the stored PDF and the
    documents row itself are removed by a later task.

    ai_request_log rows are NOT deleted. They hold no document, clinical or
    device data (PRIV-1652 forbids content there; the table has no such
    column), and carry no link to a document or device -- only an opaque
    job_id, which after this call points at nothing. PRIV-1612/PRIV-602
    concern documents and clinical data, which are all removed here, so an
    unlinkable, content-free behaviour log is not "retained clinical data".
    It also preserves the behaviour audit that plan 5.5 asks for.

    Raises DocumentNotFoundError if the document is not this device's.
    """

    _require_document(conn, device_id, document_id)
    try:
        proposals = conn.execute(
            "DELETE FROM proposals WHERE document_id = ? AND device_id = ?",
            (document_id, device_id),
        ).rowcount
        refs = conn.execute(
            "DELETE FROM source_references WHERE document_id = ?", (document_id,)
        ).rowcount
        jobs = conn.execute(
            "DELETE FROM extraction_jobs WHERE document_id = ? AND device_id = ?",
            (document_id, device_id),
        ).rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return DeletionCounts(jobs=jobs, proposals=proposals, source_references=refs)
