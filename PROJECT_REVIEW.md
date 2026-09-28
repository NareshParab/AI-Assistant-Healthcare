# Project Master Spec Review

**Reviewing:** `PROJECT_MASTER_SPEC.md` v1.0.0 (3,321 lines), read in full
**Review date:** 2026-09-27
**Reviewer role:** Senior Product Architect + Technical Planning Lead
**Status:** Planning review — no code, no scaffolding, no stack selection
**Submission deadline:** 2026-10-23, 12:00 pm PT — **~26 days remaining**

`PROJECT_MASTER_SPEC.md` was **not modified** by this review.

**A note on independence:** this review was produced by the same agent that wrote the
specification. To compensate, it was conducted adversarially — hunting for internal
conflicts, unimplementable requirements, and scope inflation rather than confirming the
document. Four genuine internal conflicts and two material safety gaps are identified
below. Where the spec is wrong, this review says so.

---

## 1. Executive Assessment

**The product direction is coherent and the concept is genuinely differentiated. The MVP as
currently scoped is not buildable in 26 days. Four internal conflicts must be resolved
before any code is written, and the central safety mechanism has a design hole that
defeats its own purpose.**

### What this product actually is

A Fire TV companion with two halves that share one loop: a **care companion** that turns
doctor-provided documents into a dated, source-attributed daily routine, and a **wellness
companion** that turns a stated time budget into a guided session. The spec holds both
without collapsing into either — which was the main risk and is handled well.

The differentiator is not the feature list. It is the **trust architecture**: a mandatory
human confirmation gate between AI extraction and the user's plan, provenance on every
health value, and a two-regime AI model where the clinical side may only *transform*
existing information and never originate it. That is a defensible, distinctive engineering
claim, and it maps directly onto the hackathon's Tech Implementation and Quality of Idea
criteria. It should be protected at the cost of almost anything else.

### The three problems

**Problem 1 — scope.** Section 30.2 lists approximately **47 feature IDs across 10+
screens**, including a document pipeline, an extraction-and-review flow, a guided session
runtime, a four-region summary generator, and a code-level guardrail layer. That is a
multi-month scope. At 26 days, on a platform that has not been chosen yet, this is
over-scoped by roughly **2–3×**. The spec's own mitigations (`PROD-1903`, `PROD-1910`,
`DP-04`) are correct in principle but are not operationalized — there is no ranked spine
that says what must work versus what may be cut under pressure. Section 3 of this review
supplies one.

**Problem 2 — four internal conflicts.** These are not nitpicks; each will cause rework if
discovered during implementation:

| # | Conflict | Severity |
|---|---|---|
| **C1** | `PROD-2111` ("MUST NOT show functionality that does not exist") directly contradicts `OQ-13` (pre-processing synthetic documents is acceptable). One forbids demo theater; the other permits it. | **High** |
| **C2** | `F-A10`/`PROD-730` promise a "plain-language explanation" of medication instructions, but `SAFE-915` restricts the operation to "linguistic simplification only" with no general medical knowledge. For a terse prescription line there is nothing to simplify — the feature promises value it is forbidden to deliver. | **High** |
| **C3** | `TECH-930` requires the core care path to work offline, but MVP care features `F-A10` (explanation) and `F-P04` (summary) are AI-dependent. Whether these are "core care path" is undefined. | **Medium-high** |
| **C4** | A four-way squeeze rather than a contradiction: `PROD-100` (5-second glance) + `PROD-510` (no scrolling for the Now/Next/Overdue tier) + `PROD-552` (source and date on every card *at card level*) + `HACK-415` (low information density). Provenance metadata adds visual weight to exactly the surface that must stay sparse. The spec asserts all four without resolving the tension. | **Medium** |

**Problem 3 — the confirmation gate has a hole.** This is the most important finding in
this review. `PROD-621` and `SAFE-1522` require the review screen to show "the proposed
structured item beside **the source text** it came from." But if extraction misread the
document, the extracted source text is *also* wrong. The reviewer would be comparing the
model's output against the model's own transcription — validating nothing. The gate that
the entire safety architecture rests on can be passed by a confidently wrong extraction.
See §6.

### What is not wrong

Both use cases are preserved and neither dominates. Fire TV remains primary. The safety
boundaries are unusually thorough — 19 prohibitions, 10 obligations, and a separation
invariant (`SAFE-940`) that is genuinely architecturally load-bearing. The hackathon
requirements are verified against primary sources with citations, and §33.7's list of
restrictions *checked and found not to exist* is exactly the right discipline.

### Bottom line

Do not start coding. Resolve `OQ-01` (platform), fix the confirmation-gate hole, resolve
C1–C3, and adopt a ranked demo spine. Those four things are about two days of decisions
and will save a week of rework. Then build.

---

## 2. What Is Strong

**1. The two-regime AI model (§17.1) is the best idea in the document.** Splitting AI into
an ASSIST regime that may only *transform* confirmed information and a GUIDE regime that
may *generate* within a safety envelope is a clean, enforceable boundary. Most health-AI
projects have a single undifferentiated model and rely on prompt wording. This one is
structural.

**2. `SAFE-940` — the four-class separation invariant.** Requiring that confirmed clinical,
self-reported, AI-generated and demo data never merge, with **no code path** promoting
AI-generated to confirmed (`SAFE-1800`), is the kind of invariant that can be tested. It is
correctly identified as the requirement that should cause an architecture to be rejected
(`SAFE-941`).

**3. The confirmation gate as a product concept (`SAFE-501`).** Making human confirmation
mandatory before anything reaches the plan is the right answer to "AI reads medical
documents." It converts the hardest safety problem into a UX problem. *The concept is
strong; the specified implementation is flawed — see §6.*

**4. Provenance as a first-class data requirement (`SAFE-970`).** Ten provenance fields on
every health datum, with `SAFE-521` making missing provenance a *blocking* error rather
than cosmetic, and `TECH-902` pushing enforcement to the data layer. Retrofitting this
would be very expensive; specifying it up front is correct.

**5. `SAFE-504` — dose text preserved as transcribed.** Prohibiting recomputation, unit
conversion, splitting, combining, rounding and normalizing of dose strings closes the
single highest-harm failure mode in the product with one rule.

**6. Refusing to invent hackathon restrictions (§33.7).** Nine restrictions were checked
and explicitly documented as *not existing* — including that Appstore publication is not
required and that the official simulator is acceptable for the demo video. This prevents
future work from self-imposing constraints, and it is unusually disciplined.

**7. Honest handling of the voice limitation (`TECH-450`, `PROD-451`).** Rather than
assuming a capability, the spec decouples request understanding from input channel and
makes the non-voice path mandatory. This review's new research (§5) shows that instinct
was correct and the limitation is harder than the spec assumed.

**8. Honest regulatory posture (`PRIV-1660`).** Explicitly claiming no HIPAA/GDPR/FDA
compliance, and prohibiting compliance badges (`PRIV-1662`), is the correct and rare
choice.

**9. `TECH-460` / `SAFE-1100` — reminder honesty.** Recognizing that a TV cannot reliably
alert a user, and forbidding the claim, avoids the most dangerous over-promise a health TV
app could make.

**10. Section 5.3 treats accessibility as a baseline constraint, not an accommodation.**
Given that the care persona is post-stroke, designing for reduced reading endurance and
fine motor control as *defaults* is the right framing and will improve the Design score.

**11. Requirement IDs throughout.** Stable, prefixed, cross-referenced IDs make the
document actually usable by an implementation agent — which was a stated goal and is met.

---

## 3. MVP Scope Review

The spec's §30.2 MVP is too large. This section re-ranks it **without deleting anything
from the product vision** — everything demoted lands in P2 with its role intact, per
`RULE-003` and `PROD-1902`.

The organizing principle: **define a Demo Spine that must work end-to-end, because the
demo *is* the submission (`HACK-806`).** Anything not on the spine is negotiable under
time pressure.

### MUST HAVE — the Demo Spine

Non-negotiable. If any of these fails, there is no submission.

| Item | Spec ID | Why it is on the spine |
|---|---|---|
| Profile Select with 2 seeded profiles | `F-X01`, `F-X02` | Entry point and the shared-TV privacy story. Also the cheapest screen. |
| Today with Now / Next / Done (Care) | §14.2 | The single most important screen in the product. `PROD-100` is the product's core claim. |
| Item Detail + mark taken/skipped | §14.3, `F-A11` | Closes the loop; without it nothing is recorded. |
| Care Plan read view (all 5 item types) | `F-A04`–`F-A08` | Proves the care use case is real and not a single hardcoded card. |
| Health Info with full provenance | `F-A09` | Where provenance is most visible; carries `SAFE-520`. |
| **Document Review & Confirm** | `F-A03`, `SAFE-501` | **The trust moment. The most distinctive thing in the product. Must be real and must be demonstrated live.** |
| Document text extraction → proposals | `F-A02` | The gate is meaningless without something real to confirm. See scope note below. |
| Wellness: presets → routine → preview | `F-G02`, `F-G03`, `F-G04` | The wellness use case entry. Must be the non-voice path (`PROD-403`). |
| Guided Session Player | `F-G05`, `F-G06` | The wellness payoff, and the most TV-native moment in the product. |
| Progress + streak | `F-P01`, `F-P02`, `F-P03` | Closes the loop visibly. |
| Daily Summary with 4 regions | `F-P04`, `SAFE-1410` | Demonstrates the fact/interpretation separation — a judging asset. |
| **Guardrail layer** | `F-AI08`, `SAFE-920` | **Ships with the first AI feature. Not deferrable (`DP-05`).** |
| Routine generation within envelope | `F-AI04`, `SAFE-917` | The AI moment on the wellness side. See §6 for a required change. |
| 10-ft UI baseline | `F-X05`, §12 | 25% of judging is Design. Not optional. |
| Demo data labelling | `F-X07`, `PRIV-981` | Cheap; required by `HACK-980`. |
| In-app due/overdue surfacing | `F-X09` | Makes Today dynamic rather than static. |

**Critical scope reduction on `F-A02` (recommended):** use **digitally generated,
text-layer synthetic PDFs** for the MVP rather than scanned images. Extraction then becomes
*text parsing plus LLM structuring* with **no OCR at all**. This is not a cheat — the
pipeline is genuinely real, end to end, on genuinely real documents. It removes the single
largest time sink and the single largest reliability risk from the critical path, and OCR
on scanned images moves cleanly to P2.

**This one decision also resolves conflict C1 and closes the §6 safety hole**, because a
text-layer PDF lets the review screen render the actual document page with the source span
highlighted — real verifiable provenance, not a re-display of the model's own
transcription. It is the highest-leverage decision in this review.

### SHOULD HAVE — cheap, high narrative value, cut only if forced

| Item | Spec ID | Reasoning |
|---|---|---|
| Precaution gating before a session | `F-G09`, `SAFE-032` | Very cheap (one interstitial screen) and it is the clearest visual proof that the care and wellness halves are genuinely integrated rather than two apps in a trench coat. High judging value per hour spent. |
| Optional profile PIN | `F-X03`, `PRIV-701` | One numeric-entry screen. Distinctive privacy story that most TV apps ignore. Keep it minimal; do **not** build lockout policies. |
| Care-team / emergency info card | `F-A13` | Near-zero cost, display-only, reinforces the safety posture. |
| Out-of-scope refusal moment | narrowed `F-AI07` | Needed for demo item 5 (`PROD-2101`). See the P2 note below — build the *refusal*, not a Q&A surface. |
| Basic preference memory | `F-G10` | Cheap if it is a stored list of avoided movements. Do not build a learning system. |
| "What this says" view | reframed `F-A10` | See C2 in §6. Reframed, it is cheap and honest. As specified, it is a trap. |

### MOVE TO P2 / FUTURE

Preserved in the vision, removed from the 26-day window. Each carries its intended role
forward per `RULE-003`.

| Item | Spec ID | Why it moves | Role preserved in |
|---|---|---|---|
| New-document change handling | `F-A12`, Journey 6 | An entire second flow (side-by-side conflict resolution) that appears nowhere in the demo. Roughly a week of work for zero submission value. | `FUT-1209` |
| Recorded-information comparison | `F-P06` | `SAFE-1311` and `SAFE-1312` constrain it so tightly — no characterization, no ranges, no in/out-of-range — that the surviving user value is close to zero, while the safety risk of getting it wrong is high. **Pure risk, negligible payoff.** | `FUT-1206` scope |
| General bounded Q&A | `F-AI07` (full) | A conversational surface is the riskiest AI feature in the product and the least necessary for the demo. Narrow it to *refusing an out-of-scope clinical request on the existing wellness-request surface*, which satisfies `PROD-2101` item 5 at a fraction of the cost. | `F-AI07` re-scoped |
| Live document intake mechanism | `F-A01` transfer path | `TECH-905`'s transfer options (local network, companion upload) are all multi-day builds. Bundle the synthetic PDFs as app assets. The *pipeline* stays real; only the *transfer* is seeded — and `PROD-2101` item 2 never required showing an upload. | `TECH-905`, `FUT-1200` |
| Full NL intent understanding | `F-AI01` (broad) | Narrow to parsing a wellness request (time, goal, preference). A general intent router across navigation, completion and Q&A is scope the demo does not use. | `F-AI01` re-scoped |
| Idle timeout on care surfaces | `PRIV-1701`, `TECH-1702` | Real privacy value, but invisible in a 3-minute demo and fiddly to get right. | `FUT-1710` area |
| Caregiver as a distinct on-TV role | `F-A14` distinct role | `OQ-14` already leans this way. Single profile-level actor for MVP. | `FUT-1200` |
| Third "Both" persona | `OQ-12` | Two personas (Care, Wellness) serve the demo. Journey 4 stays specified for later. | `OQ-12` default |
| OCR on scanned images | part of `F-A02` | Displaced by the text-layer PDF decision above. | `FUT-1403` |

### HIGH-RISK / VALIDATE FIRST

These must be proven before being committed to. Each has a proposed proof-of-concept in §9.

| Item | Why it is high-risk |
|---|---|
| **Platform target (`OQ-01`)** | Unresolved, and it gates every other technical decision. Vega tooling does not run on Windows. Blocks everything. |
| **Document text extraction without Google Play Services** | **New finding (§5):** Play Services are officially unavailable on Fire TV, which eliminates ML Kit on-device text recognition — a default choice. The whole extraction approach depends on this. |
| **Structured output reliability from the AI** | The entire extraction and routine pipeline assumes reliable schema-conformant output. If the model returns malformed JSON 5% of the time, the guardrail correctly fails closed and the demo breaks. Needs measurement, not assumption. |
| **Session Player timing on low-power hardware** | Fire TV Sticks are modest devices. Smooth countdowns, transitions and a screen that stays awake for 15 minutes are all unvalidated. |
| **Simulator availability on the Windows host** | `OQ-02`. If neither a device nor a usable simulator exists, `HACK-806a` cannot be satisfied and there is no submission. **This is the single highest-severity unknown.** |
| **`SAFE-917` deterministic routine validation** | As specified, not implementable against free-text AI output. Requires the design change in §6. |

### Is the MVP realistically buildable in 26 days?

**As written in §30.2: no.** With the Demo Spine above, the text-layer-PDF decision, and the
P2 demotions: **yes, but it is tight and assumes the platform decision lands within 48
hours.** The spine is roughly 12 screens and one AI pipeline, which is achievable. The
§30.2 list is not.

The binding constraint is not feature count — it is that **~5 of the 26 days must be
reserved for demo recording, repository preparation, and the required submission fields**
(`HACK-805`–`HACK-810`), which are frequently underestimated and are individually
submission-blocking (`R-19`).

---

## 4. Architecture Decisions Required

| Decision | Options | Recommendation | Tradeoff | Decide Before Coding? |
|---|---|---|---|---|
| **D1. Target OS** | (a) Fire OS (Android-based); (b) Vega OS | **Fire OS.** Vega tooling requires macOS 10.15+/Ubuntu 20.04+ and the host is Windows 11; Vega also runs on only two shipping devices (Fire TV Stick HD 2026, Fire TV Stick 4K Select 2025). Both satisfy `HACK-800`. | Vega is the forward-looking platform and may read as more innovative to judges; Fire OS is lower-risk, Windows-compatible, and covers far more devices. | **YES — blocks everything** |
| **D2. Runtime / framework** | (a) Native Android (Kotlin + Compose for TV); (b) React Native for TV; (c) Web app in a WebView | **Kotlin + Compose for TV** if D1 = Fire OS. `HACK-801` constrains nothing. Compose for TV gives first-class D-pad focus handling, which is 25% of judging. | RN offers cross-TV reuse and faster iteration for web-familiar developers, but focus management on TV is historically where RN TV projects lose Design points. Native is more verbose. | **YES** |
| **D3. Min SDK / Fire OS floor** | Fire OS 8 (API 29/30) vs Fire OS 14 (API 31–34) vs Fire OS 16 (API 35/36) | **Target the Fire OS 8 floor (API 29/30)** — current 2025–26 devices split across Fire OS 8 and 14, so an API 29 floor maximizes device reach without cost. | A higher floor unlocks newer APIs but narrows the device set and the simulator/device you may actually have. | **YES** |
| **D4. Backend: any, or none** | (a) Fully on-device; (b) Thin proxy for AI only; (c) Full backend | **(b) Thin proxy for AI only.** `PRIV-1640` forbids keys in the client, which rules out (a) if a cloud AI is used. A minimal proxy is hours of work; a full backend is days. | (a) is simplest and most private but cannot hold an API key; (c) adds auth, hosting, deployment and latency to a 26-day build for no demo benefit. | **YES** |
| **D5. Clinical data location** | (a) On-device only; (b) Server-side | **(a) On-device only.** Strongest `PRIV-1610`/`PRIV-1611` posture, no auth requirement (`PRIV-1630`), no sync complexity, and `TECH-930` offline-first becomes nearly free. | Forecloses the caregiver companion (`FUT-1200`) until P2 — which is already P2. No real cost. | **YES** |
| **D6. Local storage mechanism** | Structured local DB vs files vs preferences | **Structured local DB.** `SAFE-940`/`SAFE-1801`–`1809` require enforceable invariants and a real `ExtractedProposal` / `CarePlanItem` separation. Files and preferences cannot express these. | Slightly more setup than serializing JSON; far cheaper than discovering mid-build that provenance cannot be enforced. | **YES** |
| **D7. Document format for MVP** | (a) Text-layer synthetic PDFs; (b) Scanned images + OCR; (c) Plain text/JSON fixtures | **(a) Text-layer PDFs.** Keeps the pipeline genuinely real, removes OCR from the critical path, and — critically — enables showing the real document page with the source span highlighted, which closes the §6 safety hole and resolves conflict C1. | (b) is more impressive if it works and a catastrophic time sink if it does not. (c) is the safest but makes the pipeline demo theater, violating `PROD-2111`. | **YES** |
| **D8. OCR approach (P2, but decide the constraint now)** | Cloud OCR over HTTPS; a bundled native OCR library; **not** ML Kit | **Defer to P2, but record that ML Kit / Play-Services-dependent OCR is unavailable on Fire TV.** | Cloud OCR sends clinical content off-device, engaging `PRIV-1622`. Bundled native OCR is large and less accurate. | No — but record the constraint |
| **D9. AI provider** | Cloud LLM via proxy; on-device small model | **Cloud LLM via the D4 proxy.** On-device inference on a Fire TV Stick is not realistic for the extraction and summarization quality required. | Network dependency (mitigated by D10) and `PRIV-1622` disclosure/terms review. Must exclude any provider whose terms permit training on submitted content. | **YES** |
| **D10. Offline strategy for AI-dependent care features** | (a) Pre-generate and cache at confirmation time; (b) Require network; (c) Degrade to raw source text | **(a) Pre-generate at confirmation time.** Generate the plain-language view and cache it when the human confirms the item. The care path is then genuinely offline, and this **resolves conflict C3**. | Slight extra work at confirmation; eliminates a whole class of demo-day network failures. | **YES** |
| **D11. Structured AI output contract** | Free-form text parsed leniently; strict schema with validation and retry | **Strict schema + validation + bounded retry + fail-closed.** `SAFE-920` demands fail-closed, and `SAFE-917` is unimplementable without a schema. | Strictness causes more refusals, which is the correct direction for a health product. | **YES** |
| **D12. Wellness movement content model** | (a) AI generates movements as free text; (b) **AI selects and sequences from a curated, pre-vetted movement library** | **(b) Curated library.** This is the key change that makes `SAFE-917` deterministic validation actually possible, and it is *faster* to build than (a). Preserves the product intent — AI still generates and personalizes the *routine*. | Less variety than open generation. For a 26-day MVP with a safety obligation, this is a clear win. | **YES** |
| **D13. Voice input** | Build it; skip it for MVP | **Skip for MVP; keep the input-channel abstraction (`PROD-451`).** §5 shows Fire TV does not support the Android speech recognizer and has no Play Services. | Loses a flashy demo beat. `PROD-403`/`PROD-2102` already require the non-voice path to be complete, so nothing in the product breaks. | **YES** |
| **D14. Reminder strategy** | In-app surfacing only; system notifications | **In-app only**, exactly as `F-X09`/§21 specify. `F-X10` stays feasibility-gated P2. | No out-of-app prompting — but `SAFE-1100` already forbids claiming it. | Already decided in spec |
| **D15. Profile / auth model** | Local profiles + optional PIN; real authentication | **Local profiles + optional PIN.** Correct for D5 = on-device. Real auth becomes mandatory only if a server holds health data (`PRIV-1630`). | Not portable across devices — a P2 concern. | Already decided in spec |
| **D16. Day / plan engine** | Deterministic; AI-driven | **Deterministic**, per `TECH-906`. AI must not be in the path that decides what is on a care plan today. | None. This is correct and should not be revisited. | Already decided in spec |
| **D17. Keeping the screen awake during sessions** | Platform flag; periodic input simulation | **Platform screen-on flag** — but verify on the chosen target (§5, NEEDS POC). | If unavailable, a 15-minute guided session is broken by screen timeout. | **YES — validate early** |
| **D18. Deployment / distribution for judging** | Sideload to device; simulator run; Appstore submission | **Sideload / simulator run + repository instructions.** Appstore publication is **not** required (`HACK-805`, §33.7). | None. | No |

**Decisions that must NOT be made yet:** anything in §29.5 beyond the above. In particular,
do not select specific libraries, styling approaches or state management until D1 and D2
land, since both are downstream of the platform choice.

---

## 5. Fire TV Technical Risk Review

New research was performed for this review. Findings are labelled by evidentiary status.

### CONFIRMED (official Amazon documentation)

| # | Finding | Source | Implication |
|---|---|---|---|
| **F1** | **Google Play Services are not available on Fire TV.** *"Any APIs that rely on Google-specific services, such as Google location services, aren't available on Amazon Fire TV."* and *"Some Firebase SDKs depend on Google Play services, which are not available on Amazon devices."* | Fire TV: How Fire TV Development Differs from Android TV | **Major.** Eliminates Firebase (auth, Firestore, Crashlytics), **ML Kit on-device text recognition**, and any Play-Services-dependent library. Directly constrains D8 and any auth/analytics choice. |
| **F2** | **Fire TV does not support the Android speech recognizer used by Leanback's `SearchFragment`.** *"Leanback's SearchFragment … is not supported."* Voice search *"initiates a global search using the Alexa cloud service instead [of] speech recognition APIs."* Official guidance is to disable it or the app *"will potentially return errors."* | Fire TV: Differences from Android TV Development; Voice-enabling overview | **Upgrades `TECH-450` from "not found in docs" to "officially unsupported."** Free-form voice input is effectively closed on Fire OS. Confirms D13. |
| **F3** | Fire OS ↔ Android API mapping: Fire OS 16 → API 36/35; Fire OS 14 → API 34/33/32/31; Fire OS 8 → API 29/30; Fire OS 7 → API 28; Fire OS 6 → API 25; Fire OS 5 → API 22. | Fire OS Overview | Sets D3. Current 2025–26 devices split across **Fire OS 8 and Fire OS 14**. |
| **F4** | **Vega OS 1.1 ships on exactly two devices:** Fire TV Stick HD (2026) and Fire TV Stick 4K Select (2025). Vega does **not** run Android APKs. | Fire OS Overview; Vega OS blog | Narrow device reach for Vega. Reinforces D1 = Fire OS. |
| **F5** | **Vega developer tooling requires macOS 10.15+ or Ubuntu 20.04+. Windows and WSL are not supported.** | Install the Vega Developer Tools | Decisive for D1 given a Windows 11 host. |
| **F6** | Safe zone: avoid the outer **5%** of every edge; content within the inner **90%**. Body text **≥14sp** (~19px at 720p, 28px at 1080p). 1080p = 1920×1080px, 320dpi, 960×540dp. | Fire TV Design Guidelines; Display and Layout | Hard layout constraints. Already in spec as `HACK-410`–`HACK-412`. |
| **F7** | Every actionable element must be D-pad reachable; focus must be clearly indicated. Prefer less saturated, cool colours; low information density. | Fire TV Design Guidelines | Already `HACK-413`–`HACK-415`. Note F7 constrains health status colour-coding — `PROD-435` is the right response. |
| **F8** | Fire TV supports the **VoiceView** screen reader; content descriptions required for icons and custom controls. Use `sp` for text, `dp` for layout. | Accessibility on Amazon Fire Devices | Already `HACK-416`, `HACK-417`. |
| **F9** | The demo video may show the app on **a real Fire TV device *or* the official Fire TV / Vega simulator**. | Devpost official rules | Removes hardware as an absolute blocker — *if* a simulator runs on the host (see A1). |

### ASSUMPTION (plausible, currently unverified, would be costly if wrong)

| # | Assumption | Risk if wrong |
|---|---|---|
| **A1** | An official Fire TV emulator/simulator for the chosen target runs acceptably on Windows 11. | **Severe.** With no device and no simulator, `HACK-806a` cannot be met and there is no valid submission. **Validate first, before anything else.** |
| **A2** | A Fire TV Stick-class device can render the Session Player's timers and transitions smoothly. | Medium-high. The most visually prominent demo moment would stutter, directly hitting the Design criterion. |
| **A3** | A platform flag can hold the screen awake for a 15-minute guided session. | High. Without it the session dies mid-demo. See D17. |
| **A4** | Rendering a PDF page with a highlighted text span is feasible on the chosen runtime. | Medium-high. This is load-bearing for the §6 safety fix and D7. |
| **A5** | The AI provider returns schema-conformant structured output reliably enough that fail-closed refusals are rare. | Medium-high. Frequent refusals make the product look broken even though the guardrail is behaving correctly. |
| **A6** | Network egress from the app to the AI proxy works on the test device/simulator without special configuration. | Medium. Common source of lost hours. |

### NEEDS POC (build a throwaway spike before committing)

| # | Proof-of-concept | Answers | Time box |
|---|---|---|---|
| **P1** | Hello-world app installed and running on the chosen target (device or simulator), screenshotted. | D1, D2, A1 — and whether a submission is possible at all | **½ day, do this first** |
| **P2** | One screen with 6+ focusable cards: full D-pad traversal, visible focus, safe-zone overlay at 1080p, 14sp floor check. | D2, F6, F7 — whether the chosen runtime handles TV focus well | ½ day |
| **P3** | A 60-second timed multi-step session with automatic advancement and the screen-on flag held. | A2, A3, D17 | ½ day |
| **P4** | Read a bundled text-layer PDF, extract a text span, render the page with that span highlighted. | D7, A4, and the §6 safety fix | ½ day |
| **P5** | One AI call through a thin proxy returning a strict schema; measure malformed-output rate over ~20 calls. | D9, D11, A5, A6 | ½ day |

**Total: ~2.5 days of validation.** Against a 26-day window this is not overhead — P1 alone
determines whether the project can be submitted.

### NEEDS OFFICIAL VERIFICATION

| # | Item | Why it matters |
|---|---|---|
| **V1** | Whether the Video Skills Kit is deprecated. One search result stated *"Video Skills Kit (VSK) is no longer supported"* while the official VSK documentation page carried **no deprecation notice**. **Contradictory evidence — do not rely on VSK either way.** | Only relevant if voice is revisited. Currently moot under D13. |
| **V2** | Whether any documented API allows an app to capture free-form microphone audio on Fire OS or Vega OS. F2 strongly indicates no for the Leanback path; a definitive negative for *all* paths was not established. | Would reopen D13 if a path exists. Low priority. |
| **V3** | Whether "In-App Voice Scrolling and Selection" — which Amazon enables per app on the back end after verification — is available within a hackathon timeframe. | Almost certainly not (manual Amazon enablement). Treat as unavailable. |
| **V4** | Whether publishing the submission repository itself satisfies the Open Source mini challenge (`HACK-829`), or whether a separate contribution is required. | Determines whether a $5,000 + $5,000 prize is available at near-zero cost. Worth one clarification. |
| **V5** | A secondary source described the hackathon tracks as "Machine Learning/AI, Open Ended, Productivity." The **official rules page lists Fire TV, Alexa+, Bee, Ring plus two mini challenges.** Treat the secondary claim as **incorrect**; trust the official rules. | Prevents entering a track that does not exist. |
| **V6** | Whether the Amazon Devices Builder Tools (ADBT) MCP server supports the chosen target on Windows. | Could meaningfully accelerate development (`TECH-908`, `OQ-25`). |
| **V7** | Re-verify all `HACK-` items close to submission, per `CC-05`. Rules can change. | Cheap insurance. |

### Platform-limitation items the spec handles correctly

Document input on Fire TV (no file picker, no natural upload path) is correctly identified
as a design problem (`TECH-905`) rather than assumed away — and D7's bundled-assets
approach resolves it for the MVP. Network dependency, degraded paths and empty states are
specified in Journey 7 rather than left to chance. Text entry is correctly minimized to
D-pad numeric PIN only (`PROD-410`).

---

## 6. Safety & Privacy Review

### Already covered well

- **The confirmation gate as a concept** (`SAFE-501`) — correct answer to AI reading medical documents.
- **Dose immutability** (`SAFE-504`) — closes the highest-harm failure mode.
- **The four-class separation invariant** (`SAFE-940`, `SAFE-1800`) — testable and architecturally load-bearing.
- **Provenance mandatory, missing provenance blocking** (`SAFE-970`, `SAFE-521`).
- **Historical never rendered as current** (`SAFE-011`, `SAFE-520`, `SAFE-1804` requiring non-null observation date).
- **No gap-filling** (`SAFE-502`, `SAFE-912`) — "absent means absent" is the right rule.
- **`UNCLEAR` instead of guessing** (`SAFE-503`).
- **No emergency triage, no symptom assessment** (`SAFE-013`, `SAFE-014`) — and `SAFE-740` correctly forbids conditioning the emergency statement on symptom input, which is the subtle trap most designs fall into.
- **Behavioural-only insights** (`SAFE-703`) with explicit permitted/prohibited examples — unusually concrete and therefore enforceable.
- **Guardrail must be code, not prompts** (`TECH-922`, `RULE-024`) — correct and frequently omitted.
- **Shared-TV privacy** (§27) — profile gate, no pre-entry disclosure, opt-in spoken output, non-specific ambient surfaces.
- **Honest regulatory posture** (`PRIV-1660`, `PRIV-1662`).
- **No secrets, no real patient data, no clinical content in logs** (`PRIV-1640`–`PRIV-1652`), including the often-missed point that **AI prompt/response logging is itself a PHI leak** (`PRIV-1652`).

### Missing / needs strengthening

**S1 — The confirmation gate validates the wrong thing. (Highest severity in this review.)**

`PROD-621` requires showing "the proposed structured item beside **the source text** it came
from." If extraction misread the document, the extracted source text is *also* wrong. The
reviewer compares the model's output against the model's own transcription and confirms a
confidently wrong extraction. **The gate on which the entire safety architecture rests can
be passed by exactly the failure it exists to catch.**

*Recommended safeguard:* the review screen **MUST** display the **original document
region** — the rendered page with the source span highlighted, or an image crop — not the
extracted text. Adopt D7 (text-layer PDFs) and this becomes straightforward. Suggested
amendment: strengthen `PROD-621` and add a new obligation that human confirmation must be
performed against the original document rendering.

**S2 — No control for prompt injection from document content.**

Documents are **untrusted input fed to an LLM.** A document containing adversarial or
malformed text could manipulate the extraction prompt — including instructing the model to
fabricate items or to mark them high-confidence. The spec has no requirement addressing
this anywhere. Even with synthetic data for the hackathon, it belongs in the spec because
the production design follows from it.

*Recommended safeguard:* treat all document content as untrusted data, never as
instruction; keep document text strictly separated from instruction context; and rely on
the confirmation gate plus S1's original-document view as the terminal control. Add an
explicit requirement.

**S3 — `SAFE-917` is not implementable as specified.**

`SAFE-917` requires *deterministic* validation of generated routines against `SAFE-034`'s
prohibition list. But `SAFE-034` prohibits *concepts* — high-impact, plyometric,
breath-holding, inversions, maximal effort, neck/spinal loading, rapid positional change.
Deterministically detecting these in free-text AI output is not feasible; keyword matching
would be trivially evaded by paraphrase and would produce both false positives and false
negatives.

*Recommended safeguard:* adopt **D12** — the AI selects and sequences from a **curated,
pre-vetted movement library**, and does not invent movements. Validation then becomes a
trivial set-membership check plus a duration sum, and `SAFE-917` becomes genuinely
deterministic. This preserves the product intent (AI still generates and personalizes
routines) and is *faster* to build than open generation. **This is both a safety fix and a
schedule win.**

**S4 — Conflict C2: `F-A10` promises what `SAFE-915` forbids.**

`PROD-730`/`F-A10` promise a plain-language explanation of confirmed instructions, and
`PROD-2101` makes it a demo beat. But `SAFE-915` restricts the operation to "linguistic
simplification only" and forbids drawing on general medical knowledge. For a terse
prescription line there is nothing to simplify — any genuinely useful explanation would
require drug knowledge, which `SAFE-507` and `SAFE-731` prohibit. **The feature as
specified either delivers almost nothing or quietly violates the safety boundary.** The
second outcome is the likely one under demo pressure.

*Recommended safeguard:* reframe the action from **"Why this?"** to **"What this says"** —
showing the verbatim original text, the timing expressed in plain words, the source
document and date, and the standing pointer to the clinician. Apply genuine simplification
only where the source actually contains prose to simplify (exercise and diet handouts,
precautions), not to single-line prescriptions. This keeps `SAFE-915` intact and stops the
UI from promising clinical insight. **Do not resolve this by relaxing `SAFE-915`.**

**S5 — No first-run acknowledgement gate.**

`SAFE-950`/`SAFE-951` require transparency statements in orientation and Settings, but
nothing requires the user to *acknowledge* them before first reaching health content. For a
product whose core risk is over-trust (`R-03`), a single explicit acknowledgement is cheap
and materially strengthens the posture.

*Recommended safeguard:* a one-screen, plain-language acknowledgement on first entry into a
Care profile. Not a legal wall of text — one screen, large type, one Select.

**S6 — No specified behaviour for AI failure modes, by type.**

`SAFE-920` says fail closed and Journey 7 covers "AI unavailable" generically, but the
distinct cases — extraction returns malformed output, explanation generation fails, routine
generation fails validation, summary generation fails — have no specified user-facing
behaviour. Under-specification here tends to produce ad-hoc fallbacks that quietly bypass
the guardrail, which is exactly the outcome `SAFE-920` exists to prevent.

*Recommended safeguard:* specify per-operation fallbacks — extraction failure → `UNCLEAR`;
explanation failure → show verbatim original text only; routine validation failure →
offer a vetted preset; summary failure → render regions 1–3 and omit region 4 entirely.
Note that omitting region 4 is safe precisely because of `SAFE-1410`'s separation.

**S7 — No retention rule for the document files themselves.**

`PRIV-602` covers documents and extracted data loosely, and `PRIV-1610` covers storage, but
nothing specifies what happens to a source document **after** extraction and confirmation.
Since S1 requires retaining the original rendering for verification, the document must
persist — so the retention rule needs stating explicitly rather than being left implicit.

**S8 — `SAFE-1522` is an intention, not a mechanism.**

It requires that confirmation "MUST NOT be reducible to a single unconsidered
press-through," but specifies no mechanism. `PROD-623`'s one-at-a-time queue with a position
indicator helps. Combined with S1's original-document view, this is probably sufficient —
but it should be stated as a concrete requirement rather than an aspiration.

### High-risk areas

| Area | Why | Primary control |
|---|---|---|
| **Extraction → confirmation path** | Every clinical error the product could make enters here. | S1 (original-document view) + `SAFE-503` + `SAFE-504` |
| **Generated wellness content for a Care user** | A recovering cardiac/stroke user given inappropriate movement is the highest-harm wellness failure. | D12 curated library + `SAFE-037` + `SAFE-032` precaution gating |
| **Summary region 4** | The one place the product writes free prose about a person's health. | `SAFE-1410` separation + `SAFE-1412` + `SAFE-703` + S6 (omit region 4 on failure) |
| **Over-trust** | Users treating the product as clinical authority or a safety net. | `SAFE-952`, `SAFE-741`, S5 acknowledgement |
| **Demo narration** | The likeliest place an unsupported medical claim actually gets made — spoken, not coded. | `SAFE-2110`, `PROD-2111`; script review before recording |

### Verification: does the design accidentally permit any prohibited behaviour?

| Prohibited behaviour | Permitted anywhere? | Basis |
|---|---|---|
| Diagnosis | **No** | `SAFE-001`; `SAFE-972` blocks a stated diagnosis becoming a reasoned-from attribute; §28.4 has no `Diagnosis` entity |
| Prescribing | **No** | `SAFE-002`; ASSIST regime cannot originate content (`SAFE-915`) |
| Dose changes | **No** | `SAFE-003`, `SAFE-504`, `SAFE-505`; §28.4 has no computed-dose entity |
| Invented medical / doctor instructions | **No** | `SAFE-004`, `SAFE-005`, `SAFE-912`; confirmation gate. **Conditional on fixing S1 and S2.** |
| Unsupported recovery/improvement claims | **No** | `SAFE-008`, `SAFE-703`, `SAFE-1420`, `SAFE-1311` with worked examples |
| Historical treated as current | **No** | `SAFE-011`, `SAFE-520`, `SAFE-1804` |
| Unsafe exercise | **Residual risk** | `SAFE-030`–`SAFE-037` are correct, but enforcement depends on `SAFE-917`, which **is not implementable as written**. **Requires S3/D12.** |
| Autonomous emergency decisions | **No** | `SAFE-014`, `SAFE-740` |

**Conclusion: the safety architecture is sound in design but has two enforcement gaps —
S1 (confirmation validates the wrong artifact) and S3 (`SAFE-917` unimplementable). Both
must be closed before the corresponding features are built. Neither requires weakening any
safety rule; both are fixed by architecture choices (D7 and D12) that also save time.**

---

## 7. Hackathon Compliance Review

Verified 2026-09-27 against official sources: `amazonappdev2026.devpost.com` (rules,
site, resources) and `developer.amazon.com`. Categories are kept separate as the spec
requires.

| Requirement | Status | Evidence / Source | Implementation Impact |
|---|---|---|---|
| **OFFICIAL:** App must run on **Fire OS or Vega OS** | Spec compliant (`HACK-800`) | Official rules: *"Eligible projects for this category have to launch a demo-ready app that works on Fire OS or Vega OS."* | The only fixed platform constraint. Drives **D1**. |
| **OFFICIAL:** Any framework acceptable | Spec compliant (`HACK-801`) | Official rules: *"The requirement is that the project runs on Fire OS or Vega OS."* | **D2** is genuinely free. No framework is mandated. |
| **OFFICIAL:** Submission deadline **2026-10-23, 12:00 pm PT**; no changes after | Spec compliant (`HACK-802`, `HACK-830`) | Official rules | ~26 days. Forces the §3 spine and reserving ~5 days for submission work. |
| **OFFICIAL:** GitHub repo with all source, assets and functional instructions | Spec compliant (`HACK-805`) | Official rules | `README.md` per `PROD-2120` is a deliverable, not an afterthought. |
| **OFFICIAL:** Repo public with visible OSS license **OR** private shared with `testing@devpost.com` + six named Amazon accounts | Spec compliant (`HACK-805a`) | Official rules (`chris-trag`, `knmeiss`, `giolaq`, `anishamalde`, `mosesroth`, `emersonsklar`) | **Submission-blocking.** Recommend the public+OSS route: also satisfies `HACK-829` candidacy (pending **V4**). |
| **OFFICIAL:** Demo video **<3 min**, public on YouTube/Vimeo, showing the app functioning on its device | Spec compliant (`HACK-806`) | Official rules | Drives the entire §8 storyboard and the time allocation. |
| **OFFICIAL:** Fire TV demo must show **a real Fire TV device or the Fire TV/Vega simulator** | Spec compliant (`HACK-806a`) | Official rules | **The hardest gate.** Depends on **A1**/**P1**. Validate first. |
| **OFFICIAL:** No third-party trademarks or copyrighted music without permission | Spec compliant (`HACK-806b`) | Official rules | Silence or original audio only. Easy to get wrong. |
| **OFFICIAL:** Text description of features | Spec compliant (`HACK-807`) | Official rules | Write during build, not at the end. |
| **OFFICIAL:** **Product Feedback is required** — tools used, what worked, what needs improvement, onboarding, likelihood to reuse | Spec compliant (`HACK-808`) | Official rules | A required field that is easy to miss. Keep notes from day one. |
| **OFFICIAL:** Declare primary track (+ any mini challenges) | Spec compliant (`HACK-809`) | Official rules | Fire TV. |
| **OFFICIAL:** All materials in English | Spec compliant (`HACK-810`) | Official rules | No impact. |
| **OFFICIAL:** Free and accessible to judges through the judging period | Spec compliant (`HACK-811`) | Official rules | No licence keys or paywalls in the build. |
| **OFFICIAL:** Third-party SDKs/APIs/data must be authorized and licence-compliant | Spec compliant (`HACK-812`) | Official rules | Track every dependency's licence. Engages **D8**/**D9**. |
| **OFFICIAL:** New, or significantly updated during the submission period | Compliant by construction (`HACK-813`) | Official rules | Project began 2026-09-27. |
| **OFFICIAL:** Original work, solely owned, no IP violation | Spec compliant (`HACK-814`) | Official rules | Relevant to any movement-library content in **D12** — author it or licence it properly. |
| **OFFICIAL:** Judging — four criteria at **25% each** (Tech Implementation, Design, Potential Impact, Quality of Idea) | Spec compliant (`HACK-821`–`HACK-824`) | Official rules | See §8 mapping. Note the Tech Implementation gap below. |
| **OFFICIAL:** Friction logs score **up to 10% bonus** | Spec compliant (`HACK-826`) | Official rules | **Materially significant.** Start the log on day one (`DP-16`). |
| **OFFICIAL:** Optional AWS Builder and Open Source mini challenges ($5k + $5k credits each) | Spec compliant (`HACK-828`, `HACK-829`) | Official rules | A project may win one track + one mini prize. Decide via `OQ-10`; must not distort the product (`RULE-004`). |
| **OFFICIAL:** Eligibility — age of majority, jurisdiction restrictions, no conflict of interest | **Unconfirmed for this entrant** | Official rules | **`OQ-11`. Owner must confirm personally. A late failure here wastes the entire effort.** |
| **OFFICIAL:** Appstore publication | **NOT required** | Official rules require a *demo-ready* app + repo + video; no publication requirement found | Removes a multi-day certification path. Correctly captured in §33.7. |
| **OFFICIAL:** Accessibility | **No hackathon requirement found** | Not present in the official rules | Accessibility is a **PRODUCT RECOMMENDATION** (`HACK-416`–`HACK-417` are Amazon *design guidance*, not hackathon rules) and supports the Design criterion. |
| **OFFICIAL:** Mandatory AI/ML usage for the Fire TV track | **No requirement found** | Official rules list AI as a *priority area*, not a requirement | AI is **OUR DESIGN DECISION**, aligned with `HACK-804` priority areas. |
| **OFFICIAL:** Alexa integration for Fire TV track | **NOT required** | Alexa+ is a separate track (`HACK-803`) | Supports **D13** (skip voice). |
| **OFFICIAL:** Physical hardware | **NOT required** for the demo | Simulator explicitly permitted (`HACK-806a`); `HACK-817` reserves a right to request hardware access only for non-widely-available hardware | Fire TV is a consumer device; low concern. |
| **OFFICIAL:** Track list | **Verified: Fire TV, Alexa+, Bee, Ring + 2 mini challenges** | Official rules page | A secondary source claiming "ML/AI, Open Ended, Productivity" tracks is **incorrect** (**V5**). Do not act on it. |
| **PRODUCT RECOMMENDATION:** Appstore content policy — *"must not include content that provides inaccurate or misleading medical advice or makes unsubstantiated medical claims"*; policy applies to **metadata** too | Spec compliant (`HACK-960`, `HACK-961`) | Amazon Appstore Restricted Content / Content Policy | Good discipline even without publication. Engages `OQ-09` (display name). |
| **NEEDS VERIFICATION:** Stricter health-app obligations (mandatory diagnosis disclaimer, accuracy-claim substantiation) described by secondary sources | **Unverified — correctly not asserted** | Not confirmed verbatim on primary Amazon policy pages | Spec records as `OQ-08`; its own `SAFE-` rules already meet or exceed them. Recommend adopting anyway — zero cost. |
| **NEEDS VERIFICATION:** Does publishing the submission repo satisfy `HACK-829`? | **Unverified** | — | **V4.** Worth one clarification for a low-cost prize. |
| **NEEDS VERIFICATION:** Re-verify all `HACK-` items before submission | Pending | `CC-05` | Rules can change mid-event. |

### One strategic gap in hackathon alignment

**Tech Implementation (25%) asks whether the project "effectively leverage[s] the required
APIs, SDKs, or device capabilities for the specified track."** The spec ensures the app
*runs on* Fire TV but does not require it to *use any Fire TV-specific capability*. An app
that merely runs there risks reading as a generic app on a TV.

*Recommendation (OUR DESIGN DECISION, not a requirement):* lean explicitly into device
capability as the technical story — a genuinely native D-pad focus model, the safe-zone and
type-scale system, VoiceView content descriptions, and correct Back/lifecycle handling —
and say so in the `HACK-807` description and `HACK-808` feedback. The **multi-modal UX**
priority area (`HACK-804`) is satisfiable as *D-pad-first with deliberate voice
exclusion*, which — given F2 — is a more credible and more interesting technical narrative
than a half-working voice feature. **Do not add unrelated Fire TV features to score points
(`RULE-004`).**

---

## 8. Demo Strategy

One flow, under 3 minutes, on the real device or official simulator (`HACK-806`,
`HACK-806a`). This changes nothing about the product — it sequences what §30.2 already
specifies, and it doubles as the integration test (`DP-15`).

**Total: 2:50. Build in this order, because this order is the submission.**

### Beat-by-beat

| # | Time | Beat | Screens | What is real | What is seeded |
|---|---|---|---|---|---|
| 1 | 0:00–0:20 | **The problem, on screen.** Open on the Fire TV home, launch the app. Narration states the problem in one sentence: a person two months past a cardiac event, alone during the day, with instructions spread across five documents. | Fire TV launcher → Profile Select | App launch on device/simulator; Profile Select with two profiles showing name + avatar only (`PRIV-702`) | Both profiles pre-created |
| 2 | 0:20–0:35 | **Today answers "what now."** Select the Care profile. The Now card fills the screen: *"Before breakfast — Tablet A, 1 tablet,"* with the dose line as transcribed and a quiet source line *"From Prescription, 12 Aug 2026."* Next and Done visible below. | Today | Real day construction from confirmed items; real Now/Next/Done state; real provenance rendering | The care plan was confirmed before recording |
| 3 | 0:35–0:50 | **Acting and recording.** Select the card → Item Detail → **Mark as taken**. Now advances to the next item. Calm acknowledgement, no spectacle. | Item Detail → Today | Real completion write; real re-derivation of Now | — |
| 4 | 0:50–1:35 | **The trust moment — the centrepiece.** Navigate to Documents. One document is in **Needs Review**. Open it: the rendered document page sits beside the proposed structured item, **with the source span highlighted on the page itself**. Show the dose text matching. Press **Confirm**. Cut to Today — the item is now in the plan. Narration: nothing reaches this person's plan until a human has checked it against the document. | Documents → Review & Confirm → Today | **All of it.** Real text-layer PDF, real extraction, real span highlighting, real confirmation gate, real plan mutation | The document file is bundled (the *transfer* is seeded; the *pipeline* is real) |
| 5 | 1:35–1:45 | **The safety boundary, shown not claimed.** On the request surface, an out-of-scope clinical question is declined in one short line and redirected to the clinician. | Request surface | Real refusal path through the guardrail (`SAFE-916`) | The question is typed/selected for the demo |
| 6 | 1:45–2:05 | **Wellness — one request, one routine.** Switch to the Wellness profile. Today leads with time presets. Select **15 min**, then a goal chip. The routine appears with every segment and an explicit total: 2 min warm-up, 5 min mobility, 5 min light exercise, 3 min cooldown. **Executed entirely on the non-voice path** (`PROD-2102`). | Profile Select → Today → Routine Preview | Real generation/selection from the curated library, real duration validation (`SAFE-917`) | — |
| 7 | 2:05–2:30 | **Guided session, hands down.** Press Start and put the remote down. The player advances automatically: current activity, remaining time, short instructions, progress, next activity. Skip forward to the completion view; the session is recorded. | Session Player → Session Complete | Real timing, real automatic advancement, real recording (`PROD-122`) | Video is time-compressed — **narration must say so** (`PROD-2111`) |
| 8 | 2:30–2:50 | **The loop closes.** Progress shows the streak updating. Open the Daily Summary: recorded facts, historical information with dates, user activity, and — visually separated and labelled — the AI-written summary. Close on the separation. | Progress → Daily Summary | Real records, real four-region rendering (`SAFE-1410`) | — |

### Fire TV interaction that must be visible

Every navigation in the video is a **D-pad press with a visible focus move** — no cursor, no
touch, no scrubbing. Show at least one **Back** press returning exactly one level
(`PROD-430`). Keep everything inside the safe zone. The interaction model should be legible
to a judge who has never seen the app.

### The AI moments (three, deliberately)

1. **Extraction → proposal** (beat 4) — ASSIST regime, transform only.
2. **Refusal** (beat 5) — the guardrail visibly holding.
3. **Routine generation + summary** (beats 6, 8) — GUIDE regime generating, and labelled interpretation.

Three moments is enough. Each is short and each demonstrates a *different* AI role, which
is a stronger technical story than one long AI showcase.

### What must NOT be demonstrated

| Do not show | Why |
|---|---|
| Any free-form voice interaction | F2: officially unsupported. Showing a fake or unreliable voice beat risks looking broken and misrepresents capability (`PROD-2111`). |
| An AI answering a clinical question | Direct `SAFE-916` violation, and the fastest way to fail the Appstore medical-claims standard (`HACK-960`). Show the **refusal** instead. |
| Any health value without its date | `SAFE-520`. A single undated reading on screen undercuts the entire trust narrative. |
| Live OCR of a scanned document | Not in MVP (D7). Do not imply a capability that does not exist. |
| Clinical improvement framing in the summary | `SAFE-703`, `SAFE-1420`. Highest-risk narration line in the whole video. |
| Real patient documents or real names | `HACK-980`, `PRIV-982`. |
| Any screen with a key, credential or local path visible | `PRIV-2113`. |
| Uncompressed real-time waiting on an AI call | Wastes scarce seconds. Cut, and disclose the cut. |

### Mapping MVP capabilities to the judging criteria

Evidence the demo should surface for each — no scores, no ranking.

**Tech Implementation.** The extraction → proposal → **confirmation gate** → plan mutation
pipeline, shown working end to end on a real document. The guardrail visibly refusing. A
native D-pad focus model with correct Back and lifecycle handling. Provenance enforced at
the data layer, not painted on. Deliberate, documented voice exclusion grounded in official
platform limits — a more credible technical claim than a fragile voice feature.

**Design.** Safe zone and type scale observed; focus always visible and never lost; the Now
card answering "what now" without navigation; one primary action per screen; status never
encoded in colour alone; a hands-free session; and a calm tone appropriate to a recovering
user. The four-region summary is itself a design artifact — it makes a safety boundary
legible.

**Potential Impact.** Two concrete personas with distinct, real needs. A large, genuinely
underserved population (post-event recovery alone at home) plus a broad wellness audience.
The TV as the correct surface for both — legible at distance, four buttons, already part of
daily routine. The caregiver setup path shows a realistic adoption route.

**Quality of the Idea.** Reframing the television as a care-and-wellness companion rather
than a media device. The two-regime AI model — transform in the clinical domain, generate in
the wellness domain — as a distinctive answer to health-AI safety. The confirmation gate as
a product mechanic, not a disclaimer. Two use cases held in one coherent experience without
either collapsing into the other.

### Demo production notes

- Rehearse **offline** — `TECH-930`/`R-16`. A network hiccup during recording is the most
  common way a demo dies.
- Record in **one take per beat**, then cut. Do not attempt a single continuous take.
- **Silence or original audio only** (`HACK-806b`).
- Script the narration and review it against `SAFE-2110` **before** recording. The narration
  is where an unsupported medical claim actually gets made.
- Build the storyboard **first** and let it drive build order (`TECH-2130`).

---

## 9. Major Risks

Ordered by expected cost. Spec risk IDs are cross-referenced where they exist; new risks
are marked **NEW**.

| Risk | Impact | Likelihood | Mitigation | Validation |
|---|---|---|---|---|
| **No runnable target** — no Fire TV device and no simulator working on Windows 11 (`R-11`, **A1**) | **Fatal** — `HACK-806a` unmet, no valid submission | Medium | Resolve `OQ-02`/`OQ-03` today. Fire OS (D1) maximizes tooling options on Windows. If neither works, acquiring a Fire TV Stick becomes the critical path. | **P1 — hello-world on target. Do this before anything else.** |
| **Platform decision drifts** (`R-10`, `OQ-01`) | **High** — every other decision is downstream; late reversal wastes days | Medium-high | Decide D1 within 48 hours. Vega is effectively excluded by F5 on a Windows host. | P1 |
| **Timeline: MVP as written is ~2–3× the available window** (`R-13`) | **High** — an incomplete demo | **High** | Adopt the §3 Demo Spine. Demote the nine P2 items. Reserve ~5 days for submission work. Storyboard-driven build order. | Weekly check: can the §8 flow run end to end today? |
| **`SAFE-917` unimplementable; unsafe routine reaches a user** (**NEW / S3**, extends `R-05`) | **High** — safety failure and a broken zero-tolerance criterion (`SC-27`) | Medium-high if unaddressed | Adopt **D12**: curated movement library; AI selects and sequences only. Validation becomes set-membership + duration sum. | Unit test: every library movement passes `SAFE-034`; no generated routine can contain a non-library movement |
| **Confirmation gate validates the model against itself** (**NEW / S1**) | **High** — the central safety mechanism is defeated by the exact failure it exists to catch | Medium-high if unaddressed | Show the **original document region** with the span highlighted, not extracted text. Enabled by **D7**. | **P4 — render a PDF page with a highlighted span** |
| **Submission mechanics missed** — repo access, public video, Product Feedback (`R-19`) | **Fatal** — unjudged or disqualified | Medium (easy to defer) | Treat `DOD-21`–`DOD-33` as blocking. Configure repo access and upload a private placeholder video in **week one**, not the final week. | Dry-run the full submission form 5 days early |
| **Document pipeline consumes disproportionate time** (`R-14`) | High | Medium-high | **D7** removes OCR from the critical path entirely. Bundle documents; keep the pipeline real. | **P4** |
| **AI structured-output unreliability** (**NEW**, related to `R-17`) | High — fail-closed refusals make a correct system look broken | Medium | **D11** strict schema + bounded retry. Per-operation fallbacks (**S6**). Pre-generate and cache at confirmation (**D10**). | **P5 — measure malformed-output rate over ~20 calls** |
| **Session Player breaks on device** — stutter or screen timeout (**A2**, **A3**) | High — the most visible demo beat | Medium | Validate the screen-on flag and timing early. Keep animation minimal, which `PROD-438` already requires. | **P3 — 60-second timed session with screen-on held** |
| **Play Services absence invalidates a dependency choice** (**NEW / F1**) | High if discovered late | Medium | Record the constraint now. No Firebase, no ML Kit, no Play-Services-dependent library. Affects D8 and any auth/analytics/crash choice. | Dependency audit before adding anything |
| **`F-A10` delivers nothing or violates `SAFE-915`** (**NEW / S4, C2**) | Medium-high — a demo beat that is either empty or unsafe | Medium-high | Reframe to **"What this says."** Apply true simplification only to prose-bearing documents. **Do not relax `SAFE-915`.** | Review the rendered output for a real prescription line before committing the beat |
| **Scope drift toward fitness-only** (`R-18`) | **High** — loses the differentiator and violates an explicit owner instruction | Medium (wellness is easier to build) | The care journey holds the largest demo allocation (beat 4 = 45s). `RULE-002`, `RULE-003`. Build the care spine **first**, while energy is high. | Weekly: does the demo still show both journeys? |
| **10-ft UI underestimated; reads as a web app on a TV** (`R-15`) | Medium-high — directly hits 25% Design | Medium | §12 as a hard checklist. **D2** (Compose for TV) for first-class focus. Test focus traversal continuously, not at the end. | **P2 — 6-card focus traversal + safe-zone overlay** |
| **Offline/degraded paths untested; demo dies on a network hiccup** (`R-16`) | High — demo-fatal | Medium | **D10** pre-generate and cache; `TECH-930`; Journey 7 paths built, not assumed. | Rehearse the entire demo with networking disabled |
| **Prompt injection via document content** (**NEW / S2**) | Medium for the hackathon (synthetic data); **high** for any real deployment | Low-medium now | Treat document text as untrusted data, never instruction. Keep it out of instruction context. Confirmation gate + **S1** as terminal control. | Adversarial test: a synthetic document containing instruction-like text |
| **Over-trust by a real user** (`R-03`) | High (real-world) | Medium | `SAFE-952`, `SAFE-741`, plus **S5** first-run acknowledgement. | Review every user-facing string for overclaiming |
| **Demo video over 3 minutes or missing the device** (`R-20`) | High | Medium | §8 allocation; rehearse to time; verify device/simulator footage is unmistakable. | Time the rehearsal |
| **Copyrighted music in the video** (`R-21`) | Medium-high | Medium | Silence or original audio only (`HACK-806b`). | Check before upload |
| **Eligibility failure** (`OQ-11`) | **Fatal** | Low | Owner confirms against the official rules **today**. | One-time check |
| **App name reads as a clinical claim** (`R-22`, `OQ-09`) | Medium | Low-medium | Decide the display name before any store-facing metadata exists. Internal project name unchanged. | Owner decision |

---

## 10. Open Questions

Only questions that genuinely require an owner decision or technical validation. Spec
questions that are already resolved by this review's recommendations are marked as such.

### Blocking — needed within 48 hours

| # | Question | Who | Notes |
|---|---|---|---|
| **Q1** | **Do you have a physical Fire TV device? If not, does an official Fire TV emulator/simulator run on your Windows 11 machine?** (`OQ-02`) | Owner + **P1** | **Highest-severity unknown in the project.** Without one of these, `HACK-806a` cannot be met and there is no submission. Everything else is secondary. |
| **Q2** | **Fire OS or Vega OS?** (`OQ-01`) | Owner | This review recommends **Fire OS** (F5: Vega tooling excludes Windows; F4: two devices only). Confirm so D2–D7 can proceed. |
| **Q3** | **Is a macOS or Linux environment available** — machine, VM or cloud host? (`OQ-03`) | Owner | Only matters if you want to overrule Q2 toward Vega. If the answer is no, Q2 is effectively settled. |
| **Q4** | **Have you confirmed your personal eligibility** under the official rules — jurisdiction, age of majority, no conflict of interest? (`OQ-11`) | Owner | Five minutes now; catastrophic if discovered on 23 October. |
| **Q5** | **Are you building solo, and roughly how many hours per day?** | Owner | **Not in the spec, and it materially changes the §3 spine.** A solo developer at 3 hours/day and a solo developer at 10 hours/day need different scopes. I have assumed solo, substantial daily hours. Please correct me. |

### Needed before the Architecture Specification

| # | Question | Who | This review's position |
|---|---|---|---|
| **Q6** | **Which AI provider, and do its terms permit sending clinical text?** (`OQ-06`) | Owner + Architecture | `PRIV-1622` excludes any provider whose terms permit training on submitted content. Also decides D9 and the D4 proxy shape. |
| **Q7** | **Confirm the thin-proxy backend (D4) and on-device-only clinical storage (D5).** (`OQ-04`, `OQ-07`) | Owner | Recommended: proxy for AI only, all clinical data on-device. Simplest path that satisfies `PRIV-1640` without building auth. |
| **Q8** | **Approve the text-layer-PDF decision (D7)?** (replaces `OQ-13`) | Owner | Resolves conflict **C1**, closes safety gap **S1**, removes OCR from the critical path. Highest-leverage single decision available. |
| **Q9** | **Approve the curated-movement-library model (D12)?** | Owner | Makes `SAFE-917` implementable (**S3**), and is faster than open generation. Preserves AI generation of the *routine*. |
| **Q10** | **Approve reframing `F-A10` from "Why this?" to "What this says"?** | Owner | Resolves conflict **C2**. The alternative — relaxing `SAFE-915` — should be rejected. |
| **Q11** | **Confirm that pre-generating AI content at confirmation time (D10) satisfies `TECH-930`.** | Owner | Resolves conflict **C3**. Makes the care path genuinely offline. |
| **Q12** | **How should conflict C4 be resolved** — the squeeze between the 5-second glance, no-scroll Now/Next tier, card-level provenance, and low information density? | Owner + design | Suggested: provenance as **one short quiet line** at reduced emphasis, with full provenance in Item Detail. This requires a small `PROD-552` clarification, so it needs your approval rather than a unilateral choice. |
| **Q13** | **Enter the mini challenges?** (`OQ-10`, **V4**) | Owner | Public repo likely satisfies both `HACK-805a` and `HACK-829` candidacy at near-zero cost — worth verifying (**V4**). AWS Builder only if D9 lands on AWS. Neither may distort the product. |

### Technical validation (answered by POCs, not by discussion)

| # | Question | POC |
|---|---|---|
| **Q14** | Does the chosen runtime give acceptable D-pad focus behaviour at 1080p within the safe zone? | **P2** |
| **Q15** | Can the screen be held awake for a 15-minute session, and does timing stay smooth on target hardware? | **P3** |
| **Q16** | Can a PDF page be rendered with a highlighted text span on the chosen runtime? | **P4** |
| **Q17** | What is the malformed-structured-output rate from the chosen model, and is bounded retry sufficient? | **P5** |
| **Q18** | Does ADBT support the chosen target on Windows? (`OQ-25`, **V6**) | Quick check; potential accelerator |

### Deferred — do not spend time on these now

`OQ-20` (recency windows), `OQ-21` (duration tolerance), `OQ-22` (idle timeout — now P2),
`OQ-24` (rollover boundary), `OQ-26` (exact type scale and colour tokens), `OQ-27`
(VoiceView scope). All are design detail that follows the platform decision. `OQ-12` (third
persona) and `OQ-14` (caregiver role) are resolved by §3's demotions.

---

## 11. Recommended Build Order

High-level phases. No implementation detail. Day counts assume ~26 calendar days and are
indicative, not a commitment.

### Phase 0 — Environment validation (Days 1–2) — **gate everything on this**

Run **P1** (hello-world on the chosen target, screenshotted). Answer Q1–Q5. Decide D1 and
D2. Run **P2** (focus traversal + safe-zone overlay).

**Gate:** if P1 fails, stop and solve the target problem before writing a line of product
code. Nothing else matters until an app runs somewhere that satisfies `HACK-806a`.

### Phase 1 — Architecture decisions (Days 2–3)

Produce and get approval on `ARCHITECTURE_SPEC.md`, resolving D1–D18 and Q6–Q13. Run **P4**
and **P5** to de-risk D7, D9 and D11 before committing. Set up the repository, the
secrets-exclusion configuration (`PRIV-1641`), **and repo access for judges** (`HACK-805a`)
— now, not in the final week. Start the friction log (`HACK-826`).

**Gate:** `RULE-020` — no application code before this is approved.

### Phase 2 — Fire TV foundation (Days 4–7)

The 10-ft UI system: type scale, safe zone, colour tokens, focus treatment, navigation
shell, Back semantics, Profile Select. Run **P3** here so the session runtime is de-risked
before it is needed. **Establish the provenance-carrying data model before any health
surface exists** (`DP-06`) — this is the one thing that is genuinely expensive to retrofit.

**Gate:** D-pad traversal clean on every existing screen; provenance impossible to omit.

### Phase 3 — Core care product (Days 7–13) — **build this first, while energy is high**

Today with Now/Next/Done; Item Detail and completion; Care Plan read views for all five item
types; Health Info with provenance; the deterministic day/plan engine (`TECH-906`); seeded
Care persona with bundled synthetic documents.

**Rationale:** the care half is the differentiator and the harder build. Doing it first
protects against `R-18` scope drift toward fitness-only. Wellness is easier and can absorb
compression later; the care spine cannot.

**Gate:** demo beats 2 and 3 run end to end.

### Phase 4 — AI and the confirmation gate (Days 13–18) — **the centrepiece**

The guardrail layer **first** (`DP-05`, `SAFE-920`) — it ships with the first AI feature, not
after. Then extraction → proposals with source spans; the Review & Confirm screen **with
original-document rendering** (S1); the two-regime separation (`SAFE-900`); routine
generation against the curated library (D12) with deterministic validation; pre-generate and
cache at confirmation (D10); the refusal path.

**Gate:** demo beats 4, 5 and 6 run end to end. `SC-20`–`SC-28` tests exist and pass.

### Phase 5 — Wellness runtime and progress (Days 18–21)

Session Player with automatic advancement, pause/resume, honest partial recording; activity
log; streak; Daily Summary with the four-region separation; behavioural insights.

**Gate:** demo beats 7 and 8 run end to end. The full §8 flow is now rehearsable.

### Phase 6 — Safety, privacy and accessibility hardening (Days 21–23)

PIN; precaution gating; care-team card; first-run acknowledgement (S5); per-operation AI
fallbacks (S6); demo-data labelling; logging audit (`PRIV-1650`–`PRIV-1652`); secrets scan;
VoiceView content descriptions; string review for overclaiming.

**Note:** `SAFE-` work is *verified* here, not *started* here — it was built alongside its
features per `DP-05`.

**Gate:** every Section 35.2 and 35.3 zero-tolerance criterion verified at zero.

### Phase 7 — Testing and rehearsal (Days 23–25)

Full D-pad traversal of every screen; safe-zone and type-size verification at 1080p; **the
entire demo rehearsed offline**; both journeys completed with voice disabled and no typing;
degraded paths exercised; timing rehearsal against the 3-minute limit.

### Phase 8 — Demo and submission (Days 25–26)

Record and cut the video (<3 min, device/simulator footage, silence or original audio);
upload publicly; write the description (`HACK-807`) and Product Feedback (`HACK-808`);
finalize the friction log; complete `README.md` (`PROD-2120`); verify repo access; submit
**before 2026-10-23, 12:00 pm PT**.

**Do not leave submission work to the final day.** Recommendation: complete a full dry-run
submission on Day 21 with whatever exists, then refine. `R-19` is a fatal risk and it is
entirely self-inflicted.

### Cross-cutting, every phase

Friction log entries as they occur (`HACK-826`). Notes for the Product Feedback field.
Weekly check: *can the §8 demo flow run end to end today, and does it still show both
journeys?*

---

## 12. Final Recommendation

### Is the current product direction coherent?

**Yes.** Both use cases are preserved and neither dominates. Fire TV is genuinely primary
rather than a deployment target. The companion framing holds. The trust architecture — the
confirmation gate, the two AI regimes, the provenance model — is a real differentiator and
maps cleanly onto the judging criteria. **The product concept should not be changed.**

The direction is stronger than it needs to be for a hackathon, which is a compliment to the
concept and a warning about the scope.

### Is the MVP realistic?

**As written in §30.2: no.** Roughly 47 feature IDs across 10+ screens, on an unchosen
platform, in 26 days, is over-scoped by about 2–3×.

**With this review's changes: yes, but tight.** Specifically: adopt the §3 Demo Spine,
demote the nine P2 items, take **D7** (text-layer PDFs — removes OCR entirely) and **D12**
(curated movement library — makes safety validation trivial *and* is faster), and reserve
~5 days for submission work. That reduces the build to roughly 12 screens and one AI
pipeline, which is achievable.

The scope risk is not really feature count. It is that **the care half is harder than the
wellness half, and under pressure the wellness half is what gets finished.** Building the
care spine first (Phase 3) is the structural defence against that.

### What must be resolved before coding?

1. **Q1 — device or simulator on Windows.** Highest-severity unknown. Without it there is no valid submission.
2. **Q2 — Fire OS or Vega OS** (`OQ-01`). Recommend Fire OS. Gates every downstream decision.
3. **Q4 — personal eligibility** (`OQ-11`). Five minutes; fatal if wrong.
4. **The four internal conflicts:** C1 via D7, C2 via reframing `F-A10` (Q10), C3 via D10 (Q11), C4 via Q12.
5. **The two safety gaps:** S1 (confirmation must show the original document, not extracted text) and S3 (`SAFE-917` needs D12 to be implementable).
6. **Q5 — solo, and how many hours a day.** Not in the spec and it changes the spine.
7. **An approved `ARCHITECTURE_SPEC.md`** resolving D1–D18 (`RULE-020`).

### What should we validate first?

In this order, roughly 2.5 days total:

**P1** hello-world on target → **P2** D-pad focus and safe zone → **P4** PDF page with
highlighted span → **P5** structured-output reliability → **P3** timed session with screen
held awake.

**P1 is not optional and not deferrable.** It answers whether this project can be submitted
at all. Do it before writing any product code.

### What should NOT be changed?

- **The healthcare / care use case.** It is the differentiator and it is harder than the wellness half. Protecting it is the single most important scope decision.
- **Fire TV as the primary experience** (`PROD-400`). No web-first, no phone-first.
- **Both use cases in one product.** Do not let this become fitness-only (`R-18`) or clinical-only.
- **Section 18 — the AI safety boundaries.** They may be strengthened or clarified, never weakened (`CC-03`). In particular, **do not resolve conflict C2 by relaxing `SAFE-915`.** Reframe the feature instead.
- **`SAFE-940` — the four-class separation invariant.** Reject any architecture that cannot express it (`SAFE-941`).
- **The confirmation gate** (`SAFE-501`). Fix *how* it verifies (S1); never remove *that* it verifies.
- **`SAFE-504` — dose text immutability.**
- **The guardrail layer as code, not prompts** (`TECH-922`). Do not defer it to a hardening pass.
- **Provenance-first build order** (`DP-06`). Retrofitting this is the most expensive mistake available.

### The one-sentence version

The concept is strong and should not be touched; the scope must be cut to a ranked demo
spine; two architecture decisions (text-layer PDFs, curated movement library) simultaneously
fix the two real safety gaps and save time; and nothing should be built until it is known
that an app can actually run on a Fire TV target from this machine.

---

*End of review. `PROJECT_MASTER_SPEC.md` was not modified. No code, scaffolding, or
dependencies were created. Awaiting approval before any implementation or architecture
work.*
