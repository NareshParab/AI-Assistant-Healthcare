# API Contract — AI Assistant Healthcare Backend

**STATUS: DRAFT v1.0.0 — awaiting owner approval to freeze. NOT FROZEN.**

This document is a proposal for review, not a commitment either developer may build
against as final. The owner freezes it by explicit approval; until then, treat every shape
in this document as provisional.

| | |
|---|---|
| **Date drafted** | 2026-09-29 |
| **Source of truth** | `ARCHITECTURE_MVP_PLAN.md` §4 (API Design), §5 (AI Architecture), §6 (Document Pipeline), §7.3 (routine validation), and `PROJECT_MASTER_SPEC.md` (SAFE-501, SAFE-916, SAFE-1410, SAFE-1807, PRIV-1620, PRIV-1652) |
| **Repo state this draft was written against** | `main` @ `f9b7f38760f4824bab7482136d0bf86748557b29` |
| **Author** | Drafted per owner task; not self-approved |

This document does not modify `PROJECT_MASTER_SPEC.md`, `PROJECT_REVIEW.md`, or
`ARCHITECTURE_MVP_PLAN.md`. Where this draft cites those documents, the citation is a
pointer, not a restatement with authority of its own.

---

## 1. Conventions

| Convention | Value |
|---|---|
| Base path | `/v1` |
| Transport | **HTTPS only** — plaintext HTTP is not a valid deployment target (`PRIV-1620`) |
| Body format | JSON (`application/json`) for all requests and non-binary responses |
| Timestamps | ISO-8601, UTC, e.g. `2026-09-29T10:57:18Z` |
| Auth | Device-token, sent as a single HTTP header on every request except `/v1/health`. **Header name is OPEN — see §11.** No accounts, no login, no per-user credential (D22) |
| Idempotency | `POST /v1/documents/{id}/extract` is idempotent per document: calling it again while a job is already `PENDING`/`RUNNING` for that document returns the existing job, not a second job. `POST /v1/proposals/{id}/review` is **not** idempotent — reviewing an already-reviewed proposal returns `409 Conflict`. All other `POST` endpoints are not idempotent (each call is a new, independent generation) |
| Pagination | None of the 16 endpoints below return an unbounded list; document/proposal lists are scoped to one device's own documents, which is expected to stay small. No pagination scheme is defined in this draft |

### 1.1 What the client never holds

Per D25/`PRIV-1640`: the client (Fire TV app or companion) **never holds, stores, or
transmits an AI provider credential**. `ANTHROPIC_API_KEY` exists only as a server-side
environment variable, read once by `backend/ai/client/anthropic_client.py`. No endpoint in
this contract accepts, returns, or echoes that variable, any other credential, or any
provider-specific request/response body (`PRIV-1652`).

---

## 2. Uniform error model

Every non-2xx response body has this exact shape:

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "That document could not be found.",
    "retryable": false
  }
}
```

| Field | Type | Rule |
|---|---|---|
| `code` | string, `UPPER_SNAKE_CASE` | Machine-readable. Stable across versions once frozen |
| `message` | string | Short, plain language, **safe to render on a TV**. Never document text, never extracted values, never clinical content, never a prompt or response body (D26) |
| `retryable` | boolean | `true` if an identical retry might succeed (e.g. transient network); `false` if retrying without changing the request cannot help (e.g. validation error, not-found) |

**The starter error code list below is a proposal, not exhaustive — see §11 (OPEN:
error code list).**

| Code | HTTP status | retryable | Meaning |
|---|---|---|---|
| `UNAUTHENTICATED` | 401 | false | Missing or invalid device token |
| `DOCUMENT_NOT_FOUND` | 404 | false | No document with that id for this device token |
| `PROPOSAL_NOT_FOUND` | 404 | false | No proposal with that id |
| `JOB_NOT_FOUND` | 404 | false | No extraction job with that id |
| `ALREADY_REVIEWED` | 409 | false | The proposal has already been confirmed/edited/discarded |
| `UNKNOWN_FIELD_ID` | 404 | false | Wellness/field lookup for an id that does not exist (POC-era; see §8) |
| `PAYLOAD_TOO_LARGE` | 413 | false | Document upload exceeds the size limit (§11 OPEN) |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | false | Uploaded file is not a text-layer PDF (D7) |
| `VALIDATION_ERROR` | 422 | false | Request body failed schema validation |
| `EXTRACTION_FAILED` | 200 (in job body) | true | Extraction could not complete; see §5 |
| `TRANSIENT_UPSTREAM_ERROR` | 503 | true | The backend's own dependency (e.g. AI provider) failed transiently |
| `INTERNAL_ERROR` | 500 | true | Unclassified server error |

---

## 3. The 16 endpoints

**Finding, reported plainly rather than silently reconciled**: `ARCHITECTURE_MVP_PLAN.md`
§4 states *"Eighteen endpoints"* in its own prose, but its own table lists **16** distinct
`(method, path)` rows — verified by direct count. This draft documents the **16 endpoints
that are actually specified**. It does not invent two more to match the prose count. See
§11, OPEN question 1.

Grouped exactly as §4 groups them.

### 3.1 Devices

#### `POST /v1/devices/register`

| | |
|---|---|
| Purpose | Issue a device token on first run |
| Regime | none |
| Tier (D20) | 2 (network required — there is no device identity without it) |
| Fallback (D24) | None specified in the plan. **OPEN — see §11** |

**Request**
```json
{}
```
*(No fields specified by the plan. This draft proposes an empty body; the server assigns
and returns a new token. OPEN if any client metadata should be sent — see §11.)*

**Response `201 Created`**
```json
{
  "deviceToken": "SYNTHETIC-8f14e45f-ceea-467e-bd97-11example0001",
  "issuedAt": "2026-09-29T10:00:00Z"
}
```

**Status codes:** `201` created. `500` `INTERNAL_ERROR`.

---

#### `POST /v1/devices/pairing-code`

| | |
|---|---|
| Purpose | Create a short pairing code for the companion (D22) |
| Regime | none |
| Tier (D20) | 2 |
| Fallback (D24) | None specified. **OPEN — see §11** |

**Request** (device token header required)
```json
{}
```

**Response `201 Created`**
```json
{
  "pairingCode": "7X9K2Q",
  "expiresAt": "2026-09-29T10:15:00Z"
}
```

D22 specifies the code is **6 characters**; this draft's example matches that. The
**expiry duration is not specified by the plan** (it says only "short-lived pairing
record" and, separately, "long-lived demo codes" for the hackathon demo specifically —
these are not the same number). **OPEN — see §11.**

**Status codes:** `201` created. `401` `UNAUTHENTICATED`. `500` `INTERNAL_ERROR`.

---

### 3.2 Documents

#### `POST /v1/documents`

| | |
|---|---|
| Purpose | Upload a document (from the companion, or a seeded/bundled document) |
| Regime | none (no AI runs on upload itself) |
| Tier (D20) | 2 |
| Fallback (D24) | None specified. **OPEN — see §11** |

**Request:** `multipart/form-data` with one file field, `file`, containing a text-layer PDF
(D7 — no OCR, no scanned images accepted in this MVP).

**Response `201 Created`**
```json
{
  "documentId": "SYNTHETIC-doc-0001",
  "name": "synthetic_prescription.pdf",
  "documentType": "prescription",
  "receivedAt": "2026-09-29T10:05:00Z",
  "processingState": "RECEIVED",
  "pageCount": 1
}
```

**Status codes:** `201` created. `401` `UNAUTHENTICATED`. `413` `PAYLOAD_TOO_LARGE`. `415`
`UNSUPPORTED_MEDIA_TYPE`. `500` `INTERNAL_ERROR`.

Upload size limit is **not specified anywhere in the plan. OPEN — see §11.**

---

#### `GET /v1/documents`

| | |
|---|---|
| Purpose | List documents with processing and review state, scoped to this device token |
| Regime | none |
| Tier (D20) | 2 (listing requires reaching the server; the confirmed plan itself is device-local per D6 and needs no server call) |
| Fallback (D24) | None specified. Tier-2 network-unavailable messaging applies (D20 row 3) |

**Response `200 OK`**
```json
{
  "documents": [
    {
      "documentId": "SYNTHETIC-doc-0001",
      "name": "synthetic_prescription.pdf",
      "documentType": "prescription",
      "receivedAt": "2026-09-29T10:05:00Z",
      "processingState": "PROPOSALS_READY",
      "pageCount": 1
    }
  ]
}
```

**Status codes:** `200` ok (including an empty `documents: []`). `401` `UNAUTHENTICATED`.

---

#### `GET /v1/documents/{id}`

| | |
|---|---|
| Purpose | Document detail |
| Regime | none |
| Tier (D20) | 2 |
| Fallback (D24) | None specified |

**Response `200 OK`**
```json
{
  "documentId": "SYNTHETIC-doc-0001",
  "name": "synthetic_prescription.pdf",
  "documentType": "prescription",
  "receivedAt": "2026-09-29T10:05:00Z",
  "processingState": "PROPOSALS_READY",
  "pageCount": 1
}
```

**Status codes:** `200` ok. `401` `UNAUTHENTICATED`. `404` `DOCUMENT_NOT_FOUND`.

---

#### `GET /v1/documents/{id}/pages/{n}/render`

**This is the D16 evidence surface — the single most important endpoint in the product.**
It is grounded directly in the already-implemented `backend/documents/pdf_evidence.py`
(`find_evidence_span` + `render_evidence_image`), verified by reading that module.

| | |
|---|---|
| Purpose | Return the rendered page image, optionally with a highlighted region, cropped and zoomed |
| Regime | none (pure rendering; no AI call) |
| Tier (D20) | 2 for a document the server hasn't rendered before; the client should cache the returned image so re-viewing an already-confirmed item works offline (Tier 0 per §14.7's evidence caching note) |
| Fallback (D24) | None specified for this exact endpoint. If rendering fails, `500` with a plain message; there is no partial-image fallback |

**Query parameters:**

| Param | Required | Meaning |
|---|---|---|
| `highlight` | no | A `sourceReferenceId` (see §6) identifying the span to highlight. Omit to get the plain page render |
| `crop` | no | `true` (default) or `false`. When `true`, returns a cropped, zoomed region around the highlight rather than the full page — matches `render_evidence_image`'s existing `zoom=3.0`, `crop_padding_pt=36.0` behaviour |

**Response `200 OK`, `Content-Type: image/png`** — raw PNG bytes, not JSON. No example body
(binary). Dimensions are not fixed: a cropped render's size depends on the located span's
bounding box plus padding (as implemented today); the full-page render is a fixed
`page_width_pt * zoom` by `page_height_pt * zoom` in pixels.

**Status codes:** `200` ok (PNG body). `401` `UNAUTHENTICATED`. `404` `DOCUMENT_NOT_FOUND`
or "page does not exist" (mirrors `EvidenceNotFoundError` for an out-of-range page,
confirmed in `pdf_evidence.py:55-58`). `422` if `highlight` names a `sourceReferenceId`
that does not resolve to a span on this page (mirrors `EvidenceNotFoundError` when
`page.search_for` finds nothing, confirmed at `pdf_evidence.py:60-62`).

---

### 3.3 Extraction

#### `POST /v1/documents/{id}/extract`

| | |
|---|---|
| Purpose | Start extraction; returns a job id (D9) |
| Regime | **ASSIST** (`assist.document_structuring`, per `backend/ai/client/operations.py:31`) |
| Tier (D20) | 2 |
| Fallback (D24) | On failure: mark the document `EXTRACTION_FAILED`; offer retry; **no partial proposals are ever returned** |

**Request**
```json
{}
```

**Response `202 Accepted`**
```json
{
  "jobId": "SYNTHETIC-job-0001",
  "documentId": "SYNTHETIC-doc-0001",
  "status": "PENDING"
}
```

Calling this again for the same document while a job is already `PENDING`/`RUNNING`
returns the **existing** job with `200 OK` instead of creating a second one (idempotency,
§1).

**Status codes:** `202` accepted (new job). `200` ok (existing job returned). `401`
`UNAUTHENTICATED`. `404` `DOCUMENT_NOT_FOUND`.

---

#### `GET /v1/extraction-jobs/{id}`

The job-and-poll contract in full is in §7.

| | |
|---|---|
| Purpose | Poll status; on completion, returns proposals |
| Regime | ASSIST (reports on an ASSIST operation's progress) |
| Tier (D20) | 2 |
| Fallback (D24) | `EXTRACTION_FAILED` terminal state, no partial output |

**Response `200 OK` — while running**
```json
{
  "jobId": "SYNTHETIC-job-0001",
  "documentId": "SYNTHETIC-doc-0001",
  "status": "RUNNING",
  "proposals": null
}
```

**Response `200 OK` — completed successfully**
```json
{
  "jobId": "SYNTHETIC-job-0001",
  "documentId": "SYNTHETIC-doc-0001",
  "status": "COMPLETED",
  "proposals": [
    {
      "proposalId": "SYNTHETIC-prop-0001",
      "proposedType": "MEDICATION",
      "proposedFields": {
        "medicineName": "Tab. Ecosprin",
        "doseText": "Tab. Ecosprin 75mg -- 1 tablet before breakfast"
      },
      "sourceReferenceId": "SYNTHETIC-ref-0001",
      "page": 0,
      "confidence": 0.94,
      "reviewState": "PROPOSED"
    }
  ]
}
```

**Response `200 OK` — failed (D24)**
```json
{
  "jobId": "SYNTHETIC-job-0001",
  "documentId": "SYNTHETIC-doc-0001",
  "status": "EXTRACTION_FAILED",
  "proposals": null
}
```

**Status codes:** `200` ok for every state above (the job resource always exists once
created; failure is a status value, not an HTTP error). `401` `UNAUTHENTICATED`. `404`
`JOB_NOT_FOUND`.

---

#### `GET /v1/documents/{id}/proposals`

| | |
|---|---|
| Purpose | Proposals with `sourceReferenceId` and confidence, for a document whose extraction has already completed |
| Regime | ASSIST |
| Tier (D20) | 2 |
| Fallback (D24) | None specified beyond the job's own `EXTRACTION_FAILED` state |

**Response `200 OK`** — same `proposals` array shape as the completed-job response above.

**Status codes:** `200` ok. `401` `UNAUTHENTICATED`. `404` `DOCUMENT_NOT_FOUND`.

---

### 3.4 Verification

#### `POST /v1/proposals/{id}/review`

**This is the confirmation gate — SAFE-501's enforcement point.** No extracted item may
affect a device's plan until a human confirms it here.

| | |
|---|---|
| Purpose | Record confirm / edit / discard / unclear; return the confirmed payload for device persistence |
| Regime | ASSIST — the plain-language pre-generation (D10) triggered by a `confirm`/`edit` action is `assist.plain_language` |
| Tier (D20) | 2 to submit the review itself; the resulting confirmed data is written device-side and thereafter lives at Tier 0 |
| Fallback (D24) | Plain-language pre-generation fallback: **verbatim original text only** — always safe, never blocks the confirmation itself |

**Request — `confirm`**
```json
{
  "action": "confirm"
}
```

**Request — `edit`**
```json
{
  "action": "edit",
  "editedFields": {
    "doseText": "Tab. Ecosprin 75mg -- 1 tablet before breakfast, with water"
  },
  "reason": "Clarified with the confirming caregiver"
}
```

The exact shape of `editedFields` (a free-form patch of `proposedFields`, versus a
fully-specified replacement object) is **not fixed by the plan. OPEN — see §11.** This
draft proposes a free-form partial patch, matching `proposedFields`' own shape.

**Request — `discard`**
```json
{
  "action": "discard"
}
```

**Request — `unclear`**
```json
{
  "action": "unclear"
}
```

**Response `200 OK` (confirm/edit)**
```json
{
  "proposalId": "SYNTHETIC-prop-0001",
  "reviewState": "CONFIRMED",
  "confirmedInstruction": {
    "instructionType": "MEDICATION",
    "medicineName": "Tab. Ecosprin",
    "doseTextAsTranscribed": "Tab. Ecosprin 75mg -- 1 tablet before breakfast",
    "originalText": "Medication: Tab. Ecosprin 75mg -- 1 tablet before breakfast",
    "sourceDocumentId": "SYNTHETIC-doc-0001",
    "sourceReferenceId": "SYNTHETIC-ref-0001",
    "plainLanguage": {
      "text": "Tab. Ecosprin 75mg -- 1 tablet before breakfast",
      "isVerbatimFallback": false
    }
  }
}
```

`plainLanguage.isVerbatimFallback: true` signals the D24 fallback fired (the confirmed
`text` equals `originalText` verbatim, not a genuine simplification) — the client can
distinguish the two cases without inspecting the text itself.

**Response `200 OK` (discard)**
```json
{
  "proposalId": "SYNTHETIC-prop-0001",
  "reviewState": "DISCARDED"
}
```

**Response `200 OK` (unclear)**
```json
{
  "proposalId": "SYNTHETIC-prop-0001",
  "reviewState": "UNCLEAR"
}
```

**Status codes:** `200` ok. `401` `UNAUTHENTICATED`. `404` `PROPOSAL_NOT_FOUND`. `409`
`ALREADY_REVIEWED`. `422` `VALIDATION_ERROR` (unknown `action` value, or malformed
`editedFields`).

---

### 3.5 Wellness

#### `POST /v1/routines/generate`

Grounded directly in `backend/guardrail/routine_validator.py` (`validate_routine`,
`RoutineSegment`) and `shared/movement-catalog/catalog.json` (`catalogVersion: "1.0.0"`,
verified by reading both files).

| | |
|---|---|
| Purpose | Return a validated routine of catalog movement IDs, or a preset fallback |
| Regime | **GUIDE** (`guide.routine_generation`, per `operations.py:37`) |
| Tier (D20) | 1 — network preferred; falls back to a vetted preset |
| Fallback (D24) | Generation or validation failure → **offer a vetted preset** of the requested duration from the catalog |

**Request**
```json
{
  "requestedBudgetSec": 900,
  "goal": "ENERGIZE",
  "preferences": ["seated_preferred"],
  "activePrecautionTags": ["no_neck_movement"]
}
```

**Response `200 OK` — generated and validated**
```json
{
  "origin": "GENERATED",
  "catalogVersion": "1.0.0",
  "requestedBudgetSec": 900,
  "totalDurationSec": 870,
  "validationResult": {
    "passed": true,
    "failureReasons": []
  },
  "segments": [
    { "movementId": "warmup_seated_shoulder_rolls", "durationSec": 45 },
    { "movementId": "mob_shoulder_circles_seated", "durationSec": 60 },
    { "movementId": "breathing_seated_diaphragmatic", "durationSec": 60 }
  ]
}
```

**Response `200 OK` — validation failed, preset served (D24)**
```json
{
  "origin": "PRESET",
  "catalogVersion": "1.0.0",
  "requestedBudgetSec": 900,
  "totalDurationSec": 900,
  "validationResult": {
    "passed": true,
    "failureReasons": []
  },
  "segments": [
    { "movementId": "warmup_seated_shoulder_rolls", "durationSec": 60 },
    { "movementId": "mob_seated_torso_twist_gentle", "durationSec": 780 },
    { "movementId": "breathing_seated_slow_count_breathing", "durationSec": 60 }
  ]
}
```

The client distinguishes a genuine GUIDE-generated routine from a fallback preset via
`origin`. **`failureReasons` on the original (failed) generation attempt is not exposed to
the client in this draft** — only the fact that a preset was served. Exposing the internal
failure reason was judged unnecessary for the client and a potential minor information
leak about the model's behaviour; **OPEN if the owner wants it exposed anyway — see §11.**

**A note on presets**: this endpoint's `PRESET` response shape assumes hand-authored 10/15/
20-minute presets exist per plan §7.4. **As of `f9b7f38`, no preset content exists anywhere
in the repository** (verified: no file under `shared/movement-catalog/` or elsewhere
defines presets). This endpoint is therefore documented as **NOT YET IMPLEMENTED** — see
§9.

**Status codes:** `200` ok (both origins). `401` `UNAUTHENTICATED`. `422`
`VALIDATION_ERROR` (malformed request body itself, distinct from a GUIDE-generation
failure, which is handled internally via the preset fallback, not surfaced as a 4xx).

---

#### `GET /v1/catalog`

| | |
|---|---|
| Purpose | Catalog version check — the catalog's *content* is bundled with the client (D17), not fetched here |
| Regime | none |
| Tier (D20) | 1 (a version check is a convenience; the bundled catalog keeps wellness working fully offline at Tier 0) |
| Fallback (D24) | Network unavailable → client trusts its bundled `catalogVersion` |

**Response `200 OK`**
```json
{
  "catalogVersion": "1.0.0"
}
```

**Status codes:** `200` ok.

---

### 3.6 AI — bounded

#### `POST /v1/assist/plain-language`

| | |
|---|---|
| Purpose | ASSIST transform of one confirmed instruction's own text. Normally called once, at confirmation time (D10), not on every view |
| Regime | **ASSIST** (`assist.plain_language`, `operations.py:32`) |
| Tier (D20) | 1 (pre-generated and cached device-side at confirmation; a live call to this endpoint after that point is a re-generation, not required for normal use) |
| Fallback (D24) | **Verbatim original text only** — always safe |

**Request**
```json
{
  "originalText": "Medication: Tab. Ecosprin 75mg -- 1 tablet before breakfast",
  "instructionType": "MEDICATION"
}
```

**Response `200 OK` — genuine transform**
```json
{
  "text": "Take one Ecosprin 75mg tablet before you eat breakfast.",
  "isVerbatimFallback": false
}
```

**Response `200 OK` — fallback fired**
```json
{
  "text": "Medication: Tab. Ecosprin 75mg -- 1 tablet before breakfast",
  "isVerbatimFallback": true
}
```

**Status codes:** `200` ok (always — this endpoint cannot fail from the client's
perspective, because its own fallback is defined as always-safe). `401`
`UNAUTHENTICATED`. `422` `VALIDATION_ERROR` (missing `originalText`).

---

#### `POST /v1/summary/interpretation`

| | |
|---|---|
| Purpose | Generate Daily Summary region 4 only, from region-1/region-2 inputs (SAFE-1807: no value may appear in region 4 that isn't already in region 1 or 2) |
| Regime | **ASSIST** (`assist.summary_interpretation`, `operations.py:33`) |
| Tier (D20) | 1 |
| Fallback (D24) | **Omit region 4 entirely**; regions 1–3 render regardless (safe by SAFE-1410's structural separation) |

**Request**
```json
{
  "region1RecordedFacts": ["Morning medication marked taken at 08:12"],
  "region2HistoricalInfo": [
    { "measure": "blood_pressure_systolic", "value": 128, "observedAt": "2026-08-12" }
  ]
}
```

**Response `200 OK` — generated**
```json
{
  "region4AiInterpretation": "Today's morning medication was completed on schedule.",
  "omitted": false
}
```

**Response `200 OK` — omitted (D24)**
```json
{
  "region4AiInterpretation": null,
  "omitted": true
}
```

**Status codes:** `200` ok (always — this endpoint's own contract guarantees a safe
result). `401` `UNAUTHENTICATED`. `422` `VALIDATION_ERROR`.

---

#### `POST /v1/requests/interpret`

| | |
|---|---|
| Purpose | Parse a wellness request (budget, goal, preferences); **refuse** out-of-scope clinical requests (SAFE-916) |
| Regime | **GUIDE** (`guide.request_interpretation`, `operations.py:36`) for in-scope requests. A refusal is a guardrail decision, not itself an AI regime's output |
| Tier (D20) | 1 |
| Fallback (D24) | Out-of-scope request → brief warm refusal + redirect to the clinician, never a partial answer first |

**Request**
```json
{
  "utterance": "I have 15 minutes before work, give me something to wake me up"
}
```

**Response `200 OK` — in-scope**
```json
{
  "outcome": "INTERPRETED",
  "requestedBudgetSec": 900,
  "goal": "ENERGIZE",
  "preferences": []
}
```

**Response `200 OK` — refused (SAFE-916)**
```json
{
  "outcome": "REFUSED",
  "refusalMessage": "That's something to check with your doctor or care team.",
  "requestedBudgetSec": null,
  "goal": null,
  "preferences": null
}
```

The client checks `outcome` to distinguish an interpretable wellness request from a
refusal; it never has to guess by inspecting the fields for `null`.

**Status codes:** `200` ok (both outcomes — a refusal is not an HTTP error, it's a valid,
safe result). `401` `UNAUTHENTICATED`. `422` `VALIDATION_ERROR` (missing `utterance`).

---

### 3.7 Health / diagnostics

#### `GET /v1/health`

| | |
|---|---|
| Purpose | Liveness, for the client's degraded-mode banner |
| Regime | none |
| Tier (D20) | N/A — this endpoint's only job is to report whether Tier 1/2 features are reachable; its own absence of a response IS the signal |
| Fallback (D24) | None needed; a failed call to this endpoint is itself the "network unavailable" signal |
| Auth | **Does not require the device-token header** — a client must be able to check liveness before it has a token |

**Response `200 OK`**
```json
{
  "status": "ok"
}
```

**Status codes:** `200` ok. (No error responses are meaningful for this endpoint; if the
server cannot respond at all, that is a connection failure, not a JSON error body.)

---

## 4. Fallback and fail-closed semantics, summarized

| Endpoint | Distinguishing field | Values the client must branch on |
|---|---|---|
| `POST /v1/routines/generate` | `origin` | `GENERATED` vs `PRESET` — both carry `validationResult` and `catalogVersion`; the client never needs to re-validate, only to know which one it got |
| `POST /v1/assist/plain-language` | `isVerbatimFallback` | `false` = genuine transform, `true` = D24 fallback fired |
| `POST /v1/summary/interpretation` | `omitted` | `false` = region 4 present, `true` = region 4 must not render at all (not even an empty state — absent) |
| `POST /v1/requests/interpret` | `outcome` | `INTERPRETED` vs `REFUSED` |
| `GET /v1/extraction-jobs/{id}` | `status` | `PENDING` / `RUNNING` / `COMPLETED` / `EXTRACTION_FAILED` — the last carries `proposals: null`, never a partial list |

No endpoint in this contract can return an ASSIST or GUIDE result that bypasses
`backend/guardrail/` validation (D14): `routines/generate` always runs the routine through
`validate_routine` before choosing between `GENERATED` and `PRESET`; the ASSIST endpoints'
only failure mode is falling back to verbatim/omitted, never emitting unvalidated model
output.

---

## 5. Proposal and evidence shapes

### `ExtractedField` (server-side name for one proposal)

| Field | Type | Notes |
|---|---|---|
| `proposalId` | string | Server-assigned identifier |
| `proposedType` | string | e.g. `MEDICATION`, `PRESCRIBED_ACTIVITY`, `MEAL_INSTRUCTION`, `PRECAUTION`, `APPOINTMENT` (per `CareInstruction` subtypes) |
| `proposedFields` | object | Type-specific fields, e.g. `medicineName`, `doseText` for `MEDICATION`. **Dose text is always verbatim, never normalized or recomputed (SAFE-504)** |
| `sourceReferenceId` | string | Identifies the exact page + bounding box this proposal came from; pass this to `pages/{n}/render?highlight=` |
| `page` | integer | 0-indexed, matches the PDF page the span is on |
| `confidence` | number | `0.0`–`1.0`. **Exact scale/meaning not fixed by the plan — OPEN, see §11** |
| `reviewState` | string | `PROPOSED` or `UNCLEAR` — **only these two values exist server-side before a human acts.** `CONFIRMED`/`EDITED_CONFIRMED`/`DISCARDED` only exist after `POST /proposals/{id}/review` |

### Evidence image contract (`GET /v1/documents/{id}/pages/{n}/render`)

| Property | Value |
|---|---|
| Content-Type | `image/png` |
| Cropping | `crop=true` (default): region is the highlighted span's bounding box **expanded by 36pt of padding on every side** (matches `pdf_evidence.py`'s `DEFAULT_CROP_PADDING_PT = 36.0`), clamped to the page. `crop=false`: full page |
| Zoom | 3x the PDF's native 72dpi (matches `DEFAULT_ZOOM = 3.0`), i.e. ~216 DPI |
| Highlight style | Translucent yellow fill, red border — matches the already-implemented constants `HIGHLIGHT_FILL`/`HIGHLIGHT_BORDER` in `pdf_evidence.py` |
| Dimensions | Not fixed; varies with the span's size and the page size. Client must not assume a fixed image size |

---

## 6. `sourceReferenceId`

A `sourceReferenceId` uniquely identifies one located span: a `(documentId, page, bbox)`
triple, server-side. It is opaque to the client — the client never constructs one, only
passes back one it was given, either to highlight a render or to trace a confirmed
instruction to its evidence. **Exact string format (UUID vs composite key) is not fixed by
the plan — OPEN, see §11.**

---

## 7. Job-and-poll contract (D9)

Applies to `POST /v1/documents/{id}/extract` + `GET /v1/extraction-jobs/{id}` only — the
**only** asynchronous pair in this contract. Every other endpoint is synchronous (D9).

| State | Meaning | Terminal? |
|---|---|---|
| `PENDING` | Job created, not yet started | no |
| `RUNNING` | Extraction in progress | no |
| `COMPLETED` | Proposals available, `proposals` populated | **yes** |
| `EXTRACTION_FAILED` | D24 fallback fired; `proposals: null`, never partial | **yes** |

**Poll interval guidance**: not specified by the plan. This draft recommends **2 seconds**,
matching the "honest, determinate progress state" language in D9/`PROD-439` without being
so frequent it's chatty for no benefit. **OPEN — see §11.**

**Timeout behaviour**: not specified by the plan. This draft recommends the **client**
impose a timeout (e.g. 60 seconds of polling) and show a non-alarming "this is taking
longer than expected, try again" state — the server itself does not time out a job, it
either completes or fails per D24. **OPEN — see §11.**

---

## 8. Implemented vs. Specified

Verified by reading `backend/api/main.py` directly and by importing the FastAPI `app`
object and enumerating `app.routes` offline (no server started):

```
['GET', 'HEAD'] /openapi.json          (FastAPI auto-generated, not part of this contract)
['GET', 'HEAD'] /docs                  (FastAPI auto-generated, not part of this contract)
['GET', 'HEAD'] /docs/oauth2-redirect  (FastAPI auto-generated, not part of this contract)
['GET', 'HEAD'] /redoc                 (FastAPI auto-generated, not part of this contract)
['GET']         /v1/health
['GET']         /v1/poc/p4/evidence
['GET']         /v1/poc/p4/fields
```

| Contract endpoint | Implementation status |
|---|---|
| `GET /v1/health` | **Matches.** `backend/api/main.py:60-62` returns exactly `{"status": "ok"}` |
| `GET /v1/documents/{id}/pages/{n}/render` | **NOT YET IMPLEMENTED** as this exact route. A functionally-related POC route exists at `GET /v1/poc/p4/evidence?field=<id>` (`main.py:65-93`), which locates one of five hardcoded field ids in one bundled demo document and returns a cropped, highlighted PNG. It proves the *mechanism* this contract's endpoint depends on (backed by the same `pdf_evidence.py` module) but takes a different, non-contract-shaped parameter (`field`, not `id`/`n`/`highlight`) and has no document/page/sourceReferenceId model behind it |
| All other 14 endpoints (devices, documents CRUD, extraction, review, routines, catalog, assist, summary, requests) | **NOT YET IMPLEMENTED.** No route, no handler, no request/response model exists for any of them in `backend/api/main.py` as of `f9b7f38` |
| `GET /v1/poc/p4/fields` | **Not part of this contract.** POC-only, scoped under `/v1/poc/`, explicitly excluded from the frozen API surface by its own namespace |

**Summary: 1 of 16 contract endpoints is implemented and matches exactly (`/v1/health`).
15 of 16 are not yet implemented.** The Fire TV client should build against this document
as a set of stubs, not against the live server, for all but `/v1/health`.

---

## 9. Deliberately absent

Per D6, D10, D18, D19 and plan §4's own closing statement, this contract **does not, and
must not,** include server endpoints for:

- Care plan (read or write)
- Today's plan
- Care-task completion
- Progress / activity history
- Wellness session state (start/pause/resume/complete)
- Settings (profile, PIN, preferences)

All of the above are **device-local and offline** by design. Adding a server endpoint for
any of them would duplicate the source of truth and break the offline guarantee (D20 Tier
0). No such endpoint should be added to this contract in any future revision without an
explicit architecture change to D6/D18/D19/D20.

---

## 10. Open questions for the owner

Every place the plan is silent, or where this draft found a conflict, rather than
resolving it silently:

| # | Question | This draft's recommended default | Status |
|---|---|---|---|
| 1 | Plan §4 says "Eighteen endpoints" but its own table lists 16. Which is correct — is content missing from the plan, or is the prose count wrong? | Treat 16 as authoritative (it's the enumerated, checkable artifact); fix the prose count when the plan is next revised | **OPEN** |
| 2 | What HTTP header carries the device token? | `X-Device-Token: <token>` | **OPEN** |
| 3 | Pairing code expiry duration | 15 minutes for real use; a separate, longer-lived demo code for hackathon recording (D22 already distinguishes these informally) | **OPEN** |
| 4 | Document upload size limit | 20 MB per document (generous for a scanned or authored text-layer PDF, small enough to reject anything clearly wrong) | **OPEN** |
| 5 | Full error code list (§2's table is a starting proposal, not exhaustive) | Ratify the starter list in §2; extend only as real failure modes are discovered during implementation | **OPEN** |
| 6 | Exact shape of `editedFields` in `POST /proposals/{id}/review` (`action: "edit"`) | A free-form partial patch of `proposedFields`, as drafted in §3.4 | **OPEN** |
| 7 | `confidence` field: scale and meaning (model-reported probability? a calibrated score? categorical bucketed to a float?) | `0.0`–`1.0`, treated as an uncalibrated relative signal only — never surfaced to the end user as a precise probability | **OPEN** |
| 8 | `sourceReferenceId` format | Server-generated UUID v4 string | **OPEN** |
| 9 | Extraction job poll interval | 2 seconds | **OPEN** |
| 10 | Extraction job client-side timeout | 60 seconds of polling before showing a "taking longer than expected" state | **OPEN** |
| 11 | Should a failed `routines/generate` attempt's internal `failureReasons` be exposed to the client at all, even when a preset is served? | No — expose only `origin: "PRESET"`; keep validator failure detail server-side/log-only | **OPEN** |
| 12 | `POST /v1/devices/register` and `POST /v1/devices/pairing-code`: any request body fields at all (e.g. client app version, platform), or genuinely empty? | Genuinely empty for this MVP; add fields only if a real need appears | **OPEN** |
| 13 | Presets for `routines/generate`'s `PRESET` origin do not exist anywhere in the repo yet (plan §7.4). Who authors them, and against which catalog version? | Same author/process as the D17 catalog itself, pinned to `catalogVersion: "1.0.0"` | **OPEN — blocks real use of the PRESET fallback** |

None of these were decided by this draft. Each needs your explicit choice before the
contract can be frozen.

---

## 11. Freeze status

**This document is a DRAFT. It is not frozen.** Freezing requires:

1. Resolution of all 13 open questions in §10 (or an explicit owner decision to defer
   specific ones past the freeze, clearly marked if so).
2. Owner review of every request/response shape in §3.
3. Explicit owner approval recorded (e.g. a commit message, a review comment, or direct
   confirmation) before either developer treats any shape in this document as a
   commitment.

Until frozen, the Fire TV client may build against these shapes as **stubs for
development convenience**, but must expect them to change.
