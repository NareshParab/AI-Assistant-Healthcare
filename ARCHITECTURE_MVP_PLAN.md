# ARCHITECTURE & 26-DAY MVP EXECUTION PLAN

**Project:** AI Assistant Healthcare — Fire TV-first care + wellness companion
**Hackathon:** Build, Ship, Shape: Amazon Developer Hackathon 2026 — Fire TV track
**Document version:** 1.0.0
**Date:** 2026-09-27 (Day 1 of 26)
**Deadline:** 2026-10-23, 12:00 pm PT
**Team:** 2 developers
**Host OS:** Windows 11

**Source documents (read in full):** `PROJECT_MASTER_SPEC.md` v1.0.0 (product source of
truth), `PROJECT_REVIEW.md` (planning review). Neither was modified by this document.

**Scope of this document:** architecture decisions and execution plan only. No code, no
scaffolding, no dependency installation.

### Evidence labelling used throughout

| Label | Meaning |
|---|---|
| **[VERIFIED]** | Confirmed against official Amazon or Devpost documentation, cited in `PROJECT_MASTER_SPEC.md` §33.8 or `PROJECT_REVIEW.md` §5 |
| **[RECOMMENDATION]** | An architectural judgement made here, defensible but not externally verified |
| **[ASSUMPTION]** | Believed true, not validated. Every assumption has a POC or a verification action |
| **[VERIFY BEFORE SUBMISSION]** | Must be re-checked before 2026-10-23 |

### Product concept — unchanged and non-negotiable

`ASSIST` (care routine support from verified clinician information) · `GUIDE` (wellness
routines and guided activity) · `PROGRESS` (completion, history, Daily Health & Wellness
Summary) · `AI CORE` (bounded intelligence serving the other three). Fire TV is the primary
product experience. This document changes **no** product requirement.

---

## 0. Conflicts Identified and Resolved

Where the two source documents disagree, or where this task's framing overrides the
review, the conflict is named and resolved with a reason rather than silently decided.

### Conflict 0.1 — Backend: the review said none; this task requires server-side validation

**`PROJECT_REVIEW.md` D4/D5** recommended "thin proxy for AI only" and "on-device only"
clinical storage, on the grounds of privacy, simplicity and demo robustness. **This task**
states safety validation must be "deterministic and server-side where applicable" and asks
for a companion interface — both of which require a real backend.

**Resolution: a backend is required, but its scope is deliberately narrow.** The backend is
an **ingestion + AI + validation plane**. It never becomes the system of record for
confirmed clinical information.

- **Backend holds:** documents, rendered document page images, extracted *proposals*, the
  movement catalog, AI orchestration, deterministic validators.
- **Fire TV device holds (canonically):** the **confirmed** care plan, health measurements,
  activity records, day plans, summaries.

**Why this resolves both:** the no-secrets rule (`PRIV-1640`) and server-side deterministic
validation both require a server; data minimization (`PRIV-601`) and offline resilience
(`TECH-930`) both argue for keeping confirmed clinical data on the device. Splitting along
the confirmation boundary satisfies all four. It also means there is **no bidirectional
sync** to build — documents and proposals flow server→device, confirmation writes
device-local only.

**Consequence:** if the backend is down, the user's confirmed plan, Today, session runtime,
completion and progress all still work. Only *new* document ingestion and *new* AI
generation are unavailable. That is exactly the right failure profile for a demo.

### Conflict 0.2 — `PROD-2111` (no demo theater) vs `OQ-13` (pre-processed documents allowed)

**Resolution:** `OQ-13` is **withdrawn as unnecessary.** Decision **D7**/**D15** makes the
document pipeline genuinely real end to end using text-layer PDFs. Nothing is
pre-processed, so `PROD-2111` is satisfied without compromise. See §7.

### Conflict 0.3 — `F-A10` "plain-language explanation" vs `SAFE-915` "linguistic simplification only"

**Resolution:** the feature is **reframed, and `SAFE-915` is not weakened** (`CC-03`
forbids weakening §18). The action becomes **"What this says"**: verbatim original text, the
timing expressed in plain words, the source document and date, and the standing pointer to
the clinician. Genuine AI simplification is applied **only** to prose-bearing sources
(exercise handouts, diet instructions, precautions), never to single-line prescriptions
where no prose exists to simplify. See §9.3.

### Conflict 0.4 — `TECH-930` offline care path vs AI-dependent care features

**Resolution:** **pre-generate and cache at confirmation time** (D10). When a human confirms
an item, the plain-language view is generated once and stored with the confirmed item.
Thereafter it is local data. Daily Summary region 4 is generated when a network is available
and **omitted entirely on failure** — which is safe precisely because `SAFE-1410` keeps
regions 1–3 independent.

### Conflict 0.5 — glance speed vs card-level provenance vs low density (`C4`)

**Resolution:** provenance on Today cards renders as **one short line at reduced visual
emphasis** (source + date only). Full provenance lives in Item Detail. This satisfies
`PROD-552` (provenance at card level), `PROD-100` (5-second glance) and `HACK-415` (low
density) simultaneously. It is a clarification of presentation, not a requirement change.

### Conflict 0.6 — `SAFE-917` deterministic validation of free-text AI exercise output

**Resolution:** adopt the **curated movement catalog** (D17). AI selects and sequences
catalog entries by ID; it never emits free-text movements. Validation becomes set-membership
plus a duration sum — genuinely deterministic, as `SAFE-917` requires. See §8.

### Conflict 0.7 — Confirmation gate validating the model against its own transcription (`S1`)

**Resolution:** confirmation is performed against a **server-rendered image of the original
document page with the source region highlighted** (D16). The reviewer compares the proposal
to the *document*, not to extracted text. This closes the review's highest-severity finding
and is now a locked architectural requirement.

---

## 1. Architecture Decisions

Thirty decisions. Each states the chosen option, why, what was rejected and why,
implementation consequence, risk, and reversibility.

Optimization priorities, in order: **(1)** working Fire TV demo, **(2)** reliability,
**(3)** development speed, **(4)** D-pad/10-foot UX quality, **(5)** safety, **(6)** AI
reliability, **(7)** hackathon compliance, **(8)** maintainability, **(9)** two developers
finishing in 26 days.

---

### D1 — Target operating system

**Chosen: Fire OS (Android-based). Vega OS becomes a post-hackathon port target.**

**Why.** Three pieces of verified evidence converge. **[VERIFIED]** Vega developer tooling
requires macOS 10.15+ or Ubuntu 20.04+; **Windows and WSL are not supported** — the host is
Windows 11. **[VERIFIED]** Vega OS 1.1 ships on only two devices (Fire TV Stick HD 2026,
Fire TV Stick 4K Select 2025), while Fire OS 8 and 14 cover the rest of the current fleet.
**[VERIFIED]** The hackathon accepts *either*: *"Eligible projects for this category have to
launch a demo-ready app that works on Fire OS or Vega OS."* There is no scoring advantage
stated for Vega.

**Alternatives considered.** (a) Vega OS natively. (b) Vega via a macOS/Linux VM or cloud
host. (c) Dual-target.

**Why not selected.** (a) is not possible on the current machine. (b) spends 2–4 days of a
26-day budget on environment plumbing, on an OS with a two-device install base, for zero
rules benefit — and a VM adds emulator-within-VM graphics risk. (c) dual-targeting doubles
the platform surface for two developers; it is the clearest way to finish neither.

**Implementation consequence.** Android toolchain on Windows. Android APK packaging.
Sideload or emulator for testing. Fire OS device filtering applies at Appstore submission
time, which is not required here.

**Risk.** Low. The main residual risk is that no Fire OS device or emulator runs acceptably
on this machine — that is **P1**, and it gates everything.

**Reversibility.** Medium. Switching to Vega later means rewriting the UI layer. The
backend, catalog, data model and API are platform-neutral by design and would carry over
unchanged, which is a deliberate hedge.

---

### D2 — Fire TV application framework

**Chosen: Native Android — Kotlin + Jetpack Compose for TV.**
**Conditional reversal trigger defined below.**

**Why.** Focus quality is directly judged (Design is 25% of scoring, and `HACK-413`/
`HACK-414` are hard requirements). Compose for TV provides first-class D-pad focus
primitives and TV-specific components, which is precisely where TV apps lose Design points.
**[VERIFIED]** Google Play Services are unavailable on Fire TV (*"Some Firebase SDKs depend
on Google Play services, which are not available on Amazon devices"*), which penalizes any
stack that reaches for Firebase or Play-dependent libraries; native Android with no Play
dependency is unaffected. Official Amazon starter samples exist for the Kotlin/Compose path.
**[VERIFIED]** `HACK-801` constrains nothing: *"The requirement is that the project runs on
Fire OS or Vega OS."*

**Alternatives considered.** (a) React Native for TV. (b) Web app in a WebView.

**Why not selected.** (a) RN for TV is a legitimate choice with official samples and an
easier Vega path later, but D-pad focus management is its historical weak point, and the
project's hardest client requirement — rendering an original document region — would depend
on third-party native modules of uncertain Fire TV compatibility. (b) a WebView gives the
weakest focus model and the least TV-native feel, directly harming the criterion that is
25% of scoring.

**Implementation consequence.** Developer A works in Kotlin/Compose for the full 26 days.
Local storage via Room. Coroutines for the session runtime. `FLAG_KEEP_SCREEN_ON` for
sessions.

**Risk.** **[ASSUMPTION]** that at least one developer is productive in Kotlin/Compose. If
not, this is the wrong choice and the cost is severe.

**Reversal trigger — decide by end of Day 2.** Switch to React Native for TV (using the
official `react-native-multi-tv-app-sample`) if **either**: no developer has JVM/Android
experience, **or** P1 + P2 take Developer A more than 1.5 days. The switch is cheap at Day 2
and expensive after Day 6. **D16's server-rendered evidence image was chosen specifically so
that this reversal does not touch the document-verification feature** — the client only ever
displays an image, on any framework.

**Reversibility.** High before Day 6, low after.

---

### D3 — Fire OS / API target strategy

**Chosen: `minSdk` = API 29 (Fire OS 8 floor). `targetSdk` = API 34 (Fire OS 14 range).**

**Why.** **[VERIFIED]** Fire OS ↔ Android mapping: Fire OS 8 → API 29/30; Fire OS 14 → API
31–34; Fire OS 16 → API 35/36. Current 2025–26 devices split across Fire OS 8 and 14. An
API 29 floor maximizes the set of devices and emulator images that can run the app —
important because **we do not yet know which device or image will be available** — while
targeting 34 keeps modern behaviour.

**Alternatives considered.** (a) `minSdk` 31 (Fire OS 14 only). (b) `minSdk` 25 (Fire OS 6).

**Why not selected.** (a) excludes Fire OS 8 devices, and the most likely available hardware
is an older stick. (b) buys nothing and drags in legacy compatibility work.

**Implementation consequence.** Avoid APIs above 29 without a guarded fallback. `PdfRenderer`
(API 21+) is available if the D16 fallback path is ever needed.

**Risk.** Low.

**Reversibility.** High — a manifest and Gradle change.

---

### D4 — Is a backend required?

**Chosen: yes — one narrow backend service.**

**Why.** Three requirements make it unavoidable. `PRIV-1640` forbids API keys in client code,
and the AI provider requires a key (D8). Deterministic safety validation is required
server-side. Companion document upload (D21) needs a receiving endpoint. Additionally, PDF
text extraction *with coordinates* and page rasterization are far better served by
server-side libraries than by anything on-device.

**Alternatives considered.** (a) Fully on-device, no backend. (b) Full multi-tier backend
with accounts and sync.

**Why not selected.** (a) cannot hold an API key, cannot do server-side validation, and
cannot receive a companion upload — it fails three stated requirements. (b) adds
authentication, hosting, migrations and sync to a 26-day build for zero demo benefit, and
`PRIV-1630` would then mandate real authentication.

**Implementation consequence.** Developer B owns one service. A clean HTTP API boundary
becomes the parallelization seam between the two developers — which is itself a schedule
benefit.

**Risk.** Network dependency on demo day. Mitigated by Conflict 0.1's split: the
demo-critical care path runs entirely from device-local data.

**Reversibility.** Medium. Removing the backend would mean abandoning the companion and
moving the key into the client, which is not permissible.

---

### D5 — Backend architecture

**Chosen: a single stateless Python service (FastAPI) with SQLite, serving the JSON API and
the companion web page from the same process.**

**Why.** The backend's hardest job is document handling: extract text spans **with bounding
boxes**, and rasterize a page region to an image. Python's PDF tooling does both in a single
mature library, which materially de-risks D15 and D16 — the two hardest technical
requirements in the project. One process serving both API and companion page removes a whole
deployment target. SQLite removes database operations entirely.

**Alternatives considered.** (a) Node/TypeScript service. (b) Serverless functions.
(c) Separate API service + separate companion app.

**Why not selected.** (a) is attractive for language unity with a JS companion, and
`pdf.js` + `node-canvas` can do the job — but with noticeably more code for text-with-
coordinates plus rasterization, against the single most schedule-critical feature. The
language-unity benefit is small because the companion is deliberately tiny (D21). (b)
serverless adds cold-start latency to AI calls and complicates local development for two
devs. (c) splitting is unnecessary structure for a 26-day build (`RULE-004` spirit: no
unnecessary architecture).

**Implementation consequence.** Developer B writes Python. Runs locally during development;
one hosted instance for the demo (D28). Companion is server-rendered static HTML + minimal
JS — no frontend framework.

**Risk.** Two languages in the repo (Kotlin + Python). Acceptable given the clean API seam
and the near-zero coupling.

**Reversibility.** High for hosting; medium for language (the API contract is the real
asset and is language-neutral).

---

### D6 — Database / storage strategy

**Chosen: two stores, split on the confirmation boundary.**
**Device:** Room (SQLite) — canonical for confirmed clinical data.
**Server:** SQLite file + a local blob directory — documents, page renders, proposals.

**Why.** This is the physical expression of Conflict 0.1. It also directly enforces
`SAFE-1801` (a `CarePlanItem` exists only in a confirmed state) and `SAFE-1803` (a scheduled
item can never reference a proposal) — because proposals live in a *different database on a
different machine* from confirmed plan items. The separation invariant `SAFE-940` becomes
structurally difficult to violate rather than merely policy.

**Alternatives considered.** (a) One server database for everything. (b) Device-only with
files. (c) A hosted managed database.

**Why not selected.** (a) puts confirmed clinical data on a server, weakening `PRIV-601` and
breaking offline operation. (b) cannot express the provenance invariants (`SAFE-970`,
`SAFE-1801`–`1809`) — flat files have no constraints. (c) unnecessary operations for a
hackathon; SQLite is sufficient at this scale.

**Implementation consequence.** Room entities with non-null provenance columns, so a health
datum without provenance cannot be persisted (`SAFE-521`, `TECH-902`). No sync engine
required — a deliberate, significant scope saving.

**Risk.** Device data is not portable across devices. Accepted; portability is `FUT-1200`.

**Reversibility.** Medium.

---

### D7 — Document format strategy for the MVP

**Chosen: digitally generated, text-layer synthetic PDFs. No OCR in the MVP.**

**Why.** This single decision does four things at once. It makes the pipeline genuinely real
end to end, resolving Conflict 0.2. It removes OCR — the largest time sink and largest
reliability risk — from the critical path. It provides **text spans with exact bounding
boxes**, which is what makes D16's original-document verification possible at all. And it
keeps extraction quality high enough that the confirmation queue is reviewable rather than
noise.

**Alternatives considered.** (a) Scanned images + OCR. (b) Plain-text or JSON fixtures.

**Why not selected.** (a) is more impressive if it works and a catastrophic time sink if it
does not; OCR also destroys reliable bounding boxes, undermining D16. **[VERIFIED]** ML Kit
on-device text recognition — the default choice — depends on Google Play Services and is
therefore **unavailable on Fire TV**, so on-device OCR would require a bundled native
library. (b) would make the pipeline theater and violate `PROD-2111`.

**Implementation consequence.** Developer B authors 6–7 synthetic clinical documents as
text-layer PDFs (discharge-style summary, prescription, exercise handout, diet instructions,
precautions, follow-up note, lab result). These are synthetic and labelled as such
(`HACK-980`, `PRIV-982`). OCR moves to `FUT-1403`.

**Risk.** A judge might ask about scanned documents. Answer honestly in the description: the
pipeline is real, OCR is a known next step. Honesty beats a broken feature.

**Reversibility.** High — OCR can be added behind the same extraction interface later.

---

### D8 — AI provider and abstraction

**Chosen: Claude via the Anthropic API, accessed exclusively through an internal
`LlmClient` interface on the backend. Model selection per task.**
**[VERIFY BEFORE SUBMISSION]** — provider terms, per `PRIV-1622`.

**Why.** The spec requires provider abstraction (`TECH-904`) so the choice stays reversible.
Claude offers strong structured/tool-use output, which D11 depends on. Task-appropriate
model selection: a capable model (`claude-sonnet-5`) for document structuring where accuracy
matters most, and a smaller fast model (`claude-haiku-4-5`) for summarization and routine
sequencing where the task is narrower and latency matters more.

**Alternatives considered.** (a) A single model for all tasks. (b) On-device inference.
(c) A different provider.

**Why not selected.** (a) wastes latency and cost on summarization. (b) not realistic on
Fire TV Stick hardware for extraction-quality work, and would put the model in the client.
(c) reasonable, but the abstraction makes this reversible, so the decision is low-stakes —
which is the point of the abstraction.

**Implementation consequence.** All AI calls originate on the backend. The Fire TV client
never holds a key and never calls a provider directly. One interface, one place to swap.

**Risk.** **[VERIFY BEFORE SUBMISSION]** `PRIV-1622` requires that a provider whose terms
permit training on submitted content **MUST NOT** be used for clinical content. This must be
confirmed in writing against current terms before any real document text is sent, and
recorded in the repository. Until confirmed, use only synthetic documents — which is the
plan regardless (`HACK-980`).

**Reversibility.** High by design.

---

### D9 — AI request/response architecture

**Chosen: synchronous request/response for short operations; a job-and-poll pattern for
document extraction only.**

**Why.** Routine generation, plain-language transformation and summarization complete in
seconds and can be synchronous. Document extraction touches multiple pages and may take
long enough that a blocked TV screen would violate `PROD-439` (honest loading states). A
simple job record plus polling is far less machinery than a queue or websockets and is
sufficient at this scale.

**Alternatives considered.** (a) Everything synchronous. (b) A message queue with push.

**Why not selected.** (a) risks a multi-second frozen TV screen during the demo's most
important beat. (b) unnecessary infrastructure (`RULE-004` spirit).

**Implementation consequence.** `POST /documents/{id}/extract` returns a job id;
`GET /extraction-jobs/{id}` returns status and, on completion, proposals. TV shows a
determinate, honest progress state with a timeout path.

**Risk.** Polling is chatty. Irrelevant at this scale.

**Reversibility.** High.

---

### D10 — AI pre-generation and caching strategy

**Chosen: device-canonical confirmed data, plus pre-generation of AI-derived text at
confirmation time.** *(The resulting offline tiering is specified in D20.)*

**Why.** This is the resolution of Conflict 0.4 and the single most demo-protective decision
in the document. When a human confirms an item, the backend generates the plain-language
"What this says" view once, and it is stored **with** the confirmed item on the device.
Thereafter Today, Item Detail, the day engine, the session runtime, completion, progress and
summary regions 1–3 are all pure local reads with **no network dependency whatsoever**.

**Alternatives considered.** (a) Generate on demand each time. (b) Require network for the
care path.

**Why not selected.** (a) puts an AI call on the critical path of the most-used screen —
slow, fragile, and repeatedly expensive for identical output. (b) directly violates
`TECH-930` and makes the demo hostage to venue wifi (`R-16`).

**Implementation consequence.** Network is needed for exactly two things: ingesting a new
document, and generating a new wellness routine or summary region 4. Everything else works
offline. Per-operation fallbacks are specified in §10.5.

**Risk.** Cached text could drift from a later prompt improvement. Acceptable — and
arguably correct, since the user confirmed *that* text.

**Reversibility.** High.

---

### D11 — Structured AI output contract

**Chosen: strict JSON schema enforced via provider tool-use, with server-side schema
validation, a bounded retry of 2, and fail-closed on exhaustion.**

**Why.** `SAFE-920` requires fail-closed behaviour and `SAFE-917` is unimplementable without
a schema. Free-text parsing in a clinical pipeline is indefensible. Two retries absorb
transient malformation; beyond that, failing closed is the correct and safe outcome.

**Alternatives considered.** (a) Lenient parsing with repair heuristics. (b) Unbounded
retry.

**Why not selected.** (a) repair heuristics are exactly how invented clinical content enters
a system. (b) unbounded retry turns a failure into an indefinite hang on a TV screen.

**Implementation consequence.** Every AI operation has a named schema version. Validation
failures are logged without clinical content (`PRIV-1652`) and surface the §10.5 fallback.
**P5** measures the malformed rate before this is committed to.

**Risk.** Frequent refusals would make a correct system look broken. **P5** is the mitigation
and the go/no-go measurement.

**Reversibility.** High.

---

### D12 — ASSIST AI architecture (clinical regime)

**Chosen: a transform-only pipeline with no generative latitude, running server-side, whose
output is always a *proposal* requiring human confirmation.**

**Why.** `SAFE-900` requires each AI operation to be assigned to exactly one regime, and
`SAFE-915` restricts ASSIST to operating on the confirmed item's own text with no recourse
to general medical knowledge. Architecturally this means ASSIST operations receive **only**
document-derived text as data, are forbidden from emitting fields absent from the source
(`SAFE-912`), and must attach a `sourceExcerptRef` with page and bounding box to every
proposed value.

**Alternatives considered.** (a) One general AI service for all tasks. (b) Allowing ASSIST to
enrich with medical knowledge for usefulness.

**Why not selected.** (a) collapses the regime boundary that is the product's principal
safety claim. (b) is prohibited by `SAFE-004`, `SAFE-005`, `SAFE-012`, `SAFE-507` and
`SAFE-731`, and is the exact failure mode the product exists to avoid.

**Implementation consequence.** Two physically separate code paths and two separate prompt
sets for ASSIST and GUIDE, with no shared "ai.call()" helper that could blur them. ASSIST
output always lands in `PROPOSED` (`SAFE-913`).

**Risk.** ASSIST usefulness is deliberately limited. That is the intended trade, and §9.3
reframes the user-facing feature accordingly.

**Reversibility.** Low — and intentionally so. This boundary should not be easy to move.

---

### D13 — GUIDE AI architecture (wellness regime)

**Chosen: catalog-constrained selection and sequencing. The model emits movement **IDs** and
durations, never movement text.**

**Why.** This is the resolution of Conflict 0.6 and it makes `SAFE-917` genuinely
deterministic. Because the model can only reference catalog IDs, validation reduces to: do
all IDs exist, are all flagged safe for this profile's precautions, does the sequence satisfy
warm-up/cooldown structure (`SAFE-811`), and does the duration sum match the budget within
tolerance (`PROD-121`). Every one of those is a deterministic check.

**Alternatives considered.** (a) Free-text generation validated by keyword screening.
(b) Purely static preset routines with no AI.

**Why not selected.** (a) keyword screening against conceptual prohibitions (`SAFE-034`:
plyometric, breath-holding, spinal loading) is trivially defeated by paraphrase and produces
both false positives and false negatives — it is safety theater. (b) would remove the AI
value the product claims and weaken the personalization the spec requires (`PROD-830`).

**Implementation consequence.** The movement catalog (§8) must exist before GUIDE AI can be
built — this is a hard dependency in the schedule. Catalog authoring is a Developer B task
starting Day 5.

**Risk.** Less variety than open generation. Entirely acceptable for a 26-day MVP with a
safety obligation — and it is *faster* to build.

**Reversibility.** Medium. Loosening this would require rebuilding validation, which is the
correct friction.

---

### D14 — Guardrail architecture

**Chosen: a mandatory server-side validation stage that every AI response passes through
before leaving the backend, plus client-side render-time provenance assertions.**

**Why.** `SAFE-920` requires a guardrail that cannot be bypassed and that fails closed;
`TECH-922` and `RULE-024` state that prompt instructions alone are **not** an acceptable
implementation. Placing it as a required stage in the response path — not an optional helper
— means the only way to return AI output is through it. The client adds a second, independent
check: a component that cannot resolve provenance refuses to render (`SAFE-521`).

**Duties (per `SAFE-920`).** Enforce regime assignment; verify ASSIST output contains no
value absent from its source; validate GUIDE routines against the catalog and duration
budget; enforce refusal for out-of-scope requests; enforce labelling and provenance; and
**fail closed** — if validation cannot complete, nothing is returned.

**Alternatives considered.** (a) Prompt-level instruction only. (b) Client-side validation
only. (c) Advisory logging without blocking.

**Why not selected.** (a) explicitly prohibited by `TECH-922`. (b) a client can be bypassed
and cannot be trusted with a safety boundary. (c) a guardrail that does not block is not a
guardrail.

**Implementation consequence.** Validators live in their own module, are readable
independently of any prompt or provider (`SAFE-921`), and are the highest-priority target for
unit tests (`SC-20`–`SC-28`).

**Risk.** A validator bug blocks legitimate output. Preferable to the inverse, and detectable
by tests.

**Reversibility.** Low. Intentionally.

---

### D15 — PDF text and coordinate extraction strategy

**Chosen: server-side extraction of text spans **with page number and bounding box**, from
text-layer PDFs. No OCR.**

**Why.** D16's verification UX is impossible without coordinates. Extracting text plus
geometry server-side, where mature libraries exist, is dramatically cheaper than any on-device
approach — and **[VERIFIED]** the obvious on-device option (ML Kit) is unavailable on Fire TV
because Play Services are absent.

**Alternatives considered.** (a) On-device text extraction. (b) Text-only extraction without
coordinates. (c) Send whole page images to a vision model.

**Why not selected.** (a) no good Fire TV path and it would put document processing on
constrained hardware. (b) would force confirmation against extracted text — the precise
failure the review identified as `S1`. (c) loses reliable coordinates and increases
hallucination surface for no benefit.

**Implementation consequence.** Each `ExtractedField` carries `page`, `bbox`, and the
verbatim `sourceText`. Pipeline: parse PDF → page text with geometry → structure via ASSIST
AI → proposals carrying coordinates.

**Risk.** A PDF with an unusual internal structure could produce poor spans. Mitigated
because we author the synthetic documents (D7) and **P4** validates the path early.

**Reversibility.** High behind the extraction interface.

---

### D16 — Original-document verification UX architecture

**Chosen: the backend renders the document page to an image with the source region
highlighted, and the Fire TV client simply displays that image beside the proposed fields.**

**Why.** This closes `S1`, the highest-severity finding in `PROJECT_REVIEW.md`: confirming a
proposal against *extracted text* validates the model against its own transcription and
catches nothing. Confirming against a **rendered image of the actual page** means the human
is checking the proposal against the document itself.

Making the highlight **server-rendered** rather than client-drawn is a deliberate
architectural hedge. The client becomes a dumb image viewer, which means this feature —
the most important one in the product — is **completely independent of the D2 framework
choice**. If D2 reverses to React Native on Day 2, this feature does not change at all.

**Alternatives considered.** (a) Client-side PDF rendering with a drawn overlay (Android
`PdfRenderer` + Canvas). (b) Showing extracted text only. (c) Showing the whole page with no
highlight.

**Why not selected.** (a) is viable on Android and is retained as an optimization if image
transfer proves slow — but it couples the hardest feature to the framework choice during the
window when that choice may still reverse. (b) is the `S1` failure itself. (c) makes the
reviewer hunt the page, which weakens the gate in practice (`SAFE-1522`).

**Implementation consequence.** Endpoint returns a PNG of the page (or a cropped region)
with a highlight rectangle already drawn. The review screen is a two-pane D-pad layout:
evidence image left, proposed fields right, actions **Confirm / Edit / Discard / Unclear**.
Images are cached on device after first fetch so review works offline on a second pass.

**Risk.** Image legibility on a TV at 10 feet. Mitigated by rendering a **cropped region
around the highlight** at high zoom rather than a full page, with a toggle to see the whole
page for context.

**Reversibility.** High — the client contract is "show me an image."

---

### D17 — Exercise / movement catalog architecture

**Chosen: a versioned, human-authored JSON catalog, held in one shared repository package
and bundled into both the backend and the Fire TV app.**

**Why.** D13 requires the model to reference catalog IDs. The backend needs the catalog to
validate; the device needs it to run offline preset routines and render instructions without
a network call. One authored artifact, two consumers, no drift — which is why the repository
needs a shared package (§2).

**Alternatives considered.** (a) Catalog in a database. (b) Separate copies per app.
(c) Catalog fetched at runtime only.

**Why not selected.** (a) unnecessary for static authored content that changes by commit.
(b) guarantees drift, which here is a *safety* defect. (c) breaks offline wellness.

**Implementation consequence.** Developer B authors ~40–50 movements (§8). Schema is
versioned; the version is recorded on every generated routine for auditability.

**Risk.** Authoring time is real — budget 1.5 days. Every entry must be written to satisfy
`SAFE-030` and `SAFE-034` by construction.

**Reversibility.** High for content, medium for schema.

---

### D18 — Day / Plan engine

**Chosen: fully deterministic, device-side, pure function. No AI involvement whatsoever.**

**Why.** `TECH-906` requires this and it is correct: AI must never be in the path that
decides what is on a person's clinical care plan today. Determinism also makes the engine
trivially testable and makes Today instant and offline.

**Design.** `buildDayPlan(confirmedItems, dayAnchors, date, completionRecords) → DayPlan`.
Pure, synchronous, no I/O. Timing expressions map to the user's configured anchors
(`PROD-1011`) while the stated expression stays visible (`SAFE-711`). Items without
determinable timing become reference cards (`PROD-1012`), never silently timed. Recomputed on
each Today entry and each completion (`PROD-1014`).

**Alternatives considered.** (a) AI-assisted scheduling. (b) Server-computed day plan.

**Why not selected.** (a) prohibited and unsafe. (b) breaks offline and adds latency to the
most-used screen for no benefit.

**Implementation consequence.** One of the first testable units. Unit tests cover anchor
mapping, overdue derivation, rollover (`PROD-1015`) and reference-card handling.

**Risk.** Very low.

**Reversibility.** High.

---

### D19 — Session runtime engine

**Chosen: fully deterministic, device-side, coroutine-driven state machine. No AI, no
network.**

**Why.** `TECH-907` requires it. A guided session must not stutter, pause or fail because of
a network condition — it is the most visually prominent demo beat (`PROD-122`,
`PROD-601`).

**Design.** States: `Idle → Running(segmentIndex, remaining) → Paused → Completed |
ExitedPartial`. Automatic advancement with a visible countdown. `FLAG_KEEP_SCREEN_ON` held
for the session duration and released on exit. Partial completion recorded truthfully
(`PROD-605`, `PROD-1211`). Reminders suppressed during a session (`PROD-1114`).

**Alternatives considered.** (a) Server-driven session progression. (b) AI-paced adaptation
mid-session.

**Why not selected.** (a) absurd latency coupling for a timer. (b) prohibited — AI must not
control timers, completion state or progression.

**Implementation consequence.** **P3** validates timing smoothness and the screen-on flag on
real hardware before this is built for real.

**Risk.** Screen timeout on an untested device — exactly what **P3** exists to catch.

**Reversibility.** High.

---

### D20 — Offline / degraded-mode architecture

**Chosen: three tiers, with explicit per-operation fallbacks.**

| Tier | Contents | Network |
|---|---|---|
| **Tier 0 — always works** | Profile select, Today, Item Detail, completion, care plan read, health info, day engine, session runtime, progress, summary regions 1–3, preset routines | **Never required** |
| **Tier 1 — network preferred, degrades** | Routine generation (falls back to vetted presets), summary region 4 (omitted on failure) | Optional |
| **Tier 2 — network required** | Document ingestion, extraction, confirmation-time pre-generation | Required, and clearly stated in UI |

**Why.** `TECH-930` and `TECH-931` ("fail closed on safety, fail open on convenience"). The
entire demo-critical care path sits in Tier 0.

**Alternatives considered.** (a) Uniform online requirement. (b) Full offline including AI.

**Why not selected.** (a) violates `TECH-930` and makes the demo hostage to venue wifi.
(b) not feasible on the hardware.

**Implementation consequence.** Every Tier 1/2 surface needs a designed degraded state, not
a spinner that never resolves (`PROD-439`).

**Risk.** Low, given the tiering is explicit from day one.

**Reversibility.** High.

---

### D21 — Companion interface architecture

**Chosen: a minimal mobile web page served by the backend, scoped to document upload and
awkward text entry only. It is not an application.**

**Why.** Fire TV must remain the primary experience (`PROD-400`, `OOS-2027`), and
`PROD-1521` puts caregiver review **on the TV** in the MVP. The genuine problem a companion
solves is that a TV has no file picker and no comfortable keyboard (`PROD-410`).

**Responsibilities — in scope.** Document upload. Optional text entry (profile name,
care-team contact). That is all.

**Responsibilities — explicitly out of scope.** Document review and confirmation (stays on
TV — it is the `PROD-2101` demo centrepiece and the core safety moment). Today. Care plan
viewing. Sessions. Progress. Summaries. Settings. Any health information display.

**Alternatives considered.** (a) A native companion app. (b) A full caregiver web app.
(c) No companion, bundled documents only.

**Why not selected.** (a) days of work plus store friction for an upload form. (b) becomes a
second primary experience — prohibited. (c) tempting, but then the upload path is never real;
having *both* a real upload path and bundled demo documents is the strongest combination
(§7.3).

**Implementation consequence.** One HTML page, a file input, a pairing-code field. No
framework. Half a day of work.

**Risk.** Low. It is deliberately trivial.

**Reversibility.** High.

---

### D22 — Fire TV ↔ companion communication

**Chosen: a short pairing code displayed on the TV; the companion posts to the backend with
that code; the TV polls for new documents.**

**Why.** Avoids accounts, avoids local network discovery (unreliable across guest wifi and
subnets), avoids QR-camera dependencies. A 6-character code typed on a phone is the least
fragile mechanism available and is demonstrable on camera.

**Alternatives considered.** (a) Local network transfer / mDNS. (b) QR code scanned by the
phone. (c) Cloud accounts with login.

**Why not selected.** (a) notoriously unreliable on conference and guest networks — a
demo-day risk. (b) a fine enhancement, but adds a camera path; the pairing code is the
reliable floor. QR can be added later as a convenience over the same code. (c) requires
authentication infrastructure that `PRIV-1630` would then make mandatory.

**Implementation consequence.** Backend holds a short-lived pairing record binding a code to
a device token. Documents are scoped to that token. No personal identifiers involved.

**Risk.** Code collision or expiry mid-demo. Mitigated by long-lived demo codes and by
bundled documents as the demo's primary path (§7.3).

**Reversibility.** High.

---

### D23 — API structure

**Chosen: a small REST/JSON API over HTTPS, versioned under `/v1`, grouped by the twelve
domains in §6. No GraphQL, no RPC framework.**

**Why.** The API surface is genuinely small (~18 endpoints). REST is the least machinery, the
easiest to debug from a Windows terminal, and the easiest for two developers to agree on in
writing on Day 2 — which is what makes parallel work possible.

**Alternatives considered.** (a) GraphQL. (b) gRPC.

**Why not selected.** (a) solves over-fetching problems this product does not have.
(b) tooling overhead for two developers and one client.

**Implementation consequence.** The API contract is written and frozen on **Day 3** so
Developer A can build against stubs while Developer B implements. This is the single most
important scheduling artifact in the plan.

**Risk.** Contract churn causes rework. Mitigated by freezing early and versioning.

**Reversibility.** High.

---

### D24 — Error, loading and fallback strategy

**Chosen: every AI-touching operation declares a named deterministic fallback; no generic
spinners; no silent failures.**

Per-operation fallbacks (this closes review finding `S6`):

| Operation | On failure |
|---|---|
| Document extraction | Mark document `EXTRACTION_FAILED`; offer retry; **no partial proposals** |
| Individual field low confidence | `UNCLEAR — needs a person` (`SAFE-503`), never a guess |
| Plain-language pre-generation | Store and show **verbatim original text only** — always safe |
| Routine generation | Offer a **vetted preset** of the requested duration from the catalog |
| Routine fails validation | Discard silently to the user, serve a preset, log the validation failure |
| Summary region 4 | **Omit region 4 entirely**; render regions 1–3 — safe by `SAFE-1410`'s separation |
| Out-of-scope request | Brief warm refusal + redirect to clinician (`SAFE-916`) |
| Network unavailable | Tier 0 continues; Tier 1/2 show an honest, non-alarming explanation |

**Why.** `SAFE-920` demands fail-closed, and under-specified failure handling is precisely
where ad-hoc fallbacks quietly bypass a guardrail.

**Alternatives considered.** Generic error handling; retry-forever.

**Why not selected.** Both produce an app that appears hung on a TV, and neither is safe.

**Implementation consequence.** Loading states are determinate with timeouts (`PROD-439`).
Every fallback path is demo-rehearsed.

**Risk.** Low.

**Reversibility.** High.

---

### D25 — Secrets and environment strategy

**Chosen: all credentials server-side only, supplied via environment variables, never in the
repository or any client artifact.**

**Why.** `PRIV-1640` is absolute: no secrets or API keys in client code, configuration,
commit history, build artifacts or demo assets. The Fire TV client holds **no** credential of
any kind — it is the architectural reason D4 exists.

**Implementation consequence.** `.gitignore` and a secrets-exclusion configuration committed
in the **first** commit (`PRIV-1641`). A committed `.env.example` with placeholder values
only. A secret scan before submission (`DOD-14`). The client's only configuration is a
backend base URL.

**Risk.** Accidental commit. Mitigated by day-one exclusion configuration plus a pre-
submission scan.

**Reversibility.** N/A — non-negotiable.

---

### D26 — Logging and privacy strategy

**Chosen: structured logging with identifiers only. Clinical content never logged. AI
prompt/response logging off by default and disabled in the submitted build.**

**Why.** `PRIV-1650`–`PRIV-1652`. The subtle one is `PRIV-1652`: in this product, prompts
*contain clinical text*, so AI request logging is itself a PHI leak. This is the most
commonly missed control in AI health projects.

**Rules.** Log `documentId`, `proposalId`, field *names*, counts, durations, validation
outcomes, error classes. Never log document text, extracted values, medication names, dose
strings, measurements, or prompt/response bodies. Verbose development logging is disabled in
the submitted build (`PRIV-1651`).

**Alternatives considered.** Full request logging for debuggability; redaction filters.

**Why not selected.** Full logging is a direct violation. Redaction filters are
best-effort and fail open — the safe default is not to log the content at all.

**Implementation consequence.** Debugging extraction relies on local fixtures and tests
rather than production logs. Accepted.

**Risk.** Harder debugging. Accepted deliberately.

**Reversibility.** N/A for the rules; logging detail is tunable locally.

---

### D27 — Demo data strategy

**Chosen: two seeded synthetic profiles and 6–7 authored synthetic documents, labelled as
demo data at the data layer and visibly in the UI.**

**Why.** `HACK-980` requires synthetic or authorized data; `PRIV-981` requires it be
identifiable at the data layer (`sourceType = demo_seed`) and visible in the UI;
`PRIV-982` forbids basing personas on real individuals.

**Content.** Care persona (post-cardiac/stroke event, per the spec's Persona A) with
discharge-style summary, prescription, exercise handout, diet instructions, precautions,
follow-up note, lab result. Wellness persona with preferences and a short history so streaks
are non-empty on camera.

**Alternatives considered.** Generating data at runtime; using public sample medical
documents.

**Why not selected.** Runtime generation is non-reproducible for a demo. Public medical
documents risk real patient data and `HACK-814` originality issues.

**Implementation consequence.** Documents authored as text-layer PDFs (D7) committed to the
repository. A one-command seed script.

**Risk.** Low. Authoring time is budgeted.

**Reversibility.** High.

---

### D28 — Deployment strategy

**Chosen: backend on one small managed host with HTTPS and a stable URL; Fire TV app
sideloaded as an APK; no Appstore submission.**

**Why.** **[VERIFIED]** Appstore publication is **not** a hackathon requirement — the rules
require a demo-ready app plus repository and video. `PRIV-1620` requires TLS for health
information in transit, so the backend needs real HTTPS, not a local tunnel, on demo day.

**Alternatives considered.** (a) Localhost with a tunnel. (b) Full cloud infrastructure.
(c) Appstore submission.

**Why not selected.** (a) tunnels expire and change URLs mid-demo — an avoidable risk.
(b) unnecessary. (c) days of certification for no scoring benefit.

**Implementation consequence.** Deploy by Day 12 so the app runs against the real URL for
two weeks before recording. Judges run the backend locally via documented instructions
(`HACK-805`) — the hosted instance is for the demo and for judges who prefer not to.

**Risk.** A hosted instance is a demo-day dependency. Mitigated: the TV app runs Tier 0
entirely offline, and documents can be pre-ingested before recording.

**Reversibility.** High.

---

### D29 — Testing strategy

**Chosen: a narrow, safety-weighted test suite, not broad coverage.**

| Layer | What is tested | Why |
|---|---|---|
| **Guardrail validators** | Every `SC-20`–`SC-28` zero-tolerance criterion has a test that fails if the boundary breaks | `DP-14`. Highest-value tests in the project |
| **Day/Plan engine** | Anchor mapping, overdue derivation, rollover, reference cards | Pure function, cheap to test, clinically load-bearing |
| **Routine validation** | Catalog membership, precaution filtering, structure, duration tolerance | Makes `SAFE-917` real |
| **Provenance invariants** | A health datum cannot persist without provenance; no path promotes AI-generated to confirmed (`SAFE-1800`) | Enforces `SAFE-940` |
| **Schema validation** | Malformed AI output is rejected, retried, then fails closed | D11 |
| **Manual TV checklist** | D-pad traversal, safe zone, type sizes, focus retention, Back semantics | `HACK-410`–`HACK-414`; cannot be automated cheaply |

**Why.** With 26 days and two developers, broad unit coverage is a poor trade. Tests that
prove *safety boundaries* are worth far more than tests that prove UI rendering.

**Alternatives considered.** Full coverage; end-to-end UI automation (Appium).

**Why not selected.** Both consume days that the critical path needs. Appium on Fire TV is
its own setup project.

**Implementation consequence.** Tests written alongside the guardrail (`DP-05`), not after.

**Risk.** UI regressions go uncaught by automation. Mitigated by the manual checklist run at
each phase gate and by continuous demo rehearsal (`DP-15`).

**Reversibility.** High.

---

### D30 — Fire TV simulator / device validation strategy

**Chosen: resolve the target within the first 24 hours, in a strict preference order, and
treat it as a project-blocking gate.**

**Order of preference.**
1. **Physical Fire TV device** — best evidence for `HACK-806a`, real performance truth.
2. **Android TV emulator image on Windows** (Android Studio, TV profile at 1080p) —
   **[ASSUMPTION]** adequate as a Fire OS development surrogate for layout, focus and
   session timing. **[VERIFY]** that recorded footage credibly satisfies *"running on an
   actual Fire TV device or the Fire TV/Vega simulator."*
3. **Acquire a Fire TV Stick** — if neither of the above is available, purchase becomes the
   critical path and must be initiated on Day 1, not Day 10.

**Why.** **[VERIFIED]** The demo video must show the project *"running on an actual Fire TV
device or the Fire TV/Vega simulator."* This is the one requirement that, unmet, makes the
submission invalid regardless of code quality. It is therefore **P1** and gates everything.

**Alternatives considered.** Deferring the question; recording a desktop window.

**Why not selected.** Deferral is how projects discover on Day 24 that they cannot submit. A
desktop recording does not satisfy the requirement.

**Implementation consequence.** Day 1 morning, before any other work.

**Risk.** **Highest-severity unknown in the project.** Option 3 has shipping lead time,
which is precisely why it must be decided on Day 1.

**Reversibility.** N/A — a discovery, not a design choice.

**[VERIFY BEFORE SUBMISSION]** Whether an Android TV emulator qualifies as "the Fire TV/Vega
simulator" for `HACK-806a`. If there is any doubt, use physical hardware. Do not gamble the
submission on an interpretation.

---

## 2. Repository Architecture

A single repository. Two runtimes (Kotlin, Python) plus one shared data package. Structure
is chosen to make the **shared movement catalog and API contract** first-class, because
those are the two artifacts both developers depend on.

```
ai-assistant-healthcare/
│
├── README.md                     # HACK-805 / PROD-2120: what it is, safety boundary,
│                                 # setup, run, demo personas, synthetic-data statement
├── LICENSE                       # open-source licence (HACK-805a public route)
├── .gitignore                    # committed in the FIRST commit (PRIV-1641)
├── .env.example                  # placeholders only — never real values (D25)
│
├── docs/
│   ├── PROJECT_MASTER_SPEC.md    # product source of truth (unchanged)
│   ├── PROJECT_REVIEW.md         # planning review (unchanged)
│   ├── ARCHITECTURE_MVP_PLAN.md  # this document
│   ├── API_CONTRACT.md           # frozen Day 3 — the parallelization seam (D23)
│   ├── FRICTION_LOG.md           # HACK-826 — from Day 1, up to 10% bonus
│   ├── PRODUCT_FEEDBACK.md       # HACK-808 — required submission field, drafted from Day 1
│   └── DEMO_SCRIPT.md            # the storyboard drives build order (TECH-2130)
│
├── firetv/                       # Developer A — the primary product experience
│   ├── app/
│   │   ├── ui/                   # Compose screens: profile, today, itemdetail,
│   │   │                         # careplan, healthinfo, review, wellness, session,
│   │   │                         # progress, summary, settings
│   │   ├── design/               # 10-ft design system: type scale, colour tokens,
│   │   │                         # focus treatment, safe-zone modifiers (§10)
│   │   ├── domain/
│   │   │   ├── dayplan/          # D18 deterministic engine — pure, unit-tested
│   │   │   ├── session/          # D19 deterministic runtime — pure, unit-tested
│   │   │   └── provenance/       # render-time provenance assertions (SAFE-521)
│   │   ├── data/
│   │   │   ├── local/            # Room: confirmed clinical data (canonical, D6)
│   │   │   └── remote/           # API client — the ONLY network surface
│   │   └── catalog/              # loads the shared movement catalog (D17)
│   └── src/test/                 # day engine, session engine, provenance invariants
│
├── backend/                      # Developer B — ingestion, AI, validation plane
│   ├── api/                      # FastAPI routes, grouped per §6
│   ├── documents/                # PDF parse, text+bbox spans, page render (D15/D16)
│   ├── ai/
│   │   ├── client/               # LlmClient abstraction (D8) — provider-swappable
│   │   ├── assist/               # ASSIST regime — transform only (D12)
│   │   ├── guide/                # GUIDE regime — catalog-constrained (D13)
│   │   └── schemas/              # versioned structured-output schemas (D11)
│   ├── guardrail/                # D14 — mandatory validation stage, fails closed.
│   │                             # Readable independently of prompts (SAFE-921)
│   ├── storage/                  # SQLite + blob dir: documents, renders, proposals
│   ├── companion/                # D21 — one HTML page + minimal JS
│   └── tests/                    # guardrail + routine validation + schema tests
│
├── shared/
│   ├── movement-catalog/         # D17 — versioned JSON, bundled into BOTH runtimes.
│   │                             # Single source of truth; drift here is a safety defect
│   └── schemas/                  # AI output schemas shared by backend + client models
│
├── demo-data/
│   ├── documents/                # D27 — authored synthetic text-layer PDFs
│   └── profiles/                 # seeded care + wellness personas
│
└── scripts/
    ├── seed.*                    # one-command demo seeding
    ├── secret-scan.*             # pre-submission scan (DOD-14)
    └── generate-documents.*      # regenerate synthetic PDFs reproducibly
```

**Rationale for the shape.** `shared/` exists because the movement catalog has two consumers
and drift between them would be a *safety* defect, not a style issue (D17). `docs/` holds
the four submission artifacts (`API_CONTRACT`, `FRICTION_LOG`, `PRODUCT_FEEDBACK`,
`DEMO_SCRIPT`) as first-class files so they are written continuously rather than
retrofitted in the final week — which is the mitigation for `R-19`, a fatal risk. The
`firetv/` and `backend/` split is the developer-parallelization seam.

**What is deliberately absent.** No `packages/` proliferation, no monorepo tooling, no
shared UI library, no microservices. Two developers, 26 days: the structure should be
navigable on day one and add no ceremony.

---

## 3. Data Model

Entities, their store (per D6), provenance obligations, relationships and phase. This
realizes `SAFE-940` and `SAFE-1800`–`SAFE-1809`.

### 3.1 Provenance block — embedded in every health-bearing entity

Required by `SAFE-970`. Non-null enforcement at the storage layer means a health datum
without provenance **cannot be persisted** (`SAFE-521`, `TECH-902`).

| Field | Notes |
|---|---|
| `dataClass` | `CONFIRMED_CLINICAL` \| `SELF_REPORTED` \| `AI_GENERATED` \| `DEMO_SEED` — the `SAFE-940` four classes |
| `sourceType` | `document` \| `user_entered` \| `caregiver_entered` \| `ai_generated` \| `demo_seed` |
| `sourceDocumentId` | FK where applicable |
| `sourceReferenceId` | FK to `SourceReference` (page + bbox) where applicable |
| `observationDate` | When observed / issued. **Non-null for measurements** (`SAFE-1804`) |
| `recordedDate` | When it entered the system |
| `confirmationState` | `PROPOSED` \| `CONFIRMED` \| `EDITED_CONFIRMED` \| `DISCARDED` \| `UNCLEAR` |
| `confirmedBy` / `confirmedAt` | Who confirmed, when |
| `confidence` | Extraction confidence where applicable |
| `originalText` | Verbatim source text. **Immutable once confirmed** (`SAFE-1802`) |

### 3.2 Entities

| Entity | Store | Purpose | Key fields | Provenance | Relationships | Phase |
|---|---|---|---|---|---|---|
| **Profile** | Device | The person and their context | `id`, `displayName`, `avatar`, `userContext` (CARE/WELLNESS/BOTH), `dayAnchors`, `pinHash?`, `preferences`, `avoidedMovementIds` | n/a (not health data) | owns everything below (`PRIV-1808`) | **MVP** |
| **HealthDocument** | Server | A clinician-provided document | `id`, `deviceToken`, `name`, `documentType`, `documentDate`, `receivedDate`, `pageCount`, `processingState`, `blobRef` | `sourceType`, `dataClass` | has many `DocumentPage`, `ExtractedField` | **MVP** |
| **DocumentPage** | Server | One rendered page — the evidence surface for D16 | `id`, `documentId`, `pageNumber`, `width`, `height`, `renderRef` | inherits document | belongs to `HealthDocument` | **MVP** |
| **SourceReference** | Server → copied to device on confirm | **The artifact that makes verification real.** Locates text on a page | `id`, `documentId`, `pageNumber`, `bbox{x,y,w,h}`, `verbatimText` | — | referenced by `ExtractedField`, `CareInstruction`, `HealthRecord` | **MVP** |
| **ExtractedField** | Server | A *proposal*. Never a plan item | `id`, `documentId`, `proposedType`, `proposedFields{}`, `sourceReferenceId`, `confidence`, `reviewState` | `dataClass=AI_GENERATED`, state `PROPOSED`/`UNCLEAR` | → `SourceReference`; on confirm **creates** a `CareInstruction` | **MVP** |
| **CareInstruction** (abstract base) | Device | A confirmed clinical instruction | `id`, `profileId`, `instructionType`, `originalText`, `timingExpression?`, provenance block | `dataClass=CONFIRMED_CLINICAL` only (`SAFE-1801`) | has many `ChangeRecord`, `CareTask` | **MVP** |
| ├ **MedicationInstruction** | Device | Medicine + dose + timing | `medicineName`, **`doseTextAsTranscribed`** (immutable, `SAFE-504`), `withFood?`, `duration?` | as above | ← `CareInstruction` | **MVP** |
| ├ **PrescribedActivity** | Device | Clinician-prescribed exercise | `activityText`, `durationOrReps`, `frequency?`, `prescribedMarker=true` (`SAFE-510`) | as above | ← `CareInstruction` | **MVP** |
| ├ **MealInstruction** | Device | Dietary instruction | `instructionText`, `scope` (include/limit/avoid) | as above | ← `CareInstruction` | **MVP** |
| ├ **Precaution** | Device | Activity or general precaution | `precautionText`, `appliesTo[]`, `blocksMovementTags[]` | as above | consumed by routine validation (`SAFE-032`) | **MVP** |
| └ **Appointment** | Device | Checkup / test / follow-up | `what`, `dateOrInterval`, `attendedAt?` | as above | ← `CareInstruction` | **MVP** |
| **HealthRecord** | Device | A recorded measurement | `id`, `profileId`, `measureName`, `value`, `unit`, `context`, `observationDate` (**non-null**) | full block; **never derived or interpolated** (`SAFE-1805`) | → `SourceReference` | **MVP** |
| **CareTask** | Device | A scheduled instance of an instruction on a day | `id`, `dayPlanId`, `careInstructionId`, `placedTime`, `statedTimingExpression`, `state` | inherits instruction | → `CareInstruction` (**never** `ExtractedField`, `SAFE-1803`) | **MVP** |
| **DayPlan** | Device | One date's computed plan | `id`, `profileId`, `date`, `rolloverBoundary`, `careTasks[]`, `wellnessSlots[]` | derived, deterministic (D18) | → `Profile` | **MVP** |
| **Movement** | `shared/` catalog | A vetted exercise primitive | `id`, `name`, `category`, `intensity`, `defaultDuration`, `instructionLines[]`, `contraindicationTags[]`, `gentlerVariantId?`, `equipment=none` | authored, versioned (§8) | referenced by `Routine` | **MVP** |
| **Routine** | Device | A wellness routine instance | `id`, `origin` (GENERATED/PRESET), `requestedBudget`, `totalDuration`, `segments[]{movementId, duration}`, `catalogVersion`, `validationResult` | `dataClass=AI_GENERATED`; unusable without passing validation (`SAFE-1806`) | → `Movement` | **MVP** |
| **ActivitySession** | Device | A performed session | `id`, `profileId`, `routineId`, `segmentsCompleted`, `activeDuration`, `outcome` (complete/partial), `timestamp` | `sourceType=user_entered` | → `Routine` | **MVP** |
| **ActivityRecord** | Device | Any completion event (care or wellness) | `id`, `profileId`, `recordType`, `subjectRef`, `timestamp`, `outcome`, `correctionOf?` | record of *user report*, not verification (`PROD-1210`) | → `CareTask` \| `ActivitySession` | **MVP** |
| **DailySummary** | Device | End-of-day picture | `id`, `profileId`, `date`, `region1_recordedFacts`, `region2_historicalInfo`, `region3_userActivity`, `region4_aiInterpretation?` (**nullable — omitted on failure**), `nextDayPlanRef` | region 4 labelled `AI_GENERATED`; contains no value absent from r1/r2 (`SAFE-1807`) | → `DayPlan` | **MVP** |
| **AIRequestLog** | Server | Auditability without PHI | `id`, `regime` (ASSIST/GUIDE), `operation`, `schemaVersion`, `model`, `latencyMs`, `validationOutcome`, `retryCount`, `errorClass?` | **No prompt or response bodies. No clinical content** (`PRIV-1652`) | → operation | **MVP** |
| **ChangeRecord** | Device | Correction audit on confirmed data | `id`, `careInstructionId`, `changedBy`, `changedAt`, `previousValue`, `reason?` | `originalText` never altered (`SAFE-975`) | → `CareInstruction` | **MVP** |
| **Reminder** | Device | Derived due/overdue state | Not persisted — **computed** by the day engine from `CareTask.placedTime` + current time | derived | → `CareTask` | **MVP** (derived) |
| **PairingSession** | Server | Companion↔TV binding | `code`, `deviceToken`, `expiresAt` | no health data | → documents scope | **MVP** |
| **CaregiverAccount** | — | Remote caregiver identity | — | — | — | **P2** (`FUT-1200`) |
| **CarePlanVersion** | — | Versioned plan timeline | — | — | — | **P3** (`FUT-1301`) |

### 3.3 Enforced invariants

| Invariant | Mechanism |
|---|---|
| `SAFE-1800` — no AI→confirmed promotion | `ExtractedField` lives **on the server**; `CareInstruction` lives **on the device**. Confirmation is an explicit device-side create. There is no update path between them. |
| `SAFE-1801` — plan items are confirmed only | `CareInstruction` has no `PROPOSED` state; proposals are a different entity in a different database. |
| `SAFE-1802` — `originalText` immutable | Write-once column; corrections go to `ChangeRecord`. |
| `SAFE-1803` — schedules reference instructions only | `CareTask.careInstructionId` FK; `ExtractedField` is not even present on the device. |
| `SAFE-1804` — measurements are dated | Non-null `observationDate`. |
| `SAFE-1805` — no derived health values | No computed columns on `HealthRecord`; nullable-absent is the only representation of missing. |
| `SAFE-1806` — routines validated | `validationResult` non-null and `PASSED` required before render. |
| `SAFE-1807` — summary region 4 bounded | Generator receives only r1/r2 values; validator rejects unseen values. |
| `PRIV-1808` — profile isolation | Every device entity carries `profileId`; all queries are profile-scoped. |
| `PRIV-1809` — demo data identifiable | `dataClass=DEMO_SEED` at the data layer; badge in UI. |

---

## 4. API Design

Eighteen endpoints. Frozen on **Day 3** as `docs/API_CONTRACT.md` — this is the artifact
that lets two developers work in parallel. All over HTTPS (`PRIV-1620`), all under `/v1`,
all scoped by a device token.

**Profile** — profiles are device-local (D6); the server needs only a token identity.
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/devices/register` | Issue a device token on first run |
| `POST` | `/v1/devices/pairing-code` | Create a short pairing code for the companion (D22) |

**Documents**
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/documents` | Upload a document (from companion, or seeded) |
| `GET` | `/v1/documents` | List documents with processing + review state |
| `GET` | `/v1/documents/{id}` | Document detail |
| `GET` | `/v1/documents/{id}/pages/{n}/render` | **Page image; `?highlight=<sourceReferenceId>` returns it with the region highlighted, optionally cropped. The D16 evidence surface.** |

**Extraction**
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/documents/{id}/extract` | Start extraction; returns a job id (D9) |
| `GET` | `/v1/extraction-jobs/{id}` | Poll status; on completion returns proposals |
| `GET` | `/v1/documents/{id}/proposals` | Proposals with `sourceReferenceId` + confidence |

**Verification** — the confirmation *decision* is recorded server-side for audit; the
resulting confirmed instruction is written **device-side** (D6).
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/proposals/{id}/review` | Body: `confirm` \| `edit` \| `discard` \| `unclear` (+ edited fields). Returns the confirmed payload for device persistence, **including pre-generated plain-language text (D10)** |

**Wellness**
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/routines/generate` | Body: budget, goal, preferences, active precaution tags. Returns a **validated** routine of catalog IDs, or a preset fallback (D24) |
| `GET` | `/v1/catalog` | Catalog version check (content is bundled, D17) |

**AI — bounded**
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/assist/plain-language` | ASSIST transform of one confirmed instruction. Normally called once at confirmation time (D10) |
| `POST` | `/v1/summary/interpretation` | Generates **region 4 only**, from r1/r2 inputs. Omitted on failure |
| `POST` | `/v1/requests/interpret` | Parses a wellness request; **returns a refusal for out-of-scope clinical requests** (`SAFE-916`) |

**Health / diagnostics**
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/health` | Liveness for the client's degraded-mode banner |

**Deliberately absent — and why.** No care-plan, today-plan, care-task-completion, progress,
session or settings endpoints. All of that is **device-local and offline** (D6, D10, D18,
D19). Adding server endpoints for them would break the offline guarantee and duplicate the
source of truth. This is the clearest expression of "do not overbuild APIs."

---

## 5. AI Architecture

### 5.1 The regime boundary

`SAFE-900` requires every AI operation to be assigned to exactly one regime.

| | **ASSIST (clinical)** | **GUIDE (wellness)** |
|---|---|---|
| Role | **Transformer** of provided information | **Generator/selector** within a safety envelope |
| May originate content | **No** | Yes, but only by selecting catalog IDs |
| Input | Document text spans, or one confirmed instruction's own text | Time budget, goal, preferences, precaution tags, catalog |
| Output | Proposed fields + `sourceReferenceId`, or simplified prose | Ordered list of `{movementId, duration}` |
| Validation | No value absent from source; source reference present | Catalog membership; precaution filter; structure; duration sum |
| Fallback | Verbatim original text | Vetted preset |
| Terminal control | **Human confirmation** (`SAFE-501`) | Deterministic validator (`SAFE-917`) |

The two regimes are **physically separate modules** (`backend/ai/assist/`, `backend/ai/guide/`)
with separate prompts and separate schemas. There is deliberately **no shared generic
`ai.call()` helper**, because a shared helper is how regime boundaries erode.

### 5.2 Where AI ends and deterministic logic begins

```
  AI MAY DO                      │  DETERMINISTIC ONLY — AI IS ABSENT
  ─────────────────────────────  │  ─────────────────────────────────────
  Structure document text into   │  Whether a proposal becomes a plan item
    proposals (never plan items) │    → human confirmation (SAFE-501)
  Simplify prose-bearing source  │  What is on today's plan
    instructions                 │    → Day/Plan engine (D18)
  Select + sequence catalog IDs  │  Session timing, advancement, completion
  Write summary region 4         │    → Session runtime (D19)
  Parse a wellness request       │  Overdue derivation, streaks, progress
  Refuse out-of-scope requests   │  Whether a routine is safe → validator (D14)
                                 │  Provenance, dates, dose text (SAFE-504)
```

`SAFE-921`: the guardrail's rules are expressed in `backend/guardrail/` in a form readable
and testable **independently of any prompt or provider**.

### 5.3 ASSIST operations

**A1 — Document structuring.** Input: page text spans with bounding boxes. Output: proposals,
each carrying `proposedType`, `proposedFields`, `sourceReferenceId`, `confidence`.
Constraints: no field may be emitted that is absent from the source (`SAFE-912`); dose text
copied verbatim, never normalized (`SAFE-504`); low confidence → `UNCLEAR` rather than a
guess (`SAFE-503`). All output lands `PROPOSED` (`SAFE-913`).

**A2 — Plain-language transform ("What this says").** Per Conflict 0.3. Input: **one
confirmed instruction's own text only**. Applied to prose-bearing sources (exercise, diet,
precautions). For single-line prescriptions the output is *structural* — the timing
expressed in plain words — with the verbatim dose line always displayed alongside. Never
drug knowledge, indications, effects or rationale (`SAFE-731`, `SAFE-507`, `SAFE-915`).
Generated **once at confirmation** and cached (D10).

**A3 — Summary region 4.** Input: only region 1 and 2 values with their dates. Prohibited:
clinical improvement/deterioration, predictions, causal claims, comparison to norms
(`SAFE-703`, `SAFE-1420`). Validator rejects any value not present in r1/r2 (`SAFE-1807`).
On failure, region 4 is **omitted** — safe because of `SAFE-1410` separation.

### 5.4 GUIDE operations

**G1 — Request interpretation.** Extract budget, goal, preferences. Out-of-scope clinical
requests return a refusal object; the client renders a brief warm redirect to the clinician
(`SAFE-916`). No partial answer before refusing.

**G2 — Routine generation.** The model receives the **filtered** catalog (movements whose
`contraindicationTags` intersect the profile's active precaution tags are removed *before*
the call) and returns `{movementId, duration}` pairs only. Then the deterministic validator
runs (§8.4). Failure → vetted preset (D24).

### 5.5 Auditability

`AIRequestLog` records regime, operation, schema version, model, latency, validation
outcome, retry count and error class. It records **no prompt or response bodies and no
clinical content** (`PRIV-1652`). This gives genuine auditability of *behaviour* without
creating a PHI store — the correct trade for a health product.

---

## 6. Document Pipeline

### 6.1 Flow

```
 [companion upload]  or  [seeded demo document]
            │
            ▼
   HealthDocument (server)  ── parse ──▶ DocumentPage[] + text spans with bbox  (D15)
            │                                            │
            │                                            ▼
            │                              SourceReference[] (page + bbox + verbatim)
            │                                            │
            ▼                                            ▼
     ASSIST A1 structuring  ────────────────▶ ExtractedField[]  state = PROPOSED
            │                                   (each → sourceReferenceId)
            │                              low confidence → UNCLEAR  (SAFE-503)
            ▼
   ┌────────────────────── HUMAN REVIEW ON FIRE TV ──────────────────────┐
   │  LEFT PANE: server-rendered page image, source region HIGHLIGHTED   │
   │             (D16 — the ORIGINAL document, not extracted text)       │
   │  RIGHT PANE: proposed structured fields, dose text as transcribed   │
   │  ACTIONS:   Confirm · Edit · Discard · Unclear                      │
   │  One item at a time, "3 of 11" position indicator (PROD-623)        │
   └─────────────────────────────┬───────────────────────────────────────┘
                                 │  confirm / edit+confirm
                                 ▼
            POST /v1/proposals/{id}/review  → returns confirmed payload
                                 │           + pre-generated plain-language (D10)
                                 ▼
             CareInstruction written to DEVICE store (canonical, D6)
                                 │
                                 ▼
                   Day/Plan engine (deterministic, D18) → CareTask on Today
```

### 6.2 How the user actually verifies

The review screen shows a **cropped, zoomed render of the document region with the
highlight drawn**, plus a toggle for the full page. The user compares what the document
says against what the system proposes. Because the left pane is a rendering of the actual
PDF — not a re-display of extracted text — a misread is visible. **This is the fix for
review finding `S1` and it is the single most important screen in the product.**

### 6.3 Ingestion options compared

| Option | Genuine? | Reliable? | Demo quality | Verdict |
|---|---|---|---|---|
| Bundled synthetic documents | Pipeline yes, transfer no | **Very high** | Good | **Adopt as the demo path** |
| Companion upload | **Yes, fully** | Medium (network, pairing) | Very good — shows the real route | **Adopt as a real, secondary path** |
| Local network transfer | Yes | **Low** — guest wifi, subnets | Risky | Reject (D22) |
| Pre-seeded proposals | **No — theater** | High | Hollow | **Reject** (`PROD-2111`) |
| OCR of scanned images | Yes | **Low** in 26 days; destroys bboxes | High if it works | **Defer to `FUT-1403`** |
| Text-layer PDF extraction | **Yes** | **High** | Good; enables D16 | **Adopt** (D7/D15) |

**Chosen combination: text-layer PDFs (D7) + bundled documents as the primary demo path +
companion upload as a genuinely working secondary path.** Nothing is pre-processed, so
`PROD-2111` holds and `OQ-13` is withdrawn. The demo can show the reliable path while the
real path exists and is demonstrable on request — the strongest combination of genuine
functionality, reliability and demo quality.

---

## 7. Wellness Architecture

### 7.1 Movement catalog schema

```
Movement {
  id                     "mob_neck_rolls_seated"        // stable, referenced by AI
  name                   "Seated neck rolls"
  category               WARMUP | MOBILITY | LIGHT_STRENGTH | STRETCH
                         | BREATHING | RELAXATION | COOLDOWN
  intensity              VERY_LOW | LOW | MODERATE       // never HIGH (SAFE-030)
  position               SEATED | STANDING | STANDING_SUPPORTED
  defaultDurationSec     60
  minDurationSec / maxDurationSec
  instructionLines[]     ["Sit tall, feet flat.", "Slowly turn your head right.",
                          "Hold, then return to centre."]   // short lines (PROD-602)
  contraindicationTags[] ["no_neck_movement", "avoid_standing", "no_exertion"]
  gentlerVariantId?      "mob_neck_turns_seated"
  equipment              NONE                            // always
  catalogVersion         "1.0.0"
}
```

**Safety metadata is the point of the schema.** `contraindicationTags` are the join key to
confirmed `Precaution.blocksMovementTags` — this is how `SAFE-032` becomes a deterministic
filter rather than a prompt instruction. Every entry is authored to satisfy `SAFE-030`
(low-to-moderate, bodyweight, non-technical, low-impact, no equipment, unsupervised-safe)
and to exclude everything in `SAFE-034` **by construction**. No entry may be added that
would fail `SAFE-034` — the catalog itself is the safety boundary.

### 7.2 Composition — ~45 movements across 6 categories

Warm-up 6 · Mobility 12 · Light strength 8 · Stretch 10 · Breathing 5 · Relaxation 4.
Roughly half are seated or standing-supported, so a Care or older user is well served
(`SAFE-037`).

### 7.3 Request → validated routine

```
"15 minutes, wake me up"   (or: preset chip 15 min + goal chip "Wake up")
        │
        ▼  G1 interpret → { budgetSec: 900, goal: ENERGIZE, prefs, avoidIds }
        ▼  filter catalog: remove movements whose contraindicationTags
           intersect the profile's ACTIVE confirmed precaution tags  ← BEFORE the AI call
        ▼  G2 generate: model returns [{movementId, durationSec}, ...] — IDs only
        ▼  DETERMINISTIC VALIDATOR (SAFE-917):
              1. every movementId exists in catalog vX              → else FAIL
              2. no movement was filtered out                       → else FAIL
              3. opens with WARMUP, closes with COOLDOWN/BREATHING
                 if any exertion segment present (SAFE-811)         → else FAIL
              4. Σ durations within tolerance of budget (PROD-121)  → else FAIL
              5. each duration within movement's min/max            → else FAIL
        ▼  PASS → Routine { validationResult: PASSED, catalogVersion }
           FAIL → discard, serve vetted preset of same duration (D24), log failure
        ▼  Routine Preview: every segment + explicit total (PROD-593)
        ▼  Session runtime (deterministic, D19)
```

Because the model emits only IDs, **every one of the five checks is a set or arithmetic
operation.** `SAFE-917`'s "deterministic validation" becomes literally true — which it
cannot be against free text.

### 7.4 Presets

For each budget (10/15/20 min) and each goal, one hand-authored preset routine exists in the
catalog package. These serve offline operation (Tier 0) and the D24 fallback. They are
authored, pre-validated, and never AI-touched.

---

## 8. Fire TV UX Architecture

### 8.1 Screen hierarchy

```
Profile Select  ── always the entry point (PRIV-700); name + avatar only (PRIV-702)
   └─ [optional PIN]
      └─ TODAY  ── home, and the convergence point of all navigation (PROD-500)
         ├─ Item Detail  → Mark done/skipped · "What this says"
         ├─ Care Plan    → Medications · Activity · Meals · Precautions · Appointments
         ├─ Health Info  → recorded measurements, each with date + source
         ├─ Wellness     → presets/goals → Routine Preview → Session Player → Complete
         ├─ Progress     → recent activity · streak · Daily Summary
         ├─ Documents    → list → Review & Confirm (two-pane, D16)
         └─ Settings     → profile · context · PIN · spoken output · orientation · reset
```

Care Plan, Health Info and Documents are hidden for a WELLNESS profile (`PROD-503`). All
sections are siblings one level below Today (`PROD-502`); any destination is ≤3 actions
from Today (`PROD-432`).

### 8.2 Focus and D-pad model

| Rule | Implementation |
|---|---|
| Every actionable element D-pad reachable (`HACK-414`) | Explicit focus order per screen; no element reachable only by an unusual path |
| Focus always clearly visible (`HACK-413`) | Scale + border + background shift **together** — never colour alone (`PROD-435`) |
| Focus never lost (`PROD-440`) | On every state change, focus is restored to a sensible visible element. A focus-restorer per screen |
| Single primary axis (`PROD-501`) | Today is vertically ordered by priority; movement within a row is horizontal. No 2-axis mazes for primary flows (`PROD-433`) |
| Arrival focus | Today arrives with the **Now card** focused (`PROD-551`) |
| Forgiving input (`PROD-437`) | Repeated/accidental presses tolerated; destructive actions confirmed; no time-limited prompts |

### 8.3 Back behaviour (`PROD-430`)

Back moves **exactly one level** toward Today. From Today, Back requests exit with
confirmation. **Back during a guided session requires confirmation** and never silently
discards a session. No modal dead ends (`PROD-504`).

### 8.4 Safe zone, typography, colour

**[VERIFIED]** Nothing in the outer **5%** of any edge; all focused items and text within the
inner **90%** (`HACK-410`). Body text **≥14sp** (`HACK-411`) — treated as a **floor, not a
target**; primary card text substantially larger (`PROD-434`). Reference layout 1080p =
1920×1080px, 320dpi, 960×540dp (`HACK-412`). `sp` for text, `dp` for spacing (`HACK-416`).
Less saturated, cool-leaning palette (`HACK-415`); **status never encoded in colour alone**
(`PROD-435`) — every state carries text and/or shape. A single `design/` module owns the
token set so these are structurally enforced rather than per-screen discipline.

### 8.5 State presentation

| State | Requirement |
|---|---|
| **Loading** | Determinate and honest, with a timeout path (`PROD-439`). Never an indefinite spinner |
| **Empty** | Today with no confirmed items explains what to add and offers wellness immediately (`PROD-554`) |
| **Error** | Plain language, non-alarming, always with a way forward. Never a stack trace or code |
| **Overdue** | Factual and calm — states only that an item is not marked done. No alarm styling, no scolding (`PROD-555`, `PROD-1111`). **No advice about what to do** (`SAFE-1112`) |
| **Degraded** | A quiet banner naming what is unavailable; Tier 0 unaffected (D20) |
| **Session** | Screen held awake; reminders suppressed (`PROD-1114`); pause/resume/exit always available |

### 8.6 Sensitive information handling

Profile Select shows no health information (`PRIV-702`). Profile switch clears the prior
profile's health data from view immediately (`PRIV-703`). Care surfaces return to a
non-disclosing state after idle — **[P2 scope]** per `PRIV-1701`/`TECH-1702`; the MVP
implements the profile gate and switch-clear, which are the load-bearing controls. Any
ambient surface outside a profile is non-specific (`PRIV-1130`).

### 8.7 Voice

**[VERIFIED]** Fire TV does not support the Android speech recognizer used by Leanback's
`SearchFragment` (*"Leanback's `SearchFragment` … is not supported"*; the speech recognizer
it looks for *"produces an error"*), and Play Services are unavailable. **Therefore: no voice
input is built in the MVP** (D13 of the review; confirmed here). The request-understanding
layer stays decoupled from the input channel (`PROD-451`) so voice can be added if a
documented path emerges. **Every journey is complete on the D-pad path** (`PROD-403`,
`PROD-2102`). No microphone API is assumed anywhere in the architecture.

---

## 9. Companion Architecture

**What it is.** One mobile web page served by the backend (D21).

**Responsibilities.** Document upload. Optional awkward text entry (profile display name,
care-team contact string).

**Explicitly not its responsibilities.** Document review or confirmation — that stays on Fire
TV, because it is the core safety moment (`SAFE-501`) and the demo centrepiece
(`PROD-2101`). Not Today, care plan, health info, sessions, progress, summaries or settings.
It displays **no health information at all**, which also keeps it outside the sensitive-data
surface.

**Flow.** TV shows a 6-character pairing code → user opens the companion URL on a phone →
enters the code → uploads a PDF → TV polls and shows the document arriving. No accounts, no
login, no personal identifiers (D22).

**Guardrail against scope creep.** The companion has **no route** that renders clinical
content. If a future change needs one, that is a product decision requiring approval
(`RULE-002`), not an implementation detail.

---

## 10. Privacy & Safety Architecture

| Control | Implementation | Requirement |
|---|---|---|
| Minimum necessary data | Every field justified by a feature ID; no analytics collection | `PRIV-601`, `PRIV-1600` |
| Profile isolation | All device queries profile-scoped; no shared household health store | `PRIV-1511`, `PRIV-1512`, `PRIV-1808` |
| Optional PIN | D-pad numeric, hashed at rest, non-punitive retry | `PRIV-701` |
| Sensitive display rules | No health data before profile entry; immediate clear on switch | `PRIV-702`, `PRIV-703` |
| No automatic sensitive spoken output | No TTS in MVP; the preference exists and defaults **off** | `PRIV-704` |
| Secrets | Server-side env vars only; client holds no credential; exclusion config in first commit | `PRIV-1640`, `PRIV-1641` |
| TLS | All health information encrypted in transit; plaintext prohibited | `PRIV-1620` |
| Logging | Identifiers and outcomes only; **no prompt/response bodies**; verbose off in submitted build | `PRIV-1650`–`PRIV-1652` |
| Synthetic demo data | `dataClass=DEMO_SEED` + visible UI badge; no real personas | `HACK-980`, `PRIV-981`, `PRIV-982` |
| Authorization boundary | Device token scopes server documents; profile+PIN gates device data. No server-held confirmed clinical data → no full auth mandate | `PRIV-1630`, `PRIV-1631` |
| Deletion / reset | Per-profile delete states plainly what is removed; document delete removes blob + renders + proposals | `PRIV-602`, `PRIV-1612`, `PROD-1531` |
| AI data handling | Only synthetic documents sent during the hackathon; minimum content per call; provider terms reviewed | `PRIV-1622` **[VERIFY BEFORE SUBMISSION]** |
| Failure-safe behaviour | Guardrail fails closed; safety checks block, convenience degrades | `SAFE-920`, `TECH-931` |
| Prompt injection *(new — review finding `S2`)* | Document text passed strictly as **data**, never as instruction context; the confirmation gate plus the D16 original-document view are the terminal controls | Closes `S2` |
| First-run acknowledgement *(new — review finding `S5`)* | One plain-language screen before first entry into a Care profile | Strengthens `SAFE-950`/`SAFE-951` |

---

## 11. Hackathon Mapping

| Requirement | How the architecture satisfies it | Status |
|---|---|---|
| Runs on Fire OS or Vega OS | D1 Fire OS; Android APK | **[VERIFIED]** requirement; satisfied by design |
| Working demo | Tier 0 offline care path + Tier 1 wellness; both journeys in §13 | Plan |
| Device or simulator footage | D30, gated by **P1** on Day 1 | **[VERIFY BEFORE SUBMISSION]** whether an Android TV emulator qualifies as "the Fire TV/Vega simulator" |
| Repository with all source + instructions | §2 structure; `README.md` per `PROD-2120` | Plan |
| Repo access for judges | Public + OSS licence (also supports the Open Source mini challenge) | Configure **Day 3**, not the final week |
| Public demo video <3 min | §13 storyboard, 2:50 allocation | Plan |
| Project description | `docs/` drafted continuously | Plan |
| Product Feedback (required) | `docs/PRODUCT_FEEDBACK.md` from Day 1 | Plan |
| Licensing | OSS licence at root; every dependency licence recorded | `HACK-812`, `HACK-815` |
| Originality | New project; movement catalog authored, not copied | `HACK-813`, `HACK-814` |
| Testing instructions | README: seed script, local backend, sideload steps | `HACK-805` |
| Friction log (up to 10% bonus) | `docs/FRICTION_LOG.md` from Day 1 | `HACK-826` |
| Deadline | Submit Day 26 (2026-10-22), one day early | `HACK-802` |
| Eligibility | **Owner action, Day 1** | **[VERIFY]** `OQ-11` |
| Re-verify all rules before submission | Day 25 task | `CC-05` **[VERIFY BEFORE SUBMISSION]** |

No new hackathon rules are invented here. Items not verifiable from the source documents are
marked **[VERIFY BEFORE SUBMISSION]**.

---

## 12. Validation Milestones (POCs)

All five run in the first four days. Total ~2.5 developer-days, parallelized across two
people. **These gate deeper development.**

### P1 — Fire TV Hello World  *(Developer A, Day 1 — blocks everything)*

**Objective.** Prove an app can run on a Fire TV target from this Windows 11 machine, and
that footage of it can satisfy `HACK-806a`.
**Build.** Minimal Kotlin/Compose app; one screen, one text label. Install and launch on the
best available target per D30's preference order. Capture a screenshot and a short screen
recording.
**Success.** App launches and renders on a physical Fire TV device **or** a TV emulator at
1080p; footage is captured.
**Failure.** No target runs, or footage would not credibly show a Fire TV device/simulator.
**Fallback.** Initiate Fire TV Stick purchase **immediately** (Day 1, not Day 10) and
continue P2/P4/P5 on the emulator meanwhile. If nothing runs at all, the project is not
submittable — escalate to the owner the same day.

### P2 — D-pad / focus / safe-zone validation  *(Developer A, Day 2)*

**Objective.** Prove the chosen framework delivers judge-grade TV focus behaviour, and
resolve the **D2 reversal trigger**.
**Build.** One screen, 6+ focusable cards in a row and a column; visible focus treatment; a
5% safe-zone overlay; a 14sp text sample beside the intended primary size.
**Success.** All cards reachable by D-pad; focus always visible and never lost; nothing in the
outer 5%; body text ≥14sp; primary text comfortably readable at distance.
**Failure.** Focus gets lost or stuck; focus states unclear; unreachable elements; or the work
exceeds 1.5 days.
**Fallback.** Invoke the **D2 reversal**: switch to React Native for TV using the official
`react-native-multi-tv-app-sample`. D16's server-rendered image means the document feature is
unaffected by this switch.

### P3 — Timed guided session  *(Developer A, Day 3)*

**Objective.** Prove the session runtime is smooth and the screen stays awake.
**Build.** A 60-second three-segment sequence with automatic advancement, a visible
countdown, pause/resume, and `FLAG_KEEP_SCREEN_ON` held for the duration.
**Success.** Segments advance accurately; countdown does not stutter; screen does not sleep;
pause/resume works; the flag is released on exit.
**Failure.** Visible stutter on target hardware, or the screen sleeps mid-session.
**Fallback.** Reduce animation to static text plus a numeric countdown (`PROD-438` already
favours calm, minimal motion — so this is a legitimate simplification, not a compromise). If
the screen still sleeps, investigate an alternative wake mechanism before building §14
Phase 5.

### P4 — Document region rendering + highlight  *(Developer B, Day 2–3)*

**Objective.** Prove D16 — the most important feature in the product — is achievable.
**Build.** Server: load a text-layer PDF, extract text spans with page + bbox, rasterize the
page, draw a highlight rectangle over one span, return a cropped PNG around it. Client:
display that PNG beside static placeholder fields.
**Success.** The returned image visibly and correctly highlights the right text, is legible at
10 feet when cropped and zoomed, and round-trips in under ~2 seconds.
**Failure.** Coordinates do not align with rendered pixels; image illegible on a TV; or
rendering is unacceptably slow.
**Fallback.** Increase crop zoom and render only the region rather than the page. If geometry
alignment fails entirely, fall back to **client-side `PdfRenderer` + Canvas overlay** (the
D16 alternative). If *both* fail, show the full page image plus the verbatim source text as a
clearly-labelled interim — but this weakens `S1` and must be escalated, not quietly accepted.

### P5 — Structured AI output reliability  *(Developer B, Day 3–4)*

**Objective.** Measure whether D11's strict-schema approach is viable, before the pipeline
depends on it.
**Build.** One extraction call against a real synthetic prescription PDF using tool-use with a
strict schema. Run ~20 times. Record schema-valid rate, retry-recovery rate, latency
distribution, and whether dose text is reproduced verbatim.
**Success.** ≥90% valid on first attempt, ≥98% after two retries, p95 latency acceptable for a
job-and-poll flow, and **dose strings reproduced verbatim in 100% of cases** (`SAFE-504` is
non-negotiable — a single normalized dose is a hard failure).
**Failure.** Frequent malformation, or any dose alteration.
**Fallback.** Narrow the schema (one field group per call rather than a whole document);
switch to a more capable model for extraction; add a deterministic verbatim-dose check that
rejects any proposal whose dose string is not a literal substring of the source text. **That
substring check should be implemented regardless — it is cheap and it makes `SAFE-504`
mechanically enforced rather than model-dependent.**

---

## 13. Demo Spine

2:50 total. Fire TV visibly central throughout — every navigation is a D-pad press with a
visible focus move. Doubles as the continuous integration test (`DP-15`).

| # | Time | Beat | Real / Seeded |
|---|---|---|---|
| 1 | 0:00–0:18 | Fire TV home → launch → **Profile Select** (name + avatar only). One sentence of problem framing. | App launch real; profiles seeded |
| 2 | 0:18–0:33 | Care profile → **Today**. Now card fills the screen: *"Before breakfast — Tablet A, 1 tablet,"* dose line as transcribed, quiet source line *"From Prescription, 12 Aug 2026."* Next + Done below. | Day engine real, provenance real |
| 3 | 0:33–0:46 | Select → **Item Detail** → **Mark as taken**. Now advances. Calm acknowledgement. | Completion write real |
| 4 | 0:46–1:34 | **THE CENTREPIECE.** Documents → one in *Needs Review* → **two-pane review**: rendered document page with the source region **highlighted** on the left, proposed fields on the right. Dose text matches. Press **Confirm**. Cut to Today — the item is now in the plan. Narration: *nothing reaches this person's plan until a human has checked it against the document.* | **All real**: PDF, extraction, bbox highlight, gate, plan mutation |
| 5 | 1:34–1:44 | An out-of-scope clinical question is **declined** in one line and redirected to the clinician. | Real guardrail refusal path |
| 6 | 1:44–2:04 | Wellness profile → Today → **15 min** preset + goal chip → **Routine Preview**: 2 warm-up / 5 mobility / 5 light / 3 cooldown, explicit total. **Non-voice path throughout.** | Real generation + real validation |
| 7 | 2:04–2:28 | **Start**, remote down. **Session Player** advances automatically: activity, remaining time, short instructions, progress, next. Skip to completion; session recorded. | Real timing/recording; video time-compressed — **narration must say so** |
| 8 | 2:28–2:50 | **Progress** streak updates → **Daily Summary**: recorded facts · historical info with dates · user activity · and, visibly separated and labelled, the AI summary. Close on that separation. | Real records, real 4-region render |

**Both journeys present.** Care gets 48 seconds (beat 4) — the largest single allocation, by
design, so the wellness half cannot crowd out the healthcare experience (`R-18`).

**Must not be shown:** any voice interaction (D13/§8.7); an AI answering a clinical question
(show the refusal instead); any health value without its date; live OCR; clinical-improvement
framing; real patient data; any credential on screen.

---

## 14. 26-Day Execution Plan — Two Developers

**Day 1 = 2026-09-27. Day 26 = 2026-10-22.** Submission target Day 26, one day before the
2026-10-23 12:00 PT deadline.

**Developer A — Fire TV application** (the primary product experience).
**Developer B — backend, AI, catalog, document pipeline, companion.**

**Hard dependency:** `API_CONTRACT.md` frozen Day 3. Before that, A works against local
stubs. This is what makes genuine parallelism possible.

### Phase 0 — Validation & decisions (Days 1–4)

| Day | Developer A | Developer B | Gate |
|---|---|---|---|
| 1 | **P1 Hello World** on best target (D30). Owner: confirm eligibility (`OQ-11`) + device availability. Start `FRICTION_LOG.md`. | Repo init, `.gitignore` + secrets exclusion **first commit** (`PRIV-1641`), OSS licence, repo access for judges (`HACK-805a`). Author 2 synthetic PDFs. | **P1 must pass or the target problem escalates today** |
| 2 | **P2 focus/safe-zone.** Resolve **D2 reversal trigger** by end of day. | **P4 begins**: PDF text+bbox extraction, page rasterize, highlight draw. | D2 locked |
| 3 | **P3 timed session.** Begin `design/` token module. | **P4 completes.** Co-author `API_CONTRACT.md`; **freeze it.** | **API contract frozen** |
| 4 | Navigation shell + Profile Select + Back semantics. | **P5 structured-output reliability** + verbatim-dose substring check. Author remaining synthetic PDFs. | **P5 pass/fail decides D11 tuning** |

### Phase 1 — Foundations (Days 5–8)

| Day | Developer A | Developer B |
|---|---|---|
| 5 | Room schema with **non-null provenance** (`SAFE-970`, `TECH-902`). Provenance-assertion component. | **Movement catalog authoring begins** (~45 movements, `SAFE-030`/`SAFE-034` by construction). |
| 6 | **Day/Plan engine (D18)** + unit tests: anchors, overdue, rollover, reference cards. | Catalog complete + presets. `LlmClient` abstraction (D8). |
| 7 | **Today screen**: Now/Next/Overdue/Done, one-line card provenance (Conflict 0.5). | **Guardrail module (D14)** scaffolding + first validators. Document endpoints. |
| 8 | Item Detail + mark taken/skipped + `ActivityRecord`. | Extraction job flow (D9) + ASSIST A1 structuring → proposals with `sourceReferenceId`. |
| — | **Gate: demo beats 2–3 run on device from seeded local data.** | |

### Phase 2 — ASSIST, the centrepiece (Days 9–14)

| Day | Developer A | Developer B |
|---|---|---|
| 9 | Care Plan read views — all five instruction types. | Page render + highlight endpoint productionized (D16). |
| 10 | Health Info with full provenance; `SAFE-520` historical-vs-current treatment. | `POST /proposals/{id}/review` incl. **D10 pre-generation** of plain-language text. |
| 11 | **Review & Confirm two-pane screen** — evidence image + proposed fields. | ASSIST A2 "What this says" (Conflict 0.3). Guardrail: source-containment validator. |
| 12 | Review queue: one-at-a-time, "3 of 11", Confirm/Edit/Discard/Unclear. | **Deploy backend to hosted HTTPS (D28)** — two weeks before recording. |
| 13 | Confirm → device write → Day engine → Today. **End-to-end care loop.** | Guardrail tests for `SC-20`–`SC-24`. Companion page (D21) + pairing (D22). |
| 14 | Integration + polish of the care path. | Integration support; document delete/reset (`PRIV-1612`). |
| — | **Gate: demo beat 4 runs end to end — the single most important milestone in the plan.** | |

### Phase 3 — GUIDE & PROGRESS (Days 15–19)

| Day | Developer A | Developer B |
|---|---|---|
| 15 | Wellness entry: presets + goal chips (non-voice, `F-G02`). | GUIDE G2 generation + **deterministic validator** (§7.3). |
| 16 | Routine Preview with explicit total (`PROD-593`). Precaution interstitial (`SAFE-032`). | G1 request interpretation + **out-of-scope refusal** (`SAFE-916`). |
| 17 | **Session Player (D19)**: auto-advance, countdown, pause/resume/exit, screen-on. | Preset fallback path (D24). Guardrail tests `SC-25`–`SC-28`. |
| 18 | Session completion + `ActivitySession` recording, partial handling. Progress + streak. | Summary region 4 generator (A3) with r1/r2-only inputs + validator (`SAFE-1807`). |
| 19 | **Daily Summary** four-region render (`SAFE-1410`), region 4 omitted on failure. | Degraded-mode + `/v1/health`; per-operation fallback wiring (D24). |
| — | **Gate: demo beats 6–8 run end to end. Full §13 spine rehearsable.** | |

### Phase 4 — Safety, privacy, accessibility (Days 20–22)

| Day | Developer A | Developer B |
|---|---|---|
| 20 | PIN (`F-X03`); profile switch clear (`PRIV-703`); **first-run acknowledgement (`S5`)**. | Logging audit (`PRIV-1650`–`1652`) — confirm no clinical content, no prompt bodies. |
| 21 | Demo-data badges (`F-X07`); care-team card (`F-A13`); empty/error/degraded states. | **Prompt-injection hardening (`S2`)**; adversarial synthetic document test. **Full dry-run submission with whatever exists** (mitigates `R-19`). |
| 22 | VoiceView content descriptions (`HACK-417`); string review for overclaiming (`SAFE-952`). | `PRIV-1622` provider-terms verification recorded; secret scan (`DOD-14`). |
| — | **Gate: every §35.2 and §35.3 zero-tolerance criterion verified at zero.** | |

### Phase 5 — Test, rehearse, submit (Days 23–26)

| Day | Both developers |
|---|---|
| 23 | Full manual TV checklist: D-pad traversal every screen, safe zone at 1080p, type sizes, focus retention, Back semantics. Both journeys with **no voice and no typing**. |
| 24 | **Rehearse the entire demo offline** (`R-16`). Exercise every degraded path. Time to <3:00. Finalize `DEMO_SCRIPT.md`; review narration against `SAFE-2110`. |
| 25 | **Record and cut the video** (<3 min, device/simulator footage, silence or original audio). Upload publicly. Write description (`HACK-807`) + Product Feedback (`HACK-808`). Finalize friction log. **Re-verify all `HACK-` items (`CC-05`).** |
| 26 | `README.md` final (`PROD-2120`); verify repo access; final secret scan; **submit**. Buffer day. |

### Stretch / optional — only if a gate clears early

Marked explicitly optional; **never** at the expense of a gate. Manual measurement entry
(`F-A16`); new-document change handling (`F-A12`); QR pairing over the same code (D22);
client-side `PdfRenderer` optimization (D16 alternative); richer preference learning
(`F-G10`); idle timeout (`PRIV-1701`).

### Genuine-but-simpler implementations (not theater)

These are legitimate simplifications that keep functionality real: bundled documents as the
demo path while companion upload also genuinely works (§6.3); presets as the routine fallback
rather than a second generator; behavioural-only insights rather than trend analysis
(`SAFE-703` requires this anyway); one hosted backend instance rather than redundant
infrastructure; manual TV checklist rather than Appium automation (D29).

---

## 15. Team Split

### Developer A — Fire TV application
Compose/Kotlin UI and design system; navigation, focus, Back semantics; Room schema and
provenance enforcement; **Day/Plan engine (D18)**; **Session runtime (D19)**; all ten screens;
Review & Confirm two-pane UX; device-side offline behaviour; TV manual checklist. **Owns
P1, P2, P3.**

### Developer B — Backend, AI, documents, catalog
FastAPI service; PDF parse + text/bbox extraction; **page render + highlight (D16)**; ASSIST
and GUIDE modules; `LlmClient` abstraction; **guardrail validators (D14)**; movement catalog
authoring; synthetic document authoring; companion page + pairing; deployment; guardrail and
validator tests. **Owns P4, P5.**

### Shared
`API_CONTRACT.md` (co-authored Day 3); the demo script; friction log; Product Feedback;
README; integration sessions at each gate; final rehearsal and recording.

### Integration points
Day 3 (contract freeze) · Day 8 (proposals reach the TV) · Day 13 (confirm → device →
Today) · Day 16 (routine generation reaches the TV) · Day 19 (summary) · Day 24 (full
rehearsal).

### Must NOT be parallelized
**Catalog before GUIDE AI** — G2 cannot be built or validated without it (Day 6 before Day
15). **API contract before client data layer** — building the client's remote layer against
an unfrozen contract guarantees rework. **Guardrail before any AI surface ships** (`DP-05`).
**P4 before the Review screen** — do not build the two-pane UX before the evidence image is
proven. **P1 before everything.**

### Safely parallelized
Design system ‖ document pipeline. Day engine ‖ extraction. Today screen ‖ guardrail.
Session runtime ‖ summary generator. Catalog authoring ‖ all client work. Synthetic document
authoring ‖ everything.

---

## 16. Definition of Done

| Area | Done when |
|---|---|
| **1. Architecture** | This document approved; D1–D30 locked or explicitly deferred; `API_CONTRACT.md` frozen; repo initialized with secrets exclusion and judge access configured |
| **2. Fire TV foundation** | Every screen fully D-pad traversable with visible, never-lost focus; nothing in the outer 5%; body text ≥14sp; Back predictable everywhere incl. mid-session; provenance impossible to omit at the data layer |
| **3. ASSIST** | Document → extraction → proposal with source reference → **confirmation against the rendered original document** → confirmed instruction on device → Today care task → completion. All five instruction types render with source + date. Dose text verbatim, mechanically checked |
| **4. GUIDE** | Preset/goal request → catalog-constrained generation → **deterministic validation passes** → preview with explicit total → hands-free guided session → recorded completion. Precautions surfaced before a session. Preset fallback works |
| **5. PROGRESS** | Every completion recorded and visible; streak accurate; partial sessions honest; Daily Summary renders four visibly separated regions |
| **6. AI CORE** | Two physically separate regimes; guardrail is a mandatory stage that **fails closed**; strict schemas with bounded retry; every §D24 fallback implemented and rehearsed; `AIRequestLog` contains no clinical content |
| **7. Companion** | Pairing code → upload → document appears on TV. Displays no health information. No clinical route exists |
| **8. Safety/privacy** | All `SC-20`–`SC-28` and `SC-30`–`SC-35` verified at **zero**, each with a test that fails if the boundary breaks; secret scan clean; verbose + AI logging off; `PRIV-1622` terms verification recorded; first-run acknowledgement present |
| **9. Testing** | Guardrail, day engine, session engine, routine validation, provenance invariant and schema tests pass; manual TV checklist complete; full demo rehearsed **offline**; both journeys complete with no voice and no typing |
| **10. Submission** | Repo complete with README + testing instructions + licence; access verified; video <3 min publicly visible showing device/simulator footage and **both** journeys; description written; **Product Feedback written**; friction log submitted; all `HACK-` items re-verified; submitted before 2026-10-23 12:00 PT |

---

## 17. Risk Register

| Risk | Prob. | Impact | Detection | Mitigation | Fallback | Owner | Deadline |
|---|---|---|---|---|---|---|---|
| **No runnable Fire TV target** | Med | **Fatal** | **P1** | D30 preference order; resolve Day 1 | Buy a Fire TV Stick — order Day 1 | A + Owner | **Day 1** |
| **Emulator footage may not satisfy `HACK-806a`** | Med | **Fatal** | Rules re-read | **[VERIFY BEFORE SUBMISSION]**; prefer physical hardware | Physical device | Owner | Day 2 |
| Framework wrong for the team (D2) | Med | High | **P2** + 1.5-day trigger | Reversal trigger defined; D16 insulates the key feature | RN TV official sample | A | **Day 2** |
| D-pad/focus quality below judge standard | Med | High (25% Design) | **P2** + checklist each gate | `design/` token module; continuous traversal testing | Simplify layouts to single-axis | A | Day 8 |
| Malformed AI output | Med | High | **P5** metrics | D11 strict schema + retry + fail closed | Narrow schema; stronger model; per-op fallbacks | B | **Day 4** |
| **Dose string altered by AI** | Low | **Critical** | **P5** verbatim check | Deterministic substring check rejects non-verbatim dose | Reject proposal → `UNCLEAR` | B | **Day 4** |
| bbox↔pixel misalignment breaks D16 | Med | **Critical** | **P4** | Server-rendered highlight; crop+zoom | Client `PdfRenderer` overlay; escalate if both fail | B | **Day 3** |
| Document extraction consumes the schedule | Med | High | Day 8 gate | D7 removes OCR entirely; we author the PDFs | Reduce to 4 documents | B | Day 8 |
| AI latency degrades the TV experience | Med | Med | P5 p95 | D9 job+poll; D10 pre-generate + cache | Determinate loading with timeout | B | Day 12 |
| Session runtime stutter / screen sleep | Med | High | **P3** | Validate early; minimal animation | Static text + numeric countdown | A | **Day 3** |
| Offline path untested; demo dies on wifi | Med | **Fatal to demo** | Day 24 offline rehearsal | Tier 0 fully local by design (D20) | Pre-ingest documents before recording | Both | Day 24 |
| Backend unavailable on demo day | Low | High | `/v1/health` | Deploy Day 12; Tier 0 needs no network | Record with pre-ingested data | B | Day 12 |
| Safety validation gap ships | Low | **Critical** | Guardrail tests | D14 mandatory stage; `SC-20`–`SC-28` tests | Block the feature, not the test | B | Day 22 |
| Prompt injection via document (`S2`) | Low | Med now / High later | Adversarial test Day 21 | Document text as data only; gate + D16 terminal | Reject document; flag `UNCLEAR` | B | Day 21 |
| PHI in logs or prompt logging left on | Med | High | Day 22 audit | `PRIV-1652` rules; off by default | Strip and re-audit | B | Day 22 |
| Secret committed | Low | High | Day 1 exclusion + scan | First-commit exclusion; scan Day 22 + 26 | Rotate key; rewrite history | B | Day 26 |
| Companion pairing fails on camera | Low | Med | Day 13 | Long-lived demo code | Bundled documents are the demo path | B | Day 13 |
| **Scope drift to fitness-only** | Med | **High** | Weekly: both journeys still in the demo? | Care built first (Phase 2 before 3); beat 4 = 48s | Cut wellness polish, never the care spine | Both | Weekly |
| Submission mechanics missed | Med | **Fatal** | Day 21 dry run | Full dry-run submission Day 21; docs from Day 1 | Day 26 buffer | Both | Day 21 |
| Video >3 min or wrong footage | Med | High | Day 24 timing | §13 allocation; rehearse to time | Cut beat 5 (10s) first | Both | Day 25 |
| Copyrighted audio in video | Low | Med-High | Pre-upload check | Silence or original audio only | Re-cut audio | Both | Day 25 |
| Eligibility failure | Low | **Fatal** | Owner check | Confirm against official rules | None — must be Day 1 | Owner | **Day 1** |
| `PRIV-1622` provider terms disallow clinical text | Low | Med | Day 22 verification | Synthetic data only regardless | Swap provider via `LlmClient` | B | Day 22 |

---

## ARCHITECTURE LOCK

Locked. Changing any of these requires explicit owner approval.

1. **D1** Fire OS (Android). Vega OS = post-hackathon port target.
2. **D2** Kotlin + Jetpack Compose for TV — **with the Day-2 reversal trigger to RN TV**.
3. **D3** `minSdk` 29, `targetSdk` 34.
4. **D4/D5** One narrow Python/FastAPI backend + SQLite, serving API and companion page.
5. **D6** Two stores split on the confirmation boundary: proposals server-side, **confirmed clinical data device-canonical**.
6. **D7/D15** Text-layer synthetic PDFs; server-side text + bbox extraction; **no OCR in MVP**.
7. **D8** Claude behind an `LlmClient` abstraction; task-appropriate models.
8. **D9** Sync for short ops; job+poll for extraction.
9. **D10** Pre-generate AI-derived text at confirmation; care path fully offline.
10. **D11** Strict schema, bounded retry (2), fail closed. Plus a deterministic verbatim-dose substring check.
11. **D12** ASSIST is transform-only; output is always a proposal.
12. **D13/D17** GUIDE emits **catalog IDs only**; versioned catalog in `shared/`, bundled into both runtimes.
13. **D14** Guardrail is a mandatory server-side stage that fails closed, readable independently of prompts.
14. **D16** Confirmation happens against a **server-rendered original document region with the source highlighted**.
15. **D18/D19** Day/Plan and Session engines are deterministic, device-side, AI-free.
16. **D20** Three-tier offline model; Tier 0 covers the whole care path.
17. **D21/D22** Companion = upload + awkward text entry only, via pairing code. Never displays health information.
18. **D23** Small REST/JSON API, frozen Day 3.
19. **D24** Every AI operation has a named deterministic fallback.
20. **D25/D26** No client credentials; no clinical content or prompt bodies in logs.
21. **D27** Two synthetic personas, 6–7 authored synthetic documents, labelled at data layer and in UI.
22. **D28** Hosted HTTPS backend by Day 12; sideloaded APK; no Appstore submission.
23. **D29** Safety-weighted test suite + manual TV checklist.
24. **D30** Target resolved Day 1 as a project-blocking gate.
25. **Conflict resolutions 0.1–0.7** as written — including that `SAFE-915` is **not** weakened and `OQ-13` is withdrawn.

## STILL OPEN

Only what genuinely cannot be decided yet.

1. **Which Fire TV target is actually available** — device, emulator, or purchase (**P1**, Day 1). Everything else is downstream.
2. **Whether an Android TV emulator satisfies `HACK-806a`** — **[VERIFY BEFORE SUBMISSION]**. If any doubt, use hardware.
3. **D2 final confirmation** — pending team Kotlin/Compose familiarity and the P2 outcome (Day 2).
4. **Exact AI models per operation** — pending P5 latency and accuracy measurements (Day 4).
5. **Routine duration tolerance** (`OQ-21`) — pending catalog authoring (Day 6).
6. **Recency window per measure type** (`OQ-20`) — pending Health Info build (Day 10).
7. **`PRIV-1622` provider-terms confirmation** — **[VERIFY]** before any non-synthetic content, recorded by Day 22.
8. **Whether publishing this repo satisfies the Open Source mini challenge** — **[VERIFY]**, worth one clarification.
9. **Owner eligibility** (`OQ-11`) — owner action, Day 1.
10. **Hosting provider for D28** — deliberately deferred; any small HTTPS host qualifies.

## FIRST 48 HOURS

In order.

**Hour 0–1 — Owner, before any code**
1. Confirm hackathon eligibility against the official rules (`OQ-11`).
2. Answer: is a physical Fire TV device available? If not, order a Fire TV Stick **today** — shipping is the long pole.
3. Confirm both developers' Kotlin/Compose familiarity (this decides the D2 reversal).
4. Approve this document, or state objections.

**Hour 1–8 — Day 1**
5. **Developer A: P1.** Hello-world on the best available target. Screenshot + short recording. **This is the gate.**
6. **Developer B:** repo init; `.gitignore` + secrets exclusion in the **first** commit; OSS licence; configure judge access now; start `FRICTION_LOG.md` and `PRODUCT_FEEDBACK.md`.
7. **Developer B:** author the first two synthetic PDFs (prescription + exercise handout).
8. **End of Day 1:** if P1 failed, escalate to the owner the same day. Do not proceed to Phase 1.

**Hour 8–16 — Day 2**
9. **Developer A: P2** focus/safe-zone. **Decide the D2 reversal by end of day.**
10. **Developer B: P4 begins** — PDF text + bbox extraction, page rasterize, highlight draw.
11. Both: draft `API_CONTRACT.md`.

**Hour 16–24 — Day 3**
12. **Developer A: P3** timed session with screen-on.
13. **Developer B: P4 completes.**
14. Both: **freeze `API_CONTRACT.md`.** Parallel work begins.
15. **Developer B: P5 begins.**

**Hour 24–48 — Day 4**
16. **Developer B: P5 completes** — including the verbatim-dose substring check.
17. **Developer A:** navigation shell, Profile Select, Back semantics.
18. Both: review P1–P5 outcomes against the Phase 0 gate. Confirm or adjust the plan. Then Phase 1.

## FIRST CODING PROMPT

To be given to the coding agent **only after this document is approved**. It implements
**P1 and P2 only** — not the product.

> Implement **P1 and P2 only** from `ARCHITECTURE_MVP_PLAN.md` §12. Do not build any product
> feature, screen, data model, or backend code. Do not add dependencies beyond what these two
> POCs require.
>
> **Context.** New project, empty repo. Target is Fire OS (Android-based) per decision **D1**;
> framework is Kotlin + Jetpack Compose for TV per **D2**, `minSdk` 29 / `targetSdk` 34 per
> **D3**. Host machine is Windows 11. There may be no physical Fire TV device — check first
> and report what target is available before writing code.
>
> **Step 1 — repository hygiene, first commit.** Initialize the repo with a `.gitignore`
> covering Android/Gradle build output and any environment files, plus a secrets-exclusion
> configuration. No credentials of any kind, ever (**D25**, `PRIV-1640`/`PRIV-1641`).
>
> **Step 2 — P1, Fire TV Hello World.** A minimal Compose for TV app, one screen, one text
> label. Install and launch it on the best available target in this order: physical Fire TV
> device → Android TV emulator image at 1080p → report that neither is available and stop.
> Report exactly which target was used, and capture a screenshot.
>
> **Step 3 — P2, D-pad / focus / safe-zone validation.** One screen containing at least six
> focusable cards arranged so that both horizontal and vertical D-pad movement are exercised.
> Requirements: every card reachable by D-pad (`HACK-414`); focus clearly visible via scale
> **plus** border **plus** background change — never colour alone (`HACK-413`, `PROD-435`);
> focus never lost after any state change (`PROD-440`); a toggleable 5% safe-zone overlay to
> verify nothing sits in the outer 5% (`HACK-410`); and two text samples side by side — one at
> exactly 14sp (`HACK-411`) and one at the intended primary card size — so the floor and the
> target can be compared at distance.
>
> **Step 4 — report, do not proceed.** Report: which target ran; P1 and P2 success criteria
> pass/fail against §12; how long each took; whether the **D2 1.5-day reversal trigger** was
> hit; any friction encountered, appended to `docs/FRICTION_LOG.md` (`HACK-826`). Then
> **stop** and wait for approval before Phase 1.
>
> Do not implement the day engine, session runtime, document pipeline, AI, or any product
> screen. Do not create the backend.

---

*End of architecture and execution plan. `PROJECT_MASTER_SPEC.md` and `PROJECT_REVIEW.md`
were not modified. No source code, scaffolding or dependencies were created.*

