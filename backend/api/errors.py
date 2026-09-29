"""The section-2 uniform error envelope, and the full v1 error-code registry.

docs/API_CONTRACT.md section 2 is frozen at v1.0.0: any addition to this list
requires owner approval and a version bump (section 12). This module defines
every v1 code in ONE place so future endpoints reuse it rather than
re-declaring codes ad hoc -- but per this task's scope, only a subset is
actually WIRED to a raisable condition today (see the docstring on each
route in backend/api/main.py). Defining the full list here, unwired, is not
scope creep: it is what "keep the full v1 list defined in one place" means.

D26: `message` is always short, plain-language, and safe to show on a TV --
never document text, extracted values, clinical content, or a prompt/
response body. This module enforces that by construction: the registry
below is the ONLY source of response messages: no call site can inject
arbitrary text into an error body.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("api.errors")


@dataclass(frozen=True)
class ErrorSpec:
    http_status: int
    retryable: bool
    message: str


# The full v1.0.0 error code list, contract section 2. Frozen: do not add,
# remove, or alter an entry without an owner-approved contract version bump.
ERROR_REGISTRY: dict[str, ErrorSpec] = {
    "UNAUTHENTICATED": ErrorSpec(401, False, "Missing or invalid credentials."),
    "DOCUMENT_NOT_FOUND": ErrorSpec(404, False, "That document could not be found."),
    "PROPOSAL_NOT_FOUND": ErrorSpec(404, False, "That proposal could not be found."),
    "JOB_NOT_FOUND": ErrorSpec(404, False, "That extraction job could not be found."),
    "ALREADY_REVIEWED": ErrorSpec(409, False, "That proposal has already been reviewed."),
    "UNKNOWN_FIELD_ID": ErrorSpec(404, False, "That field is not recognised."),
    "PAYLOAD_TOO_LARGE": ErrorSpec(413, False, "That file is larger than the 20 MB limit."),
    "UNSUPPORTED_MEDIA_TYPE": ErrorSpec(415, False, "That file type is not supported."),
    "VALIDATION_ERROR": ErrorSpec(422, False, "That request could not be understood."),
    "TRANSIENT_UPSTREAM_ERROR": ErrorSpec(503, True, "A dependency is temporarily unavailable."),
    "INTERNAL_ERROR": ErrorSpec(500, True, "Something went wrong. Please try again."),
    # EXTRACTION_FAILED is a job-body status value (contract section 5/7),
    # not an HTTP error response -- included here only so the full v1 code
    # list is genuinely enumerated in one place, per this task's requirement.
    "EXTRACTION_FAILED": ErrorSpec(200, True, "Extraction could not complete."),
}


class ContractError(Exception):
    """Raise this anywhere in route/dependency code to produce a section-2
    envelope response. `code` MUST be a key in ERROR_REGISTRY -- this is
    enforced at raise time, not just at response time, so a typo'd code
    fails loudly during development rather than silently 500ing.
    """

    def __init__(self, code: str):
        if code not in ERROR_REGISTRY:
            raise KeyError(f"{code!r} is not a v1 error code (see ERROR_REGISTRY)")
        self.code = code
        super().__init__(code)


def _envelope(code: str) -> dict:
    spec = ERROR_REGISTRY[code]
    return {
        "error": {
            "code": code,
            "message": spec.message,
            "retryable": spec.retryable,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Wire ContractError plus a catch-all into the section-2 envelope shape.

    Deliberately NOT wired here: StarletteHTTPException / unmatched-route
    handling. The v1 error code list has no generic "route not found" or
    "method not allowed" code, and inventing one would be exactly the kind
    of silent contract addition section 12 prohibits. A genuinely unmatched
    route/method therefore still gets FastAPI's own default response, not
    this envelope -- reported as a contract ambiguity, not resolved here.
    """

    @app.exception_handler(ContractError)
    async def _handle_contract_error(request: Request, exc: ContractError) -> JSONResponse:
        spec = ERROR_REGISTRY[exc.code]
        # D26: log the code and path only -- never headers, body, or any
        # request value that could carry a token, pairing code, or content.
        logger.info("contract_error code=%s path=%s", exc.code, request.url.path)
        return JSONResponse(status_code=spec.http_status, content=_envelope(exc.code))

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("validation_error path=%s", request.url.path)
        return JSONResponse(status_code=422, content=_envelope("VALIDATION_ERROR"))

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # D26: log only the exception's class name, never str(exc) -- a
        # message could incidentally contain a value from the request.
        logger.error("unhandled_error type=%s path=%s", type(exc).__name__, request.url.path)
        return JSONResponse(status_code=500, content=_envelope("INTERNAL_ERROR"))
