"""Extraction job orchestrator (extraction T5): runs ONE job, start to finish,
with no HTTP and no scheduling. A later task decides how it is launched (D9).

Pipeline (each stage is a pure/known component already on main):

    stored PDF -> T1 spans -> T2 input -> LlmClient.call_structured
               -> T3 gate -> T4 atomic persist -> audit log -> document state

Guarantees
----------
* FAIL CLOSED (D11/D24): any failure ends the job EXTRACTION_FAILED with a short
  `error_class` and the document EXTRACTION_FAILED. No partial proposals: success
  goes ONLY through `persist_extraction_results` (one transaction that also
  flips the job to COMPLETED), so a failure leaves zero proposals and zero source
  references. An exception can never leave a job RUNNING: the failure handler
  runs for every stage.
* ONE CONNECTION PER RUN: the function opens its own SQLite connection (it is
  meant to run in a worker thread) and closes it. The LlmClient is injected.
* DELETED MID-RUN: if the job or document disappears, the run stops quietly and
  writes nothing (it never resurrects data).
* NO CONTENT IN LOGS (D26/PRIV-1650/1652): logs carry identifiers, counts,
  durations and error classes only -- never span text, values, prompts, model
  output, or `str(exc)`. `error_class` is one of the codes below or an exception
  CLASS NAME, never a message.

error_class values
------------------
Internal codes:  STORAGE_UNAVAILABLE, PDF_UNREADABLE, SPAN_LIMIT, NO_TEXT_LAYER,
                 INPUT_TOO_LARGE, LLM_FAILED_CLOSED.
Class names:     the class name of the exception that stopped the run (for
                 example LlmNotConfiguredError, IntegrityError, TypeError), or,
                 when the model call fails closed, the client's own error class
                 (SchemaValidationError or LlmTransportError).

Documents: one model call per document, all-or-nothing (Q11). A document whose
serialized model input exceeds MAX_INPUT_CHARS fails closed with NO model call
(Q10).
"""

from __future__ import annotations

import json
import logging
import pathlib
import sqlite3
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from backend.ai.assist.document_structuring import OPERATION, SYSTEM_PROMPT, build_input_data
from backend.ai.client.base import LlmClient
from backend.ai.client.results import to_audit_log_entry
from backend.ai.schemas.document_structuring import SCHEMA
from backend.documents.spans import (
    DocumentSpans,
    PdfUnreadableError,
    SpanLimitExceededError,
    extract_spans,
)
from backend.guardrail.extraction_gate import apply_gate
from backend.storage import document_state
from backend.storage import extraction as ex
from backend.storage.db import get_connection

logger = logging.getLogger("extraction.orchestrator")

# Size cap (Q10). Measured on the input EXACTLY as the provider client sends it
# (`json.dumps(input_data)`), in characters. PROVISIONAL pending P5:
# 40,000 characters is roughly 10k tokens of JSON (about 4 chars/token, keys and
# ids included), comfortably inside one model context, small enough for one call
# to finish inside the provisional 60 s client timeout (contract 7, unmeasured),
# and matched to the Anthropic client's 4096-token output ceiling, which limits
# how many proposals a single call can return anyway (~50). Over the cap the job
# fails closed with INPUT_TOO_LARGE and the model is never called.
MAX_INPUT_CHARS = 40_000

ERR_STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
ERR_PDF_UNREADABLE = "PDF_UNREADABLE"
ERR_SPAN_LIMIT = "SPAN_LIMIT"
ERR_NO_TEXT_LAYER = "NO_TEXT_LAYER"
ERR_INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
ERR_LLM_FAILED_CLOSED = "LLM_FAILED_CLOSED"

OUTCOME_COMPLETED = "COMPLETED"
OUTCOME_FAILED = "EXTRACTION_FAILED"
OUTCOME_SKIPPED = "SKIPPED"  # job not found, or not PENDING: nothing was done
OUTCOME_ABANDONED = "ABANDONED"  # job/document deleted mid-run: nothing was written


@dataclass(frozen=True)
class RunOutcome:
    status: str
    error_class: str | None = None
    proposal_count: int = 0
    dropped_count: int = 0


class _Fail(Exception):
    """A controlled failure carrying a content-free error_class."""

    def __init__(self, error_class: str):
        super().__init__(error_class)
        self.error_class = error_class


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _open_connection(db: Callable[[], sqlite3.Connection] | pathlib.Path | str | None) -> sqlite3.Connection:
    if db is None:
        return get_connection()
    if callable(db):
        return db()
    return get_connection(pathlib.Path(db))


def _clock(now: Callable[[], datetime] | datetime | None) -> Callable[[], datetime]:
    if now is None:
        return _utc_now
    if callable(now):
        return now
    return lambda: now


def run_extraction_job(
    job_id: str,
    *,
    device_id: str,
    llm_client: LlmClient,
    db: Callable[[], sqlite3.Connection] | pathlib.Path | str | None = None,
    now: Callable[[], datetime] | datetime | None = None,
) -> RunOutcome:
    """Run one extraction job. Returns a RunOutcome; never raises for a job-level
    failure (those become EXTRACTION_FAILED). `device_id` is the owner of the
    job (the route that created it knows it); every storage call is scoped by it.
    `db` is a database path, or a zero-argument callable returning a NEW
    connection; None uses the default database.
    """

    started = time.monotonic()
    clock = _clock(now)
    conn = _open_connection(db)
    document_id: str | None = None
    llm_meta: dict = {}
    try:
        job = ex.get_job(conn, device_id=device_id, job_id=job_id)
        if job is None or job.status != ex.JOB_PENDING:
            logger.info("extraction_job outcome=skipped job_id=%s", job_id)
            return RunOutcome(status=OUTCOME_SKIPPED)
        document_id = job.document_id

        try:
            outcome = _run(conn, job, device_id, llm_client, clock, llm_meta)
        except (ex.JobNotFoundError, ex.DocumentNotFoundError):
            conn.rollback()
            logger.info("extraction_job outcome=abandoned job_id=%s document_id=%s", job_id, document_id)
            return RunOutcome(status=OUTCOME_ABANDONED)
        except _Fail as failure:
            outcome = _fail(conn, device_id, job_id, document_id, failure.error_class, clock, llm_meta)
        except Exception as exc:  # any stage; class name only, never str(exc)
            outcome = _fail(conn, device_id, job_id, document_id, type(exc).__name__, clock, llm_meta)

        logger.info(
            "extraction_job outcome=%s job_id=%s document_id=%s proposals=%d dropped=%d "
            "error_class=%s duration_ms=%.1f",
            outcome.status,
            job_id,
            document_id,
            outcome.proposal_count,
            outcome.dropped_count,
            outcome.error_class,
            (time.monotonic() - started) * 1000,
        )
        return outcome
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    job: ex.JobRecord,
    device_id: str,
    llm_client: LlmClient,
    clock: Callable[[], datetime],
    llm_meta: dict,
) -> RunOutcome:
    job_id, document_id = job.job_id, job.document_id

    # 1. PENDING -> RUNNING, document EXTRACTING
    try:
        ex.update_job_status(conn, device_id=device_id, job_id=job_id, new_status=ex.JOB_RUNNING, now=clock())
    except ex.IllegalJobTransitionError:
        return RunOutcome(status=OUTCOME_SKIPPED)  # another worker / the sweep got there first
    document_state.set_processing_state(
        conn, device_id=device_id, document_id=document_id, state=document_state.STATE_EXTRACTING
    )

    # 2. stored PDF (path from the DB record only, guarded, inside the storage dir)
    stored_filename = document_state.get_stored_filename(conn, device_id=device_id, document_id=document_id)
    try:
        pdf_bytes = document_state.read_stored_file(stored_filename)
    except document_state.StoredFileUnavailableError:
        raise _Fail(ERR_STORAGE_UNAVAILABLE) from None

    # 3. T1 spans
    try:
        spans = extract_spans(pdf_bytes)
    except PdfUnreadableError:
        raise _Fail(ERR_PDF_UNREADABLE) from None
    except SpanLimitExceededError:
        raise _Fail(ERR_SPAN_LIMIT) from None
    if not _has_text_layer(spans):
        raise _Fail(ERR_NO_TEXT_LAYER)

    # 4. size cap (Q10): checked BEFORE any model call
    input_data = build_input_data(spans)
    if len(json.dumps(input_data)) > MAX_INPUT_CHARS:
        raise _Fail(ERR_INPUT_TOO_LARGE)

    # 5. one model call (D11 retry / fail-closed live inside call_structured)
    result = llm_client.call_structured(
        operation=OPERATION,
        schema=SCHEMA,
        system_prompt=SYSTEM_PROMPT,
        input_data=input_data,
    )
    llm_meta.update(model=result.model, schema_version=result.schema_version, retry_count=result.retry_count)
    ex.record_ai_request(
        conn, device_id=device_id, job_id=job_id, audit_entry=to_audit_log_entry(result), now=clock()
    )
    if result.failed_closed:
        raise _Fail(result.error_class or ERR_LLM_FAILED_CLOSED)

    # 6. T3 gate, then ONE transaction: proposals + source refs + job COMPLETED
    gated = apply_gate(spans, result.output)
    references: list[ex.NewSourceReference] = []
    proposals: list[ex.NewProposal] = []
    for draft in gated.proposals:
        # One source_references row PER proposal, each with its own UUID v4,
        # even when two proposals cite the same span.
        reference = ex.NewSourceReference(
            page=draft.page,
            bbox_pt=draft.bbox_pt,
            verbatim_text=draft.verbatim_text,
            source_reference_id=str(uuid.uuid4()),
        )
        references.append(reference)
        proposals.append(
            ex.NewProposal(
                proposed_type=draft.proposed_type,
                proposed_fields=draft.fields,
                original_text=draft.original_text,
                source_reference_id=reference.source_reference_id,
                page=draft.page,
                confidence=draft.confidence,
                review_state=draft.review_state,
                verbatim_check=draft.verbatim_check,
                source_status=draft.source_status,
            )
        )
    ex.persist_extraction_results(
        conn,
        device_id=device_id,
        job_id=job_id,
        source_references=references,
        proposals=proposals,
        model=result.model,
        schema_version=result.schema_version,
        retry_count=result.retry_count,
        document_date=gated.document_date,
        now=clock(),
    )

    # 7. document state. `processing_state` is a denormalized copy of "latest job
    # COMPLETED" (contract 3.2); the job is already durably COMPLETED, so a
    # failure here must not turn a finished job into a failed one.
    try:
        document_state.set_processing_state(
            conn, device_id=device_id, document_id=document_id, state=document_state.STATE_PROPOSALS_READY
        )
    except ex.DocumentNotFoundError:
        raise
    except Exception as exc:
        logger.error(
            "extraction_job document_state_update_failed job_id=%s document_id=%s error_class=%s",
            job_id,
            document_id,
            type(exc).__name__,
        )
    return RunOutcome(
        status=OUTCOME_COMPLETED,
        proposal_count=len(proposals),
        dropped_count=gated.dropped_count,
    )


def _has_text_layer(spans: DocumentSpans) -> bool:
    return any(page.has_text_layer for page in spans.pages)


def _fail(
    conn: sqlite3.Connection,
    device_id: str,
    job_id: str,
    document_id: str,
    error_class: str,
    clock: Callable[[], datetime],
    llm_meta: dict,
) -> RunOutcome:
    """End the job EXTRACTION_FAILED and the document EXTRACTION_FAILED. Every
    step is guarded so that a failure here cannot mask the original error, and a
    job/document that has meanwhile been deleted is left alone."""

    try:
        conn.rollback()  # discard anything half-written by the failed stage
    except Exception:
        pass
    try:
        ex.update_job_status(
            conn,
            device_id=device_id,
            job_id=job_id,
            new_status=ex.JOB_FAILED,
            now=clock(),
            error_class=error_class,
            retry_count=llm_meta.get("retry_count"),
            model=llm_meta.get("model"),
            schema_version=llm_meta.get("schema_version"),
        )
    except (ex.JobNotFoundError, ex.IllegalJobTransitionError):
        pass  # deleted, or already terminal (for example swept): leave it
    except Exception as exc:
        logger.error(
            "extraction_job fail_transition_failed job_id=%s error_class=%s", job_id, type(exc).__name__
        )
    try:
        document_state.set_processing_state(
            conn, device_id=device_id, document_id=document_id, state=document_state.STATE_EXTRACTION_FAILED
        )
    except ex.DocumentNotFoundError:
        pass
    except Exception as exc:
        logger.error(
            "extraction_job fail_state_update_failed job_id=%s error_class=%s", job_id, type(exc).__name__
        )
    return RunOutcome(status=OUTCOME_FAILED, error_class=error_class)
