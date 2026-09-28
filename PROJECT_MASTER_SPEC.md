# PROJECT MASTER SPEC — AI Assistant Healthcare

**Status:** DRAFT — awaiting owner approval
**Version:** 1.0.0
**Date:** 2026-09-27
**Owner:** yadav.manan@outlook.com
**Document type:** Authoritative product specification (single source of truth)
**Primary platform:** Amazon Fire TV / Fire TV Stick
**Built for:** Build, Ship, Shape: Amazon Developer Hackathon 2026 — Fire TV track

---

## READ THIS FIRST

This document is the **single source of truth for the product**. It defines **WHAT** is
being built and **WHY**. It deliberately does **NOT** define **HOW** it will be
implemented. A separate `ARCHITECTURE_SPEC.md` will be produced and approved *after*
this document is approved.

No application code, project scaffolding, dependency installation, or UI work may begin
until this document is approved by the owner.

### Requirement ID conventions

Every normative statement in this document carries a stable ID so that future work can
cite it precisely. Categories are kept strictly separate, as required.

| Prefix | Category | Meaning |
|---|---|---|
| `HACK-` | **A. Official hackathon requirement** | Verified against the official Devpost rules or official Amazon developer documentation. A citation is given. |
| `PROD-` | **B. Product requirement** | Derived from the owner's product definition. Authoritative product intent. |
| `SAFE-` | **C. Medical / safety requirement** | Clinical-safety boundary. Non-negotiable. |
| `PRIV-` | **D. Privacy / security requirement** | Health-data protection and shared-screen privacy. |
| `TECH-` | **E. Technical recommendation** | Advisory. Not a locked decision. Resolved in the Architecture phase. |
| `FUT-` | **F. Future / optional** | Explicitly deferred beyond MVP. Preserved, not deleted. |

Normative language: **MUST** / **MUST NOT** are binding. **SHOULD** is a strong default
that requires written justification to deviate from. **MAY** is optional.

### Source verification note

All `HACK-` items were verified on 2026-09-27 against primary sources only (the official
Devpost hackathon site and `developer.amazon.com`). Where a requirement could **not** be
confirmed from a primary source, it is recorded as an **Open Question** in Section 39
rather than asserted as a requirement. This document does **not** invent hackathon
restrictions. See Section 33 for the full verified requirement set and citations.

---

## 1. Executive Summary

**AI Assistant Healthcare** is an AI-powered personal health, wellness and fitness
companion built specifically for Amazon Fire TV. It turns the television — the one screen
that is already on, already central to the living room, and already usable from across
the room with a simple remote — into a calm daily companion that helps a person follow
the health routine they have already been given, and stay physically active when they have
very little time.

The product serves two distinct situations with one coherent experience.

**Situation 1 — Health / Care Companion.** A person recovering from a serious cardiac or
neurological event is following a care routine provided by their doctor: medicines at
specific times relative to meals, prescribed exercises, meal instructions, activity
precautions, tests and follow-up checkups. When that person is alone during the day, the
hard part is not motivation — it is *remembering and organizing* a large amount of
instruction that arrived as paper and PDFs. The application ingests doctor-provided
documents, organizes the information they contain into a structured care plan, and
presents it on the TV as a simple, dated, source-attributed daily view: what to do now,
what is next, what is already done.

**Situation 2 — Busy / Healthy User.** A person who is generally healthy but
time-constrained says, in plain language, *"I have 10–20 minutes before work — give me a
quick workout to kick-start my day."* The application understands the available time, the
goal and the user's preferences, produces an appropriately structured routine, and then
guides it step by step on the big screen with clear timing, instructions and progress.

Both situations feed one loop: verified information in, AI organization and
personalization, today's plan, the user acts, completion is recorded, a daily summary is
produced, and future personalization improves.

**The product's defining constraint is trust.** The AI organizes, summarizes, explains,
and generates *wellness* content. It never diagnoses, never prescribes, never alters a
dose, and never invents a clinical fact or a doctor instruction. Information a clinician
provided is the source of truth; AI output is visibly and structurally separated from it.
Every health value carries its source, its date and its context, and historical readings
are never presented as current measurements.

**The product's defining medium is the 10-foot experience.** This is not a web dashboard
displayed on a television. It is designed for a Fire TV remote, a D-pad, large type,
unambiguous focus, minimal typing, low cognitive load, and users who may be older,
recovering, or simply not technically confident. It must be fully usable without voice.

The Fire TV track of the hackathon explicitly names **fitness** and **multi-modal UX**
among its priority areas, which aligns directly with this product without any need to
reshape it.

---

## 2. Product Vision

A television that quietly helps you take care of yourself.

Health information today arrives fragmented and in the wrong format for the moment it is
needed. A discharge summary is a dense PDF. A prescription is handwriting on paper. Meal
instructions are a verbal aside at the end of a consultation. Exercise instructions are a
photocopied sheet. All of it is correct, and almost none of it is available in a usable
form at 8:15 in the morning when the person is alone and trying to work out which tablet
goes before breakfast.

Meanwhile the healthiest screen in the house is the least used for health. The TV is
large, legible from a chair, operable with four arrow keys and a select button, and
already part of daily routine. It asks nothing of the user's dexterity, eyesight or
technical confidence.

**The vision:** Fire TV becomes a personal companion that holds a person's health routine
and wellness practice for them — organizing what their clinician already told them,
guiding the movement they already intend to do, remembering what they have completed, and
giving them a simple honest picture of their day. Not a hospital system. Not a chatbot.
Not a workout video library. A companion.

**Long-term, this extends naturally** to caregivers who want to support a family member
remotely, to households where several people each have their own routine, and to richer
guidance as more verified information becomes available — all without changing the core
promise.

---

## 3. Product Mission

To make it easy for a person to follow the health routine they have already been given,
and to stay active in the time they actually have — using the simplest screen in their
home, with an AI that organizes and guides but never oversteps.

The mission is expressed in five commitments that govern every product decision:

1. **Reduce the burden of remembering.** The user should never have to hold the day's
   routine in their head, and never have to hunt through documents to answer "what now?"
2. **Never overstep clinically.** Organize, summarize, explain, remind, and generate
   wellness content. Do not diagnose, prescribe, adjust, or invent.
3. **Be honest about provenance.** Every fact shows where it came from and when. AI
   interpretation is always labelled as such and never blended into clinical fact.
4. **Be usable from a chair, with a remote, by anyone.** Large, simple, predictable,
   forgiving. Voice is an enhancement, never a requirement.
5. **Close the loop.** What the user does is recorded, reflected back, and used to make
   tomorrow slightly better tailored.

---

## 4. Problem Statement

### 4.1 The care-companion problem

A person two months past a heart attack and a stroke is medically stable but is running a
demanding daily protocol they did not design and cannot easily hold in working memory.
Concretely, on a single ordinary day they may need to answer:

- Which medicine is taken *before* breakfast, and which *after*?
- Which medicine is taken at night, and is it with food or not?
- What exercise was prescribed, how long, how many repetitions, and at what time of day?
- What were the meal instructions — what to include, what to limit, what to avoid?
- What precautions did the doctor give about exertion, lifting, heat, or being alone?
- Is there a test due this week? When is the next checkup?
- What have I already done today, and what have I missed?

**Why this is hard:**

- **Fragmentation.** The answers live across a discharge summary, two prescriptions, a
  lab report, an exercise handout and a verbal instruction that was never written down.
- **Format mismatch.** The information is in dense clinical prose and tables, designed for
  a clinician's eye, not for a recovering patient at a moment of decision.
- **Cognitive load after a cardiac or neurological event.** Fatigue and reduced
  concentration are common; a stroke may affect memory, attention or reading endurance.
  This is precisely the population least well served by dense text.
- **Isolation.** The organizing work often falls on a family member who is not present
  during the working day.
- **Existing tools fit badly.** Patient-portal apps and pill-reminder apps assume a
  confident smartphone user, small text, typing, and a person who will do data entry.
  Hospital dashboards assume a clinician. Neither fits a recovering person alone at home.

**The gap:** there is no calm, large-format, low-effort surface that takes the
*information the clinician already provided* and turns it into *what to do now*.

### 4.2 The wellness problem

A busy, generally healthy person wants to stay active, mobile and consistent. Their
constraint is not willingness — it is time, decision fatigue and guidance. In a 10–20
minute window before work, the cost of *choosing* a routine, sequencing it sensibly and
timing it is high enough that the session often does not happen. Video libraries force a
browse-and-scrub interaction that is hostile to a remote and to a fixed time budget.
Generic apps offer either rigid programmes or an overwhelming catalogue.

**The gap:** there is no way to simply state the constraint — *"I have 15 minutes, wake me
up"* — and immediately be guided through an appropriately structured session on the screen
already in front of you.

### 4.3 Why Fire TV specifically

- **Legibility and reach.** A large display read comfortably from a chair, which matters
  for older users, recovering users, and anyone without reading glasses to hand.
- **Interaction simplicity.** Four directions and Select. No small targets, no gestures,
  no typing-first interaction.
- **Ambient presence in routine.** The TV is already part of morning and evening rhythm,
  which is exactly when medication and exercise events cluster.
- **Shared-household reality.** It is naturally a family surface, which is an opportunity
  for caregiver support and a genuine privacy obligation (Section 27).
- **Room-scale guidance.** For exercise, a large screen at distance is the *correct* form
  factor — better than a phone propped against a wall.

### 4.4 What is explicitly not the problem being solved

This product does not attempt to determine what care a person needs, to detect
deterioration, to triage symptoms, or to replace any part of the clinical relationship.
Those are different problems requiring clinical validation and regulatory standing, and
they are out of scope (Section 32).

---

## 5. Target Users

### 5.1 Primary personas

#### Persona A — "Ramesh", the Care User (primary)

- 62, retired, two months post myocardial infarction and ischaemic stroke.
- Medically stable, living at home, alone on weekdays while family works.
- Following a doctor-provided routine: multiple medications timed around meals,
  prescribed graded exercise, dietary instructions, activity precautions, weekly checkup,
  periodic blood tests.
- Comfortable with a TV remote. Finds a smartphone small and fiddly; reads long text
  slowly and tires.
- Some post-event fatigue and reduced concentration. Occasionally uncertain whether he has
  already taken a dose.
- **Wants:** to not get it wrong, and to not have to ask his family the same question twice.
- **Needs from the product:** an unambiguous "what now", a clear record of what is done,
  the doctor's own words available in plain language, and reassurance that nothing is
  being invented.
- **Success feels like:** finishing a day knowing the routine was followed.

#### Persona B — "Priya", the Wellness User (primary)

- 34, full-time job, commutes, no chronic condition.
- Intends to be active; consistency collapses under time pressure.
- Has a 10–20 minute window in the morning and sometimes a short evening window.
- Owns a Fire TV Stick and uses it daily.
- **Wants:** to be told exactly what to do for the next 15 minutes and be done.
- **Needs from the product:** a single spoken or selected request, an immediately sensible
  routine, step-by-step guidance with timing, and a sense of streak and progress.
- **Success feels like:** a session completed before leaving the house, most days.

#### Persona C — "Anjali", the Both User (primary)

- 48, manages a controlled long-term condition with a doctor-provided routine, and also
  actively wants general fitness and mobility work.
- Needs the care surface and the wellness surface in one profile, without the care
  workflow dominating the experience or the fitness workflow trivializing the care plan.
- **Needs from the product:** a single day view that holds both kinds of activity, and a
  product that does not force her into either a purely medical or purely fitness mode.

### 5.2 Secondary personas

#### Persona D — "Meera", the Caregiver / family member (secondary; supporting role)

- 36, daughter of Persona A, lives in the same house or visits.
- Realistically the person who will do the initial setup: adding documents, confirming
  what the system extracted, and checking in on adherence.
- **Needs:** a trustworthy review step where she can verify and correct extracted
  information; a readable summary of how the week went.
- **Note:** the caregiver is a *supporting role in the MVP* (setup and confirmation on the
  TV). A dedicated remote caregiver experience is future scope (`FUT-` items, Section 31).

#### Persona E — The clinician (out of band; not a user of this product)

- Provides the documents and instructions that the product organizes.
- **Is not a user of the application** and has no interface in it. The product must be
  safe and honest enough that a clinician would not object to what it shows the patient,
  but building clinician-facing tooling is out of scope.

### 5.3 Accessibility profile of the user base

Because the care use case deliberately targets people recovering from cardiac and
neurological events, the following are treated as baseline design constraints, not
optional accommodations:

- Reduced visual acuity; reading at distance without correction.
- Reduced reading endurance and concentration; possible post-stroke attention or
  language effects.
- Reduced fine motor control; imprecise remote presses, accidental repeats.
- Low technical confidence; high sensitivity to feeling lost or to irreversible mistakes.
- Possible hearing impairment — audio must never be the sole channel for any information.

`PROD-005` The product **MUST** be fully operable and fully comprehensible by a user with
the profile above, using only the D-pad, Select and Back, with no voice and no typing
beyond what Section 14 permits.

### 5.4 Explicit non-users

- Clinicians using this as a clinical tool.
- Hospitals or health systems deploying it as an enterprise product.
- Athletes seeking performance training or programming.
- Anyone in an emergency or acute situation. The product is not an emergency tool
  (`SAFE-014`).

---

## 6. Core User Situations

### 6.1 Situation 1 — Health / Care Companion

**Context.** The user has already received care instructions from a healthcare
professional. The product's job begins *after* the clinical decision has been made. It
never participates in making it.

**Inputs the product may receive** (`PROD-010`): medical reports; prescriptions; exercise
instructions; diet and meal instructions; precautions; follow-up instructions; test
results; other care-related documents.

**What the product does with them** (`PROD-011`): extracts relevant information, proposes
it as structured items for human confirmation, and — once confirmed — organizes it into a
simple daily care view and a dashboard.

**Structured information the product may hold** (`PROD-012`):

- relevant health information
- recorded health measurements
- medication instructions
- prescribed activities and exercises
- meal instructions
- precautions
- appointments and checkups
- follow-up information
- other care-plan information

**What the user must be able to understand at a glance** (`PROD-013`):

- what needs to be done now
- what is scheduled next
- what has already been completed
- relevant available health information
- today's care routine
- upcoming tasks

**The non-negotiable boundary.** Everything in this situation is *organization and
presentation of information a clinician provided*. The product adds structure, timing,
plain-language explanation and completion tracking. It adds no clinical content. See
Sections 18 and 19.

### 6.2 Situation 2 — Busy / Healthy User

**Context.** The user has time pressure and wants to be active, mobile, fit and
consistent, with minimal decision overhead.

**The canonical interaction** (`PROD-020`): the user expresses a request in natural
language — *"I have 10–20 minutes before work. Give me a quick workout that will help me
kick-start my day."*

**What the product must understand** (`PROD-021`): available time; goal; preferences;
relevant user context.

**What the product produces** (`PROD-022`): an appropriate wellness / fitness routine,
generated or selected, that fits the stated time budget.

**Illustrative 15-minute routine** (from the product definition; illustrative structure,
not a fixed catalogue):

| Duration | Segment |
|---|---|
| 2 min | Warm-up |
| 5 min | Mobility |
| 5 min | Light exercise |
| 3 min | Cooldown / breathing |

**Guided execution** (`PROD-023`): the TV guides the user step by step. The screen may
show current activity, duration or repetitions, instructions, progress, next activity, and
completion.

**Closing the loop** (`PROD-024`): on completion the activity is recorded and reflected in
the user's progress.

### 6.3 Where the two situations meet

A **Both** user holds care items and wellness items in one day view. The rules that keep
this coherent:

`PROD-030` Care items and wellness items **MUST** be visually and structurally
distinguishable at all times, because they have different provenance and different safety
rules. A confirmed prescribed exercise is clinical instruction; an AI-generated mobility
routine is not.

`PROD-031` The product **MUST NOT** force a Wellness User through any care/medical
workflow, and **MUST NOT** restrict a Care User to a fitness-only experience.

`SAFE-031` AI-generated wellness routines **MUST NOT** be presented as, merged into, or
substituted for prescribed exercise. Where a user has confirmed activity precautions, the
product **MUST** surface those precautions before a generated wellness session (see
`SAFE-032`, Section 18).

---

## 7. Product Goals

Goals are grouped and each carries a verification method so that "done" is testable.

### G1 — Make the day unambiguous (Care)

| ID | Goal | Verified by |
|---|---|---|
| `PROD-100` | A Care User can answer "what do I need to do right now?" within **5 seconds** of the Today screen appearing, without navigating. | Timed walkthrough on device with the seeded care persona. |
| `PROD-101` | A Care User can see what is next and what is already completed today without leaving the Today screen. | Screen inspection against Section 14 requirements. |
| `PROD-102` | Every care item shown traces to a confirmed source with a visible date. | Spec review of every card type; no card may render without provenance. |

### G2 — Turn documents into a usable plan (Care)

| ID | Goal | Verified by |
|---|---|---|
| `PROD-110` | Doctor-provided documents can be ingested and their relevant content proposed as structured care-plan items. | End-to-end run on the synthetic document set. |
| `PROD-111` | No extracted item affects the user's plan until a human has confirmed it. | State-machine review (Section 19) and negative test. |
| `PROD-112` | Medication instruction text is preserved as transcribed, never paraphrased in a way that changes meaning, and never recomputed. | Diff of rendered dose strings against source documents. |

### G3 — Remove friction from being active (Wellness)

| ID | Goal | Verified by |
|---|---|---|
| `PROD-120` | From the Today screen, a Wellness User can start an appropriate time-boxed session in **no more than 3 remote actions** when using a preset, or one natural-language request where voice or quick-entry is available. | Remote-press count on device. |
| `PROD-121` | A generated routine's total duration matches the requested time budget within a stated tolerance. | Automated check of generated routine durations. |
| `PROD-122` | A user can complete a guided session end-to-end without touching the remote mid-session. | Hands-free run-through on device. |

### G4 — Close the loop (Both)

| ID | Goal | Verified by |
|---|---|---|
| `PROD-130` | Every completed activity or acknowledged care task is recorded and visible in progress. | Complete an item; confirm it appears in Progress and the Daily Summary. |
| `PROD-131` | A Daily Summary is available that separates recorded facts, historical information, user activity, and AI interpretation. | Inspection of summary output against Section 24. |

### G5 — Earn trust (Both)

| ID | Goal | Verified by |
|---|---|---|
| `SAFE-140` | Zero instances of invented clinical content, invented doctor instruction, or invented health values across the full demo path. | Adversarial review of every AI output surface (Section 18). |
| `SAFE-141` | AI-generated content is unambiguously labelled and never visually equivalent to confirmed clinical information. | UI review of all AI surfaces. |
| `PRIV-142` | No real patient data and no secrets exist anywhere in the repository. | Repository scan before submission. |

### G6 — Be a genuine TV product (Both)

| ID | Goal | Verified by |
|---|---|---|
| `PROD-150` | Every interactive element is reachable and operable with the D-pad, with a clearly visible focus state. | Full D-pad traversal of every screen. |
| `PROD-151` | The application is fully usable with voice disabled. | Complete both journeys with no voice input. |
| `PROD-152` | Layout respects the Fire TV safe zone and minimum type sizes (Section 12). | Overlay check at 1080p. |

### G7 — Be demonstrable (Hackathon)

| ID | Goal | Verified by |
|---|---|---|
| `PROD-160` | Both core journeys are demonstrable, on a real Fire TV device or the official Fire TV / Vega simulator, inside a sub-3-minute video. | Rehearsed demo recording (Section 34). |

---

## 8. Non-Goals

Non-goals are things the product deliberately does not try to be. They differ from
Out-of-Scope (Section 32), which lists functionality the system will not perform.

`PROD-200` **Not a clinical system.** It is not a hospital dashboard, EHR, clinician tool,
or any part of a documented care record. Nothing in it is authoritative for clinical use.

`PROD-201` **Not a medical device.** It performs no measurement, no monitoring, no
detection, no analysis intended to inform a clinical decision. It is an organization,
reminder and guidance aid for information the user already holds.

`PROD-202` **Not a general-purpose chatbot.** Natural language is an input method for
bounded tasks. The product does not offer open-domain conversation and does not answer
questions outside its defined scope (Section 17.5).

`PROD-203` **Not a workout-video application.** The value is in the structured, timed,
guided routine adapted to the user's constraint — not in a catalogue of videos to browse.

`PROD-204` **Not an enterprise or multi-tenant healthcare platform.** No organizations, no
clinician accounts, no billing, no practice management.

`PROD-205` **Not a data-collection product.** It does not exist to accumulate health data.
It holds the minimum necessary to serve the user (`PRIV-601`).

`PROD-206` **Not a social or competitive product.** No feeds, sharing, leaderboards,
followers or challenges.

`PROD-207` **Not an entertainment application.** No media catalogue, no content
discovery, no unrelated streaming features.

`PROD-208` **Not a phone or web application with a TV skin.** Fire TV is the primary
design target, not a porting destination (`PROD-400`).

`PROD-209` **Not a replacement for the caregiver or the clinician.** It supports them.

---

## 9. Product Pillars

The four pillars are the product's conceptual structure. They are fixed. They **MUST NOT**
be replaced with a different product concept.

### Pillar 1 — ASSIST (healthcare / care routine support)

Helping a person follow the care routine a clinician gave them.

**Scope:** provided health information; doctor-provided instructions; medication
instructions; prescribed exercises; meal instructions; precautions; reminders; daily care
organization.

**Governing rule:** ASSIST **organizes and presents**. It never originates clinical
content. Every element traces to a confirmed source (`SAFE-500`).

### Pillar 2 — GUIDE (fitness / wellness support)

Helping a person be active within their real constraints.

**Scope:** fitness; wellness; quick workouts; stretching; mobility; breathing;
relaxation; time-based routines; goal-based routines.

**Governing rule:** GUIDE **may generate content**, because general wellness movement is
not clinical instruction. It operates within confirmed precautions and within a
conservative safety envelope (`SAFE-032`, `SAFE-033`).

### Pillar 3 — PROGRESS

Reflecting back what the person actually did.

**Scope:** completed activities; routine completion; history; daily summaries; wellness
progress; relevant available health information.

**Governing rule:** PROGRESS reports **behaviour and records**. It **MUST NOT** infer
clinical improvement or deterioration (`SAFE-703`).

### Pillar 4 — AI CORE

The intelligence layer serving the other three.

**Scope:** natural-language understanding; organization; personalization; routine
generation and selection; summarization; progress insights.

**Governing rule:** AI CORE is bounded by Section 18 without exception. In the ASSIST
domain it is a **transformer of existing information**, never a source. In the GUIDE
domain it is a **generator within a safety envelope**.

### Pillar interaction

```
                         ┌─────────────┐
                         │   AI CORE   │
                         └──────┬──────┘
             organizes /       │       generates /
             summarizes /      │       personalizes
             explains          │
          ┌──────────────┬─────┴──────┬──────────────┐
          ▼              ▼            ▼              ▼
     ┌─────────┐   ┌─────────┐        │        ┌──────────┐
     │ ASSIST  │   │  GUIDE  │        │        │ PROGRESS │
     │ (care)  │   │(wellness)│       │        │          │
     └────┬────┘   └────┬────┘        │        └─────▲────┘
          │             │             │              │
          └─────────────┴─── completion events ──────┘
                                                     │
                            insights / summaries ────┘
```

---

## 10. Detailed User Journeys

Journeys are written as the user experiences them. Screen names refer to Section 13.

### Journey 1 — Care User: first-time setup (with caregiver present)

**Actors:** Persona A (Ramesh) and Persona D (Meera). **Precondition:** app installed;
doctor-provided documents available.

1. **Launch → Profile Select.** The app opens to profile selection. Meera creates a
   profile for Ramesh and chooses the **Care** user context. The product asks which of the
   three contexts applies — Care, Wellness, or Both — and explains each in one line.
2. **Care-team and emergency information (optional).** Meera may enter the doctor's name
   and a contact number to display later. This is stored as user-entered contact
   information only; the product performs no assessment against it (`SAFE-014`).
3. **Add documents.** Meera adds the doctor-provided documents. *Document intake is not
   performed by typing on the TV* (`PROD-410`); the intake mechanism is an architecture
   decision (Section 29, `TECH-905`). On the TV she sees each document arrive with its
   name, type and date.
4. **Extraction.** The product processes each document and proposes structured items —
   medications, exercises, meal instructions, precautions, appointments, measurements —
   each shown with the document it came from, the date, and the source text it was drawn
   from. All items are in the **Needs Review** state and **none of them affect the plan
   yet** (`SAFE-501`).
5. **Review and confirm.** For each proposed item Meera sees the extracted structure
   beside the original source text and chooses **Confirm**, **Edit**, or **Discard**. Dose
   strings are shown exactly as transcribed. Anything the system could not read
   confidently is flagged as **Unclear — needs a person** rather than guessed
   (`SAFE-503`). Nothing is auto-confirmed (`SAFE-501`).
6. **Plan appears.** Confirmed items populate the care plan and the day. Meera sees a
   preview of Ramesh's Today screen and can adjust timing labels (e.g. which meal a dose
   attaches to) — *timing labels only, never dose content* (`SAFE-504`).
7. **Handover.** The product shows Ramesh a short orientation: this is Today, this is what
   to press, this is how to mark something done, this is how to get back. Three screens,
   large type, skippable and repeatable from Settings.

**Success:** Ramesh's confirmed care plan drives a Today screen he understands, and he has
been shown how to use it.

### Journey 2 — Care User: an ordinary day (the core journey)

**Actor:** Persona A, alone at home.

1. **08:10 — Launch.** Ramesh turns on the TV and opens the app. Profile Select appears;
   his profile is first and focused. He presses Select.
2. **Today.** The screen leads with a single **Now** card: *"Before breakfast — Tablet A,
   1 tablet."* Underneath, in smaller but still large type, the dose line exactly as
   transcribed, and a quiet source line: *"From Prescription, 12 Aug 2026."* Below the Now
   card: **Next** (the following item with its time) and **Done** (a compact count with
   what has been completed).
3. **Acting on the item.** He presses Select on the Now card. A confirmation view shows
   the item, its instruction, and one primary action: **Mark as taken**. Secondary
   actions: **Not now** and **Why this?**.
4. **"Why this?"** He chooses it. The product shows a plain-language explanation of *the
   instruction as given* — what the document says about this medicine and its timing —
   with the source and date, and an explicit note that this is a simplification of the
   document and that questions about the medicine itself go to his doctor (`SAFE-511`).
   The explanation **MUST NOT** add indications, effects, warnings or advice that are not
   in the confirmed source.
5. **Completion.** He marks it taken. The item moves to Done, the Now card advances to the
   next item, and a brief, calm acknowledgement is shown. No celebration animation, no
   sound that could startle.
6. **Mid-morning — prescribed exercise.** The Now card becomes the prescribed exercise, as
   confirmed from the exercise handout, with its instructions and its source. It is
   visibly marked as **prescribed** (`PROD-030`), distinct from wellness content. If a
   confirmed precaution applies, the precaution is shown before the activity starts
   (`SAFE-032`).
7. **Precaution and meal cards.** Meal instructions and precautions appear as reference
   cards in Today — informational, not tasks to be completed, unless the source expresses
   them as a timed instruction.
8. **Missed item.** At 14:00 the after-lunch dose has not been marked. The item moves into
   an **Overdue** presentation on Today: clearly visible, factual, never alarming, never
   scolding. The product states only that it is not marked as done. It **MUST NOT**
   advise taking it late, skipping it, or doubling it — that is a dose decision
   (`SAFE-505`). It **MAY** offer **Mark as taken**, **Mark as skipped**, or a
   plain-language pointer to contact the care team if he is unsure.
9. **Checking his information.** He navigates to **Health Info** and sees his recorded
   measurements. Each carries its value, its unit, its observation date, and its source.
   A reading from the discharge report is labelled clearly as a past recorded value from
   that report and **is not** presented as a current measurement (`SAFE-520`).
10. **Evening — Daily Summary.** Today offers **See today's summary**. It shows: what was
    completed and what was not (recorded facts); relevant available recorded information
    with dates (historical information); his activity; and, in a visually separated
    labelled block, a short AI-written plain-language summary of his day and tomorrow's
    plan. The AI block **MUST NOT** claim medical improvement (`SAFE-703`).

**Success:** Ramesh followed his routine, understood it, marked what he did, and finished
the day with a truthful picture of it.

### Journey 3 — Wellness User: the 15-minute morning (the core journey)

**Actor:** Persona B (Priya), 15 minutes before leaving.

1. **Launch → Profile Select → Today.** Her Today screen leads with wellness: a **Start a
   session** area offering time presets — **10 min**, **15 min**, **20 min** — plus
   **Ask for something specific**, alongside her current streak.
2. **The request.** Two equivalent paths, and **both must exist** (`PROD-151`):
   - **Voice, where technically supported** — she states her request in natural language.
   - **Without voice (always available)** — she selects a time preset and then, if she
     wants, a goal chip: *Wake up / Loosen up / Calm down / Move more*. Free-text entry is
     available but is never the only path and is never required (`PROD-410`).
3. **Routine proposed.** Within a short, honest loading state the product shows the
   proposed routine as a readable plan — total duration and each segment with its time.
   Illustratively: 2 min warm-up, 5 min mobility, 5 min light exercise, 3 min cooldown and
   breathing. Total shown explicitly and matching her budget (`PROD-121`). Actions:
   **Start**, **Change something**, **Back**.
4. **Guided session.** She presses Start and puts the remote down. For each step the
   screen shows the current activity prominently; duration or repetitions; brief
   instructions in short lines; progress through the session; and a preview of the next
   activity. Transitions are automatic with a clear countdown. The remote is not needed
   again (`PROD-122`). **Pause** and **Back** remain available at all times, and a paused
   session must be resumable.
5. **Completion.** A completion view states what she did and how long it took, and records
   it. Progress and streak update (`PROD-024`).
6. **Progress.** Later she opens **Progress** and sees her recent sessions, completion
   pattern and streak, plus a short labelled AI insight about consistency — behavioural
   only, never clinical (`SAFE-703`).

**Success:** one request, an appropriate session, guided hands-free, recorded.

### Journey 4 — Both User: one day, two kinds of activity

**Actor:** Persona C (Anjali).

1. **Today** holds both: confirmed care items (medication timing, a prescribed activity, a
   meal instruction) and a wellness slot.
2. Care and wellness items are **visually distinct** with different labelling, so that
   provenance is never ambiguous (`PROD-030`).
3. She starts a wellness session. Because she has a confirmed activity precaution, the
   product shows that precaution — in the source's own terms with its date — before the
   session begins, and offers a gentler option (`SAFE-032`). It **MUST NOT** decide for
   her whether the session is medically appropriate (`SAFE-033`).
4. Her Daily Summary reports both streams and keeps recorded facts, historical
   information, activity, and AI interpretation in separate labelled regions.

**Success:** one coherent day; neither workflow is forced on her; provenance stays clear.

### Journey 5 — Shared TV: profile switching and privacy

**Actors:** Personas A, B and a household member with no profile.

1. The app **always** opens to Profile Select and never auto-enters a profile holding
   health information (`PRIV-700`).
2. A profile containing care information **MAY** be protected by a simple numeric PIN
   entered with the D-pad (`PRIV-701`). PIN protection is optional and must be
   explainable in one sentence.
3. On Profile Select, profiles show a name and avatar only. No health information, no
   condition, no medication and no adherence state is visible before entry
   (`PRIV-702`).
4. Switching profiles is always available from a consistent location and clears the
   previous profile's health information from view immediately (`PRIV-703`).
5. If read-aloud or any spoken output is present, the product **MUST NOT** speak sensitive
   health information without the profile owner having enabled it (`PRIV-704`).

**Success:** health information does not leak to the room or to other household members.

### Journey 6 — Care User: a new document arrives

1. A caregiver adds a new document (e.g. a revised prescription after a checkup).
2. The product extracts and proposes items in **Needs Review**. Existing confirmed items
   are **not** silently modified or replaced (`SAFE-506`).
3. Where a proposed item appears to relate to an existing confirmed item, the product
   presents them side by side with both dates and asks a human to decide. The product
   **MUST NOT** itself decide that a newer document supersedes an older instruction
   (`SAFE-506`).
4. Only after confirmation does the plan change. A change log records what changed, when,
   and from which document.

### Journey 7 — Degraded paths (must be designed, not left to chance)

| Condition | Required behaviour |
|---|---|
| No network / AI unavailable | Confirmed care plan, Today, completion tracking and progress **MUST** remain usable. AI-dependent features degrade to preset routines and a clear, non-alarming explanation (`TECH-930`). |
| Document unreadable or low confidence | Flag as **Unclear — needs a person**. Never guess (`SAFE-503`). |
| Voice unavailable or misrecognized | Every voice path has an equivalent D-pad path (`PROD-151`). |
| User presses Back repeatedly | Back always moves one predictable level toward Today and never exits mid-session without confirmation (`PROD-430`). |
| Session interrupted | Resumable; partial completion recorded honestly as partial. |
| Empty state (no documents yet) | Today explains plainly what to add and how, and offers wellness immediately so the app is never useless. |

---

## 11. Core Features

Features are grouped by pillar. The **Phase** column is authoritative for scope: **MVP**
means required for the hackathon submission; **P2** / **P3** are future phases that remain
part of the product vision (Section 31). Nothing here is deleted for being complex.

### 11.1 ASSIST — care companion

| ID | Feature | Description | Phase |
|---|---|---|---|
| `F-A01` | Document intake | Accept doctor-provided documents (reports, prescriptions, exercise and diet instructions, precautions, follow-ups, test results). Intake mechanism decided in architecture; must not require TV typing. | MVP |
| `F-A02` | Information extraction | Extract relevant information from documents into proposed structured items with source references and confidence. | MVP |
| `F-A03` | Human review & confirmation | Mandatory human confirmation of every extracted item before it affects the plan, with source text shown beside the proposal. | MVP |
| `F-A04` | Medication instruction display | Show confirmed medication instructions with dose text preserved as transcribed, timing label, and source + date. | MVP |
| `F-A05` | Prescribed exercise display | Show confirmed prescribed activities with their instructions, clearly marked as prescribed. | MVP |
| `F-A06` | Meal instruction display | Show confirmed dietary instructions as reference information. | MVP |
| `F-A07` | Precautions display | Show confirmed precautions, and surface relevant ones before activity. | MVP |
| `F-A08` | Appointments & follow-ups | Show confirmed checkups, tests and follow-up instructions with dates. | MVP |
| `F-A09` | Health Info dashboard | Show recorded measurements with value, unit, observation date, source and context. | MVP |
| `F-A10` | Plain-language explanation | Explain a confirmed instruction in simpler words without changing its meaning or adding content. | MVP |
| `F-A11` | Care task completion | Mark care items as done / skipped, with timestamp. | MVP |
| `F-A12` | Document change handling | New documents propose changes for human decision; never silently supersede. | MVP (basic) / P2 (rich diff) |
| `F-A13` | Care-team & emergency info card | Display user-entered care-team and emergency contact details. No assessment, no triage. | MVP |
| `F-A14` | Caregiver review on TV | Caregiver performs setup and confirmation on the TV. | MVP |
| `F-A15` | Remote caregiver companion | Caregiver reviews/confirms and sees adherence from a phone. | P2 |
| `F-A16` | Manual health measurement entry | User or caregiver records a measurement with date and source = self-reported. | P2 |
| `F-A17` | Multi-document care-plan timeline | Full versioned history of how the care plan evolved across documents. | P3 |

### 11.2 GUIDE — wellness companion

| ID | Feature | Description | Phase |
|---|---|---|---|
| `F-G01` | Natural-language request | Understand a stated request covering available time, goal, preferences and context. | MVP |
| `F-G02` | Non-voice request path | Time presets plus goal chips, fully equivalent to the voice path. | MVP |
| `F-G03` | Routine generation / selection | Produce a segmented routine matching the time budget. | MVP |
| `F-G04` | Routine preview | Show the plan and total duration before starting, with the option to change it. | MVP |
| `F-G05` | Guided session player | Step-by-step guidance: current activity, duration/reps, instructions, progress, next activity, completion. Hands-free. | MVP |
| `F-G06` | Pause / resume / exit | Available throughout; resumable; honest partial recording. | MVP |
| `F-G07` | Breathing & relaxation routines | Timed breathing and relaxation as first-class routine types. | MVP |
| `F-G08` | Stretching & mobility routines | First-class routine types. | MVP |
| `F-G09` | Precaution-aware gating | Surface confirmed precautions before a generated session; offer a gentler option. | MVP |
| `F-G10` | Preference memory | Remember stated preferences and avoided movements; apply to future routines. | MVP (basic) / P2 (rich) |
| `F-G11` | Illustrated exercise guidance | Visual demonstration of each movement. | P2 |
| `F-G12` | Spoken coaching cues | Timed audio cues, always paired with on-screen text. | P2 |
| `F-G13` | Camera-based form feedback | Computer-vision form/rep feedback via a TV camera where hardware permits. | P3 |

### 11.3 PROGRESS

| ID | Feature | Description | Phase |
|---|---|---|---|
| `F-P01` | Activity log | Record every completed / skipped / partial activity with timestamp. | MVP |
| `F-P02` | Routine completion view | Today's and recent days' completion at a glance. | MVP |
| `F-P03` | Streak & consistency | Simple consistency indicators. | MVP |
| `F-P04` | Daily Health & Wellness Summary | Section 24, with strict fact/interpretation separation. | MVP |
| `F-P05` | Behavioural insights | Labelled AI insights about behaviour and consistency only. | MVP |
| `F-P06` | Recorded-information comparison | Compare recorded values across dates, clearly as records, never as clinical conclusions. | MVP (minimal) / P2 |
| `F-P07` | Weekly summary | Week-level rollup. | P2 |
| `F-P08` | Exportable summary | Printable/shareable summary the user may choose to show their clinician. | P2 |

### 11.4 AI CORE

| ID | Feature | Description | Phase |
|---|---|---|---|
| `F-AI01` | Intent understanding | Map a natural-language request to a supported in-app task. | MVP |
| `F-AI02` | Document information structuring | Convert document content into proposed structured items with source spans and confidence. | MVP |
| `F-AI03` | Simplification / explanation | Restate confirmed instructions in plain language, meaning-preserving, no additions. | MVP |
| `F-AI04` | Routine generation | Generate wellness routines within the safety envelope. | MVP |
| `F-AI05` | Personalization | Adapt routines to time, goal, preferences and history. | MVP |
| `F-AI06` | Summarization | Produce the AI portion of the Daily Summary. | MVP |
| `F-AI07` | Bounded Q&A | Answer questions about the user's own confirmed plan and app usage, within Section 18. Refuse and redirect otherwise. | MVP |
| `F-AI08` | Guardrail layer | Enforce refusal and separation rules on every AI output before display. | MVP |
| `F-AI09` | Read-aloud (TTS) | Read non-sensitive content aloud; opt-in for sensitive content. | P2 |
| `F-AI10` | Multi-language support | Plan and guidance in additional languages. | P3 |

### 11.5 Platform & cross-cutting

| ID | Feature | Description | Phase |
|---|---|---|---|
| `F-X01` | Profile select on launch | Always open to Profile Select. | MVP |
| `F-X02` | User-context selection | Care / Wellness / Both, changeable later. | MVP |
| `F-X03` | Optional profile PIN | D-pad numeric PIN for profiles holding care information. | MVP |
| `F-X04` | Profile switching | Available from a consistent location; clears prior view immediately. | MVP |
| `F-X05` | Accessibility baseline | Safe zone, type sizes, contrast, focus visibility, content descriptions (Section 12). | MVP |
| `F-X06` | Offline resilience | Core care plan and tracking work without network. | MVP |
| `F-X07` | Demo data labelling | All seeded/synthetic data visibly identified as demo data. | MVP |
| `F-X08` | Settings | Profile, context, PIN, spoken-output preference, orientation replay, data reset. | MVP |
| `F-X09` | In-app reminder surfacing | Due/overdue surfacing while the app is open (Section 21). | MVP |
| `F-X10` | System-level notifications | Notifications when the app is not in the foreground. | P2 (feasibility-gated) |

---

## 12. Fire TV Experience

Fire TV is the **primary platform and primary product experience** (`PROD-400`). This
section is binding on all UI work.

### 12.1 Non-negotiable platform stance

`PROD-400` Fire TV is the primary platform. The product **MUST** be designed for a TV /
10-foot experience from the start.

`PROD-401` The product **MUST NOT** be a desktop or web application placed on a TV. Any
design that assumes a pointer, hover, scroll wheel, small text, dense tables, or
typing-first interaction is a defect.

`PROD-402` The primary interaction model is the **Fire TV remote**: D-pad (Left / Right /
Up / Down), **Select**, and **Back**. Voice is used only where technically supported and
appropriate.

`PROD-403` The product **MUST** remain **fully usable without voice**.

### 12.2 Verified Fire TV design requirements (category A — official)

The following are taken from official Amazon Fire TV developer documentation and are
treated as hard constraints.

`HACK-410` **Safe zone / overscan.** Avoid placing UI elements within the outer **5%** of
any screen edge; focused items and text must remain fully within the inner **90%** safe
zone.
> Official: *"avoid placing any of your app's UI elements within the outer 5% of any edge on the screen"* — Fire TV Design and User Experience Guidelines.

`HACK-411` **Minimum body text size.** Body text **MUST** be at least **14sp**
(approximately 19px at 720p, 28px at 1080p). Line spacing greater than desktop or tablet.
> Official: *"at least 14sp, which is approximately 19px on 720p, 28px on 1080p"* — Fire TV Display and Layout.

`HACK-412` **Reference resolution and density.** For 1080p: screen 1920×1080px, density
320dpi (xhdpi), output resolution 960×540dp ("large").

`HACK-413` **Focus indication.** The app **MUST** clearly indicate which on-screen element
currently has focus; selected elements should momentarily show a selected state.
> Official: *"Your app should clearly indicate which on-screen element currently has the focus."*

`HACK-414` **D-pad reachability.** Every actionable on-screen element **MUST** be reachable
with the D-pad, with a clear up-down and left-right orientation immediately apparent.
> Official: *"every actionable on-screen element should be reachable with the D-pad"*

`HACK-415` **Information density and colour.** Design for low information density; minimize
text; prefer less saturated colours, with cool colours (blue, purple, grey) working better
than warmer colours (red, orange).
> Official: *"Clear, Simple, and Visual"*, *"low information density"*, *"use less saturated colors"*.

`HACK-416` **Accessibility units.** Use **sp** for font sizes and **dp** for layout
spacing so content scales with user font settings.
> Official: Amazon Fire devices accessibility guidance.

`HACK-417` **Screen reader support.** Fire TV supports the **VoiceView** screen reader.
Provide meaningful content descriptions for images, icons and custom controls.
> Official: *"VoiceView won't be able to guess what a gear icon does; you have to tell it."*

**Note on `HACK-415` and health UI.** Official guidance prefers cool, less saturated
colours. This constrains — and improves — the health design: status must not be encoded in
saturated red/green alone. See `PROD-425`.

### 12.3 Product UX principles (category B)

From the product definition, binding:

`PROD-420` Large, readable typography.
`PROD-421` Large interactive elements.
`PROD-422` Clear focus states.
`PROD-423` Simple navigation.
`PROD-424` Minimal typing.
`PROD-425` Predictable remote navigation.
`PROD-426` Simple language.
`PROD-427` Low cognitive load.
`PROD-428` Suitable for older or less technically confident users.

Operationalized, and binding on implementation:

| ID | Requirement |
|---|---|
| `PROD-430` | **Predictable Back.** Back always moves exactly one level toward Today. From Today, Back requests exit with confirmation. Back **MUST NOT** exit a guided session without confirmation. |
| `PROD-431` | **One primary action per screen.** Each screen presents one clearly dominant action; secondary actions are visibly subordinate. |
| `PROD-432` | **Shallow hierarchy.** Any MVP destination is reachable from Today within **3** D-pad-plus-Select actions. |
| `PROD-433` | **No horizontal-plus-vertical mazes.** Avoid grids requiring 2-axis hunting for primary tasks. Primary flows are single-axis. |
| `PROD-434` | **Readable at distance.** Primary card text substantially larger than the `HACK-411` minimum; the minimum is a floor, not a target. |
| `PROD-435` | **Never encode meaning in colour alone.** Every status carries text and/or shape in addition to colour (`HACK-415`, colour-blindness, and TV colour variance). |
| `PROD-436` | **Plain language.** No clinical jargon in product chrome. Clinical terms appearing inside quoted source text are preserved verbatim and may be explained (`F-A10`). |
| `PROD-437` | **Forgiving input.** Tolerate repeated/accidental presses. Destructive actions require explicit confirmation. No time-limited prompts that penalize slow response. |
| `PROD-438` | **No startling output.** No sudden loud audio, no flashing, no aggressive animation. Calm transitions. |
| `PROD-439` | **Honest loading states.** AI operations show a clear, non-blocking, non-deceptive progress state, and a graceful timeout path. |
| `PROD-440` | **Focus is never lost.** After any state change, focus rests on a sensible, visible element. Never focus-nothing. |

### 12.4 Text entry

`PROD-410` The product **MUST NOT** require keyboard text entry on the TV for any core
journey. Specifically:

- **Document intake MUST NOT** require typing document content on the TV.
- **Wellness requests MUST** be completable via presets and chips alone.
- **PIN entry** is numeric via D-pad and is the only routinely expected typed input.
- Where free-text entry exists, it is always optional and always has a non-typing
  equivalent.

### 12.5 Voice — verified capability boundary

Research finding (category A/E boundary). Official Fire TV documentation describes
voice-enablement approaches oriented to media and navigation — the Video Skills Kit
(app launch, content search, transport controls, channel change), the Media Session API
(playback control), and In-App Voice Scrolling and Selection (which Amazon enables
per app on the back end after verification). **No official documentation was found
describing an API that lets an app capture arbitrary free-form voice input from the Fire
TV remote microphone for its own natural-language processing.**

Consequently:

`TECH-450` Free-form natural-language **voice** input on Fire TV **MUST NOT** be assumed
available. Its feasibility is an explicit Open Question (`OQ-05`) to be resolved in the
Architecture phase against current official documentation and the chosen platform target.

`PROD-451` Because of `TECH-450`, the natural-language capability (`F-G01`) **MUST** be
architected so that the *understanding* layer is independent of the *input channel*. The
same request handling serves voice input where available, and on-screen selection or
optional text entry where it is not.

`PROD-452` The demo and the product **MUST** both work end-to-end with the non-voice path
alone (`PROD-403`). Voice, if implemented, is demonstrated as an enhancement.

`TECH-453` Additional voice-adjacent avenues **MAY** be explored in the Architecture
phase — including platform speech facilities available to the chosen runtime, and the
hackathon's separate **Alexa+** surface — but none may become a dependency of a core
journey. Note that the hackathon requires a single primary track (`HACK-803`); Alexa+
work would be additive, not a substitute for the Fire TV requirement.

### 12.6 Reminder and always-on reality

`TECH-460` A television is **not** an always-on, always-foreground notification surface.
The product **MUST NOT** be specified as if the TV will reliably alert a user at a
medication time. Section 21 defines reminders accordingly: in-app due/overdue surfacing is
MVP; out-of-app notification is feasibility-gated future scope (`F-X10`).

---

## 13. Information Architecture

### 13.1 Top-level structure

```
Profile Select  (always the entry point)
│
├── [profile: optional PIN]
│
└── TODAY  ......................... home / default destination
    │
    ├── Now / Next / Done              (in-place on Today)
    ├── Item Detail                    (care item or activity)
    │   ├── Mark done / skipped
    │   └── Why this? (explanation)
    │
    ├── CARE PLAN                      (Care / Both only)
    │   ├── Medications
    │   ├── Prescribed activity
    │   ├── Meal instructions
    │   ├── Precautions
    │   └── Appointments & follow-ups
    │
    ├── HEALTH INFO                    (Care / Both only)
    │   └── Recorded measurements (with source + date)
    │
    ├── WELLNESS                       (all contexts)
    │   ├── Start a session (time presets + goal chips)
    │   ├── Ask for something specific (voice where available / optional text)
    │   ├── Routine Preview
    │   └── Guided Session Player → Session Complete
    │
    ├── PROGRESS
    │   ├── Recent activity
    │   ├── Consistency / streak
    │   └── Daily Summary
    │
    ├── DOCUMENTS                      (Care / Both only)
    │   ├── Document list
    │   └── Review & Confirm (Needs Review queue)
    │
    └── SETTINGS
        ├── Profile & user context
        ├── PIN
        ├── Spoken output preference
        ├── Orientation (replay)
        ├── Care-team & emergency info
        └── Demo data / reset
```

### 13.2 Navigation model

`PROD-500` **Today is home.** Today is the default destination after profile entry and the
convergence point of all navigation.

`PROD-501` **Single primary axis per screen.** Today is vertically ordered by priority
(Now → Next → shortcuts → Done). Within a row, movement is horizontal.

`PROD-502` **Sections are siblings, not a deep tree.** Care Plan, Health Info, Wellness,
Progress, Documents and Settings are all one level below Today.

`PROD-503` **Context-aware surfaces.** A Wellness User does not see Care Plan, Health Info
or Documents. A Care User sees wellness, because wellness is appropriate for them too
(`PROD-031`) — but never as a substitute for their care plan.

`PROD-504` **No modal dead ends.** Every screen has a visible way back, and Back always
works (`PROD-430`).

### 13.3 Content priority on Today

Ordered, and binding:

1. **Now** — the single most relevant current item. Largest element on screen.
2. **Next** — what follows, with its time.
3. **Overdue** — if present, surfaced at Now-level prominence, factual and non-alarming.
4. **Start a session** — wellness entry (prominence varies by user context).
5. **Done** — compact summary of completed items.
6. **Reference cards** — meal instructions, precautions, upcoming appointments.
7. **See today's summary** — entry to the Daily Summary.

`PROD-510` Today **MUST** be comprehensible without scrolling for the Now + Next + Overdue
tier. Lower-priority content may require vertical movement.

### 13.4 Card taxonomy

Every item rendered on Today or in Care Plan is one of these card types. Each type has
fixed provenance obligations.

| Card type | Pillar | Provenance obligation | Completable |
|---|---|---|---|
| Medication item | ASSIST | Confirmed source + document + date; dose text as transcribed | Yes (taken / skipped) |
| Prescribed activity | ASSIST | Confirmed source + document + date; marked **prescribed** | Yes |
| Meal instruction | ASSIST | Confirmed source + document + date | Reference (unless source is a timed instruction) |
| Precaution | ASSIST | Confirmed source + document + date | Reference |
| Appointment / follow-up | ASSIST | Confirmed source + document + date | Yes (attended / rescheduled) |
| Recorded measurement | ASSIST | Value, unit, observation date, source, context; never shown as current unless within a defined recency window | No |
| Wellness routine | GUIDE | Labelled **generated / wellness**; never labelled prescribed | Yes |
| AI insight / summary | AI CORE | Visually separated, explicitly labelled as AI-generated | No |
| Demo-data marker | Cross-cutting | Visible identification of synthetic data | n/a |

`SAFE-520` A recorded measurement **MUST NOT** be rendered as a current or live value. It
**MUST** always display its observation date, and historical values **MUST** be visually
distinguished from any current-state presentation.

`SAFE-521` A card **MUST NOT** render at all if its provenance obligations cannot be met.
Missing provenance is a blocking error, not a cosmetic one.

---

## 14. Screen & Navigation Requirements

Per-screen requirements. Every screen inherits Section 12.

### 14.1 Profile Select

| ID | Requirement |
|---|---|
| `PRIV-700` | The app **MUST** always open here and **MUST NOT** auto-enter a profile containing health information. |
| `PRIV-702` | Profiles display **name and avatar only**. No condition, medication, adherence or health state before entry. |
| `PROD-540` | Profiles are arranged on a single horizontal axis, large targets, first profile focused by default. |
| `PROD-541` | Includes **Add profile** and **Settings**. |
| `PRIV-701` | If a profile has a PIN, entry requires D-pad numeric PIN with a clear, non-punitive retry path. |

### 14.2 Today (home)

| ID | Requirement |
|---|---|
| `PROD-100` | The Now item is answerable within 5 seconds, without navigation. |
| `PROD-550` | Layout follows the Section 13.3 priority order exactly. |
| `PROD-551` | The Now card is the largest, highest-contrast element and is focused on arrival. |
| `PROD-552` | Every care item shows source and date at card level — not hidden behind a detail view (`PROD-102`). |
| `PROD-553` | Shows the current date and a simple day-progress indication. |
| `PROD-554` | Empty state (no confirmed items) explains what to add and offers wellness immediately. |
| `PROD-555` | Overdue items are factual and calm — never red-alert styling, never scolding language (`HACK-415`, `PROD-435`). |

### 14.3 Item Detail

| ID | Requirement |
|---|---|
| `PROD-560` | Shows the item, its instruction text, its source document and date. |
| `PROD-561` | Exactly one primary action (**Mark as taken** / **Start** / **Mark as attended**). |
| `PROD-562` | Secondary actions are visibly subordinate: **Not now**, **Mark as skipped**, **Why this?**. |
| `SAFE-505` | For medication items the product **MUST NOT** advise taking late, skipping, or adjusting. It may record, and may point to the care team. |
| `SAFE-511` | **Why this?** explains the confirmed instruction in plain language, preserves meaning, adds no clinical content, and states its source and that medicine questions go to the doctor. |

### 14.4 Care Plan

| ID | Requirement |
|---|---|
| `PROD-570` | Grouped by the categories in Section 13.1, each group reachable in one D-pad move from the section entry. |
| `PROD-571` | Every entry carries source document and date. |
| `PROD-572` | Read-oriented. Editing confirmed clinical content is restricted (Section 19.6) and never casual. |

### 14.5 Health Info

| ID | Requirement |
|---|---|
| `PROD-580` | Each measurement shows value, unit, observation date, source and context. |
| `SAFE-520` | Historical values are never presented as current. |
| `SAFE-581` | No value is displayed that was not confirmed or explicitly self-reported. **No interpolation, no estimation, no derived vitals** (`SAFE-502`). |
| `PROD-582` | Where a comparison across dates is shown, both dates are shown, and no clinical conclusion is drawn (`SAFE-703`). |

### 14.6 Wellness — request and preview

| ID | Requirement |
|---|---|
| `PROD-590` | Time presets (10 / 15 / 20 min) are reachable and startable within `PROD-120`'s action budget. |
| `PROD-591` | Goal chips are optional; a preset alone is sufficient to get a routine. |
| `PROD-592` | Voice entry, where supported, appears as an additional affordance — never as the only path (`PROD-403`). |
| `PROD-593` | Routine Preview lists every segment with its duration and shows the explicit total, matching the request (`PROD-121`). |
| `PROD-594` | Preview offers **Start**, **Change something**, **Back**. |
| `SAFE-032` | Where confirmed precautions apply, they are shown before Start, in the source's terms with its date, with a gentler alternative offered. |

### 14.7 Guided Session Player

| ID | Requirement |
|---|---|
| `PROD-600` | Shows current activity, duration or repetitions, brief instructions, session progress, and next activity. |
| `PROD-601` | Advances automatically with a clear visible countdown. No remote input required mid-session (`PROD-122`). |
| `PROD-602` | Instructions are short lines, readable at distance, never paragraphs. |
| `PROD-603` | **Pause**, **Resume** and **Exit** available at all times; Exit requires confirmation (`PROD-430`). |
| `PROD-604` | Audio, if present, is always accompanied by on-screen text (hearing-impairment baseline, Section 5.3). |
| `PROD-605` | Completion view states what was done and records it; partial completion is recorded honestly as partial. |
| `SAFE-606` | Guidance includes a standing, non-alarming instruction to stop if the user feels unwell, and **MUST NOT** evaluate or triage any symptom (`SAFE-014`). |

### 14.8 Progress

| ID | Requirement |
|---|---|
| `PROD-610` | Shows recent activity, completion pattern, and consistency/streak. |
| `PROD-611` | AI insights are visually separated and labelled (`SAFE-141`). |
| `SAFE-703` | Insights are behavioural only. No clinical improvement or deterioration claims. |

### 14.9 Documents & Review

| ID | Requirement |
|---|---|
| `PROD-620` | Document list shows name, type, date and review status. |
| `PROD-621` | The Review screen shows the proposed structured item beside the source text it came from. |
| `PROD-622` | Actions are **Confirm**, **Edit**, **Discard**, plus **Unclear — ask a person**. |
| `SAFE-501` | No item is auto-confirmed. Confirmation is always an explicit human action. |
| `SAFE-503` | Low-confidence or unreadable content is flagged, never guessed. |
| `PROD-623` | The review queue is navigable one item at a time with a visible position indicator ("3 of 11"). |

### 14.10 Settings

| ID | Requirement |
|---|---|
| `PROD-630` | Contains the Section 13.1 items, one screen deep, no nested sub-menus beyond one level. |
| `PROD-631` | Data reset requires explicit confirmation and states plainly what will be removed. |
| `PRIV-704` | Spoken-output preference for sensitive content is opt-in, defaulting to off. |

---

## 15. Health/Care Companion

This section specifies the ASSIST pillar in detail. It is governed by Sections 18 and 19.

### 15.1 What this component is

`PROD-700` The Health/Care Companion is an **organization and presentation layer over
information a healthcare professional provided**. Its value is structure, timing, plain
language and completion tracking. It contributes no clinical content of its own.

### 15.2 Care-plan item types

Each type, its required fields, and its hard rules.

#### Medication instruction

- **Required:** medicine name as written; dose text **as transcribed**; timing expression
  as given (e.g. "before breakfast", "after lunch", "at night"); source document; source
  date; confirmation state.
- **Optional:** with/without food if stated; duration if stated; notes if stated.
- **Rules:**
  - `SAFE-504` Dose text **MUST** be preserved as transcribed. The product **MUST NOT**
    recompute, convert units, split, combine, round, or normalize a dose.
  - `SAFE-505` The product **MUST NOT** advise on taking a missed dose, skipping, or
    changing anything. It records state and may point to the care team.
  - `SAFE-506` A new document **MUST NOT** silently supersede a confirmed medication item.
  - `SAFE-507` The product **MUST NOT** provide drug interaction, contraindication, side
    effect or substitution information that is not present in a confirmed source.

#### Prescribed activity / exercise

- **Required:** activity as described; duration/repetitions/frequency as given; timing if
  given; source document; source date; confirmation state; **prescribed** marker.
- **Rules:**
  - `SAFE-510` Prescribed activity **MUST** be visually distinguished from generated
    wellness content and **MUST NOT** be modified, progressed, intensified or substituted
    by the AI.
  - A prescribed activity **MAY** be guided using the Session Player's presentation
    mechanics, but its **content remains exactly as confirmed**.

#### Meal / dietary instruction

- **Required:** instruction text as given; scope (include / limit / avoid) if expressed;
  source document; source date; confirmation state.
- **Rules:**
  - `SAFE-512` The product **MUST NOT** generate meal plans, recipes, calorie targets,
    portion calculations or nutritional advice for a Care User beyond what a confirmed
    source states.

#### Precaution

- **Required:** precaution text as given; applicability if expressed; source; date;
  confirmation state.
- **Rules:**
  - `SAFE-032` Relevant confirmed precautions **MUST** be surfaced before related activity.
  - `SAFE-513` Precautions **MUST NOT** be summarized in a way that weakens or broadens
    them. Where shortened for display, the full confirmed text must remain accessible.

#### Appointment / checkup / test / follow-up

- **Required:** what; date/time or interval as given; source; date; confirmation state.
- **Rules:**
  - `SAFE-514` The product **MUST NOT** schedule, reschedule, or infer clinical follow-up
    intervals. It displays what a confirmed source states and tracks attendance.

#### Recorded measurement

- **Required:** measure name; value; unit; observation date; source type; source document
  where applicable; context.
- **Rules:** `SAFE-520`, `SAFE-581`, `SAFE-502` apply in full.

### 15.3 Daily care organization

`PROD-710` Confirmed items with timing expressions are placed into the day using their
**stated timing expression**, mapped to the user's own meal/wake/sleep time labels
configured during setup.

`SAFE-711` This mapping is a **display-scheduling convenience only**. It **MUST NOT** be
described or presented as a clinical schedule, and it **MUST NOT** alter, refine or
interpret the timing instruction itself. The stated instruction text always remains
visible alongside the placed time.

`PROD-712` Items without a determinable time appear as **reference cards**, not as timed
tasks, and are never silently assigned a time.

### 15.4 Completion tracking

`PROD-720` Care items support: **completed** (with timestamp), **skipped** (with
timestamp), **overdue** (derived from time only), **not yet due**.

`PROD-721` Completion is a record of what the user reported. The product **MUST NOT**
present it as verification that a dose was taken.

`SAFE-722` Adherence data **MUST NOT** be used to generate clinical conclusions, risk
statements, or predictions (`SAFE-703`).

### 15.5 Explanation without overstep

`PROD-730` The product may restate a confirmed instruction in simpler language
(`F-A10`, `F-AI03`). Binding constraints:

- Meaning **MUST** be preserved. No content added, none removed.
- The source document and date **MUST** be shown with the explanation.
- The explanation **MUST** state that it is a simplification of the document.
- The explanation **MUST** direct clinical questions to the healthcare professional.
- `SAFE-731` The product **MUST NOT** explain *why* a clinician prescribed something, or
  what a medicine does, unless a confirmed source states it.

### 15.6 Emergency and safety posture

`SAFE-014` The product **MUST NOT** perform emergency triage, symptom assessment, urgency
classification, or any emergency medical decision.

`SAFE-740` It **MAY** display user-entered care-team and emergency contact details
(`F-A13`) and a fixed, non-assessing statement directing the user to their clinician or
emergency services if they feel unwell. This statement **MUST NOT** be conditioned on,
or generated from, any symptom input, and the product **MUST NOT** ask the user to
describe symptoms for evaluation.

`SAFE-741` The product **MUST NOT** claim to monitor the user, detect problems, or provide
any form of safety net. It **MUST NOT** imply that using it makes the user safer.

---

## 16. Wellness/Fitness Companion

This section specifies the GUIDE pillar. Unlike ASSIST, GUIDE **may generate content**,
because general wellness movement is not clinical instruction. It operates inside a
conservative envelope.

### 16.1 Request understanding

`PROD-800` The product **MUST** interpret a request expressing: **available time**;
**goal**; **preferences**; **relevant user context**.

`PROD-801` Supported request channels, in priority of guaranteed availability:

1. **Time preset + optional goal chip** — always available, no typing, no voice (`F-G02`).
2. **Natural-language voice** — where technically supported (`TECH-450`).
3. **Optional free text** — never required (`PROD-410`).

`PROD-802` Where a request is ambiguous, the product asks **at most one** clarifying
question, with selectable options, and otherwise applies a safe default. It **MUST NOT**
interrogate the user.

### 16.2 Routine structure

`PROD-810` A routine is an ordered sequence of segments. Each segment has: a name; a type
(warm-up / mobility / light exercise / strength / stretch / breathing / cooldown); a
duration or repetition count; short instruction lines; an optional gentler variant.

`PROD-811` A routine **MUST** open with a warm-up segment and close with a cooldown or
breathing segment whenever it contains any exertion segment.

`PROD-812` Total duration **MUST** match the requested budget within a defined tolerance
(`PROD-121`), and the total **MUST** be displayed before starting.

`PROD-813` Routine types **MUST** include time-based routines and goal-based routines, and
**MUST** support stretching, mobility, breathing and relaxation as first-class outputs —
not only "workouts" (`F-G07`, `F-G08`).

### 16.3 Safety envelope for generated content

These are the boundaries within which generation is permitted. They exist because the
product cannot assess a user's physical fitness for an activity.

`SAFE-030` Generated wellness routines **MUST** be restricted to low-to-moderate,
bodyweight, non-technical, low-impact movement suitable for a general adult audience in a
domestic space without equipment or supervision.

`SAFE-031` Generated wellness content **MUST NOT** be presented as prescribed exercise,
therapy, rehabilitation, or treatment, and **MUST NOT** substitute for a confirmed
prescribed activity.

`SAFE-032` Where the profile holds confirmed activity precautions, those precautions
**MUST** be surfaced before a generated session begins, in the source's own terms with its
date, and a gentler option offered.

`SAFE-033` The product **MUST NOT** decide that an activity is medically safe or
appropriate for a user. It presents, it warns from confirmed sources, and it defers to the
user and their clinician.

`SAFE-034` Generated routines **MUST NOT** include: high-impact or plyometric movement;
heavy or loaded resistance; breath-holding or forceful breathing protocols; inversions;
maximal-effort or to-failure instructions; neck or spinal loading; rapid positional change
from lying to standing; any movement requiring supervision or equipment not confirmed
available.

`SAFE-035` Routines **MUST NOT** include intensity targets expressed in clinical terms
(target heart rate, RPE thresholds tied to cardiac guidance, METs) unless such a target is
present in a confirmed source.

`SAFE-036` A standing, non-alarming stop instruction **MUST** be available during guided
sessions (`SAFE-606`). The product **MUST NOT** evaluate any symptom the user reports.

`SAFE-037` For a **Care** or **Both** user, generated wellness content **MUST** be
additionally conservative and **MUST** carry a visible note that it is general wellness
content, not part of their doctor-provided plan.

### 16.4 Guided execution

`PROD-820` The Session Player satisfies Section 14.7 in full.

`PROD-821` Timing is visible and predictable: the current segment's remaining time and the
session's overall progress are both always on screen.

`PROD-822` Transitions are announced on screen before they occur, with enough lead time
for a user to reposition.

`PROD-823` A session is resumable after pause or interruption, and partial completion is
recorded truthfully (`PROD-605`).

### 16.5 Personalization

`PROD-830` The product **MAY** personalize using: stated time budgets; stated goals;
stated preferences and dislikes; movements the user has marked to avoid; completion
history; time of day.

`PROD-831` Personalization **MUST** stay inside the `SAFE-030`–`SAFE-037` envelope.
History **MUST NOT** be used to escalate intensity beyond the envelope.

`SAFE-832` Personalization **MUST NOT** use, infer from, or be conditioned on clinical
information in a way that constitutes clinical reasoning. Confirmed precautions are
applied as stated constraints only — never as inputs to an inference about the user's
condition or capacity.

### 16.6 Recording

`PROD-840` On completion, the session is recorded with: routine identity, segments
completed, total active duration, completion state (complete / partial), timestamp, and
source (`generated` or `preset`).

`PROD-841` The record feeds PROGRESS (`F-P01`) and the Daily Summary (`F-P04`).

---

## 17. AI Capabilities

This section states what the AI **does**. Section 18 states what it **must never do**.
Both are binding; where they appear to conflict, Section 18 wins.

### 17.1 The two AI regimes

The single most important architectural idea in this specification:

| | **ASSIST regime (clinical domain)** | **GUIDE regime (wellness domain)** |
|---|---|---|
| AI role | **Transformer** of existing information | **Generator** within a safety envelope |
| May originate content? | **No** | **Yes** |
| Source of truth | Confirmed structured application data | The safety envelope + user's stated constraints |
| Output labelling | Traces to source + date | Labelled AI-generated / wellness |
| Failure mode to prevent | Inventing clinical content | Generating unsafe or over-ambitious movement |

`SAFE-900` Every AI operation **MUST** be explicitly assigned to exactly one regime at
design time, and **MUST** be constrained accordingly. An operation that would need to
generate clinical content is not permitted in either regime.

### 17.2 Capability — natural-language understanding (`F-AI01`)

Maps a user request to one supported in-app task: start a wellness session with given
constraints; answer a bounded question about their own confirmed plan; navigate; mark an
item complete; open the summary.

`PROD-910` Unrecognized or out-of-scope requests receive a short, friendly refusal that
states what the product can help with and offers selectable options. The product **MUST
NOT** improvise an answer outside scope.

### 17.3 Capability — document information structuring (`F-AI02`)

Converts document content into **proposed** structured items.

`SAFE-911` Output **MUST** include, per proposed item: the source document reference, the
specific source text or region it was derived from, and a confidence signal.

`SAFE-912` The AI **MUST NOT** fill gaps. A field not present in the source is **absent**,
never inferred, never defaulted to a typical value.

`SAFE-913` Output always lands in **Needs Review** (`SAFE-501`).

`SAFE-914` Where the AI cannot read content with adequate confidence it **MUST** emit
**Unclear — needs a person** rather than a best guess (`SAFE-503`).

### 17.4 Capability — simplification and explanation (`F-AI03`)

Restates confirmed instructions in plain language, bound by `PROD-730` and `SAFE-731`.

`SAFE-915` The explanation operation **MUST** be constrained to the confirmed item's own
text and **MUST NOT** draw on general medical knowledge. Its permitted transformation is
linguistic simplification only.

### 17.5 Capability — bounded question answering (`F-AI07`)

**In scope:** what is on the user's plan today; what a confirmed instruction says; what
they have completed; what their recorded values are and when they were recorded; how to
use the application; what a wellness routine contains.

**Out of scope — must refuse and redirect:** anything diagnostic; anything about whether
to take, skip, change or combine medication; whether a symptom is serious; whether they
are improving; what a condition is or how it progresses; medical information not in a
confirmed source; any request to act as a clinician.

`SAFE-916` Refusals **MUST** be brief, warm, non-frightening, and **MUST** direct the user
to their healthcare professional. They **MUST NOT** lecture, and **MUST NOT** partially
answer before refusing.

### 17.6 Capability — routine generation and personalization (`F-AI04`, `F-AI05`)

Governed by Sections 16.2, 16.3 and 16.5.

`SAFE-917` Generated routines **MUST** pass a deterministic validation step against the
`SAFE-034` prohibition list and the duration budget **before** being shown to the user.
Generation alone is not sufficient; validation is required (`F-AI08`).

### 17.7 Capability — summarization (`F-AI06`)

Produces the AI portion of the Daily Summary, bound by Section 24.

`SAFE-918` The summarizer receives only: completion records, activity records, and
confirmed values with their dates. It **MUST NOT** be given latitude to characterize
health status, and its output occupies a separate labelled region (`SAFE-141`).

### 17.8 Capability — behavioural insight (`F-P05`)

`SAFE-919` Insights are restricted to observable behaviour — frequency, consistency,
timing, completion patterns, streaks. Any statement about the user's health, condition,
recovery or risk is prohibited (`SAFE-703`).

### 17.9 Guardrail layer (`F-AI08`)

`SAFE-920` A guardrail layer **MUST** sit between every AI output and the user interface.
It is not advisory and **MUST NOT** be bypassed. Minimum duties:

1. Enforce regime assignment (`SAFE-900`).
2. Validate that ASSIST-regime output contains no content absent from its confirmed
   source.
3. Validate generated routines against `SAFE-034` and the duration budget (`SAFE-917`).
4. Enforce refusal for out-of-scope requests (Section 17.5).
5. Enforce provenance and labelling before render (`SAFE-521`, `SAFE-141`).
6. Fail **closed**: if the guardrail cannot validate an output, the output is **not
   shown**, and the product falls back to confirmed data, a preset, or an honest
   unavailability message (`TECH-930`).

`SAFE-921` The guardrail layer's rules **MUST** be expressed in the codebase in a form
that can be read, reviewed and tested independently of any AI provider or prompt.

`TECH-922` Prompt-level instruction alone is **not** an acceptable implementation of any
`SAFE-` requirement. Prompts are necessary but insufficient; enforcement must also exist
in code.

---

## 18. AI Safety Boundaries

This section is **non-negotiable**. It applies to every AI-touching surface, in every
phase, in perpetuity. A change to this section requires explicit owner approval and is not
within the discretion of any implementation agent (`RULE-006`).

### 18.1 Absolute prohibitions

The AI, and the product as a whole, **MUST NOT**:

| ID | Prohibition |
|---|---|
| `SAFE-001` | **Diagnose** any disease, condition or state. |
| `SAFE-002` | **Prescribe** any treatment, medication, therapy or intervention. |
| `SAFE-003` | **Change medication dosage** — or suggest, imply, calculate or normalize a change. |
| `SAFE-004` | **Invent medical instructions.** |
| `SAFE-005` | **Invent doctor instructions**, or attribute to a clinician anything not in a confirmed source. |
| `SAFE-006` | Create **unsupported medical recommendations**. |
| `SAFE-007` | **Replace a doctor**, or present itself as able to. |
| `SAFE-008` | Make **unsupported claims about recovery**, improvement or deterioration. |
| `SAFE-009` | Make **emergency medical decisions**. |
| `SAFE-010` | **Invent health values**, or fill a missing measurement by any means. |
| `SAFE-011` | Turn **historical information into a live or current measurement**. |
| `SAFE-012` | Provide drug interaction, contraindication, side-effect or substitution information absent from a confirmed source (`SAFE-507`). |
| `SAFE-013` | Assess, classify, rate or triage a **symptom** the user reports. |
| `SAFE-014` | Perform **emergency triage** or urgency classification (Section 15.6). |
| `SAFE-015` | Present **adherence** data as clinical evidence or as a basis for any clinical statement. |
| `SAFE-016` | Claim to **monitor** the user or to detect problems (`SAFE-741`). |
| `SAFE-017` | Generate **nutritional or dietary advice** for a Care User beyond a confirmed source (`SAFE-512`). |
| `SAFE-018` | Modify, progress or substitute a **prescribed** activity (`SAFE-510`). |
| `SAFE-019` | Decide that an activity is **medically safe** for a user (`SAFE-033`). |

### 18.2 Positive obligations

The AI **MUST**:

| ID | Obligation |
|---|---|
| `SAFE-500` | Treat confirmed, structured application data as **the source of truth** for all healthcare information. |
| `SAFE-501` | Require **explicit human confirmation** before any extracted item affects the user's plan. |
| `SAFE-502` | Never interpolate, estimate, derive or default a health value. Absent means absent. |
| `SAFE-503` | Flag low-confidence or unreadable source content as **Unclear — needs a person**. |
| `SAFE-520` | Preserve and display **source, date and context** for every health value; never present history as current. |
| `SAFE-141` | Keep **AI-generated content visually and structurally separate** from confirmed clinical information, and always labelled. |
| `SAFE-916` | Refuse out-of-scope clinical requests briefly and warmly, and **redirect to the healthcare professional**. |
| `SAFE-920` | Pass every output through the guardrail layer, which **fails closed**. |
| `SAFE-930` | Preserve the **exact meaning** of any clinical text it restates. |
| `SAFE-931` | Distinguish **historical** information from **current** information in every presentation. |

### 18.3 The separation invariant

`SAFE-940` **Invariant.** At every point in the system — storage, transport, processing and
presentation — it **MUST** be unambiguously determinable whether a given piece of health
information is:

1. **Confirmed clinical information** (from a document, human-confirmed), or
2. **Self-reported information** (entered by the user or caregiver, so labelled), or
3. **AI-generated or AI-derived content**, or
4. **Demo / synthetic data**.

These four classes **MUST NOT** be merged into a single undifferentiated store, rendered
with identical treatment, or allowed to flow into one another. An AI-generated value
**MUST NOT** be promotable to confirmed clinical information by any code path.

`SAFE-941` This invariant is the single most important technical requirement in this
specification. Any architecture that cannot express it **MUST** be rejected in the
Architecture phase.

### 18.4 Required user-facing transparency

`SAFE-950` The product **MUST** make plain, in language a non-technical user understands,
and at the point of use rather than buried in settings:

- that it organizes information from their own documents and does not provide medical
  advice;
- that AI-written text is AI-written;
- that questions about their health, medicines or symptoms go to their healthcare
  professional;
- that it is not for emergencies.

`SAFE-951` These statements **MUST** appear in first-run orientation and remain accessible
from Settings. They **MUST NOT** rely on a long legal document as the sole disclosure.

`SAFE-952` The product **MUST NOT** use language that overstates its role. Prohibited
framings include claiming to manage the user's health, to keep them safe, to track their
condition, or to be their doctor or nurse.

### 18.5 Relationship to Amazon Appstore policy (category A + C)

Verified official requirement:

`HACK-960` *"Your app must not include content that provides inaccurate or misleading
medical advice or makes unsubstantiated medical claims."* — Amazon Appstore Restricted
Content Policy.

`HACK-961` Appstore content policy applies **not only to app content but also to app
metadata** — title, description, images and keywords. An app may be rejected or suppressed
for metadata violations even if the app itself complies.
> Official: Amazon Appstore Content Policy.

Derived requirements:

`SAFE-962` All product copy, store metadata and demo narration **MUST** avoid any claim
that could read as medical advice or as an unsubstantiated medical claim. Sections 18.1 and
18.4 are the operative controls.

`SAFE-963` Because of `HACK-961`, the **public-facing product name and description** are
in scope for this review. The project name "AI Assistant Healthcare" is retained as the
**internal project name**; whether the user-facing display name and description should be
chosen to avoid implying clinical capability is recorded as `OQ-09`. No change is made
without owner approval (`RULE-002`).

**Note on what was *not* verified.** Secondary sources describe stricter Appstore
obligations for health apps (mandatory diagnosis disclaimers, restrictions on drug dosage
calculators, accuracy-claim substantiation). These were **not** confirmed verbatim from a
primary Amazon policy page during this review. They are therefore **not** asserted as
official requirements. They are recorded as `OQ-08` and, prudently, the product's own
`SAFE-` rules already meet or exceed each of them. This specification deliberately does
not invent hackathon or policy restrictions.

---

## 19. Health Data & Document Handling

### 19.1 Document lifecycle

```
  RECEIVED ──▶ PROCESSING ──▶ PROPOSED (Needs Review)
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
          CONFIRMED            EDITED +           DISCARDED
        (affects plan)        CONFIRMED         (retained as
              │              (affects plan)      audit record)
              │                   │
              └─────────┬─────────┘
                        ▼
                  UNCLEAR — NEEDS A PERSON
                 (never affects the plan)
```

`SAFE-501` **The confirmation gate is mandatory.** Only `CONFIRMED` and
`EDITED + CONFIRMED` items may affect the user's plan, Today screen, reminders, or
summary. Nothing else may, under any circumstance, by any code path.

### 19.2 Provenance model

`SAFE-970` Every health datum **MUST** carry:

| Field | Meaning |
|---|---|
| `dataClass` | One of the four classes in `SAFE-940`. |
| `sourceType` | `document` \| `user_entered` \| `caregiver_entered` \| `ai_generated` \| `demo_seed`. |
| `sourceDocumentRef` | Reference to the originating document, where applicable. |
| `sourceExcerptRef` | The specific text or region the value came from, where applicable. |
| `observationDate` | When the value was observed or the instruction was issued. |
| `recordedDate` | When it entered the system. |
| `confirmationState` | Per Section 19.1. |
| `confirmedBy` | Which human confirmed it, and when. |
| `confidence` | Extraction confidence, where applicable. |
| `originalText` | The verbatim source text for any clinical instruction. |

`SAFE-971` `originalText` **MUST** be retained for every clinical instruction and **MUST**
remain accessible from the UI, so that any simplification can always be checked against
what the document actually said.

`SAFE-521` A datum whose provenance fields cannot be populated **MUST NOT** be rendered.

### 19.3 Extraction rules

`SAFE-912` No gap-filling. Absent fields stay absent.
`SAFE-504` Dose strings are transcribed, never normalized.
`SAFE-913` All extraction output is `PROPOSED`.
`SAFE-914` Low confidence yields `UNCLEAR`, not a guess.

`SAFE-972` Extraction **MUST NOT** classify, stage, code or categorize a **condition**. It
may extract stated instructions and stated values. It **MUST NOT** derive a diagnosis from
a document, even where one is stated — a stated diagnosis may be **displayed as quoted
source text** with its date, but **MUST NOT** become a structured clinical attribute that
the AI reasons from (`SAFE-832`).

`SAFE-973` Extraction **MUST NOT** be run to "improve" or re-derive already-confirmed
items. Confirmed items are immutable except through the Section 19.6 path.

### 19.4 Historical vs current

`SAFE-011` / `SAFE-520` / `SAFE-931` A value with an `observationDate` outside a defined
recency window **MUST** be presented as a historical record with its date, and **MUST NOT**
appear in any "current", "latest as of now", or live-status presentation.

`TECH-974` The recency window is a product-configured value per measure type, decided in
the Architecture phase. It **MUST NOT** default to "treat everything as current".

### 19.5 Data minimization

`PRIV-601` The product **MUST** hold only the minimum health information necessary to
deliver the features in this specification. It **MUST NOT** collect health information for
analytics, model improvement, or future unspecified use.

`PRIV-602` Documents and extracted clinical data **MUST NOT** be retained longer than
needed to serve the user, and the user **MUST** be able to remove them (`PROD-631`).

### 19.6 Correcting confirmed information

`SAFE-975` Confirmed clinical items **MAY** be corrected only by an explicit human action
that: identifies who made the change; records the previous value; records the reason where
offered; and preserves `originalText` unchanged.

`SAFE-976` The AI **MUST NOT** initiate, suggest a specific value for, or auto-apply a
correction to confirmed clinical content. It **MAY** surface that two confirmed items
appear to conflict and ask a human to look (`SAFE-506`).

### 19.7 Demo and test data

`HACK-980` For the hackathon, all health data used **MUST** be synthetic, demo, or
explicitly authorized data. Real patient medical records **MUST NOT** be placed in the
repository (`PRIV-142`).

`PRIV-981` Synthetic data **MUST** be identifiable as such at the data layer
(`sourceType = demo_seed`) and visibly identified in the UI (`F-X07`), so that no viewer of
a demo can mistake seeded content for a real person's records.

`PRIV-982` Synthetic personas **MUST NOT** be based on a real identifiable individual, and
**MUST NOT** reuse real names, identifiers, dates of birth, or document scans.

---

## 20. Daily Routine

### 20.1 Purpose

`PROD-1000` The product **MUST** organize the user's day into a single, ordered, glanceable
routine that answers *what now*, *what next*, *what is done*.

### 20.2 Composition by user context

**For a CARE user, the day may include:**

| Element | Source | Rule |
|---|---|---|
| Medication instructions | Confirmed documents | `SAFE-504`, `SAFE-505` |
| Prescribed exercises | Confirmed documents | `SAFE-510` |
| Meal instructions | Confirmed documents | `SAFE-512` |
| Precautions | Confirmed documents | `SAFE-032`, `SAFE-513` |
| Appointments / checkups | Confirmed documents | `SAFE-514` |
| Other doctor-provided instructions | Confirmed documents | `SAFE-500` |

**For a WELLNESS user, the day may include:**

| Element | Source | Rule |
|---|---|---|
| Workout | Generated / preset | `SAFE-030`–`SAFE-037` |
| Stretching | Generated / preset | `SAFE-030`–`SAFE-037` |
| Mobility | Generated / preset | `SAFE-030`–`SAFE-037` |
| Breathing | Generated / preset | `SAFE-034` |
| Relaxation | Generated / preset | `SAFE-034` |
| Activity goals | User-stated | Behavioural only (`SAFE-919`) |

**For a BOTH user:** the union of the above, with `PROD-030` (visual and structural
distinction) and `SAFE-037` (extra conservatism for generated content) enforced at all
times.

### 20.3 Construction rules

`PROD-1010` The day is constructed from **confirmed** care items plus **wellness slots**.
No unconfirmed item may enter it (`SAFE-501`).

`PROD-1011` Care items are placed using their stated timing expression mapped to the user's
configured day anchors (wake, breakfast, lunch, evening, night). The stated expression
remains visible beside the placed time (`PROD-710`, `SAFE-711`).

`PROD-1012` Items without determinable timing appear as reference cards, never as timed
tasks (`PROD-712`).

`PROD-1013` Wellness slots are **offers, not obligations**. An unused wellness slot is
recorded as *not done*, never as a failure, and never surfaced with the prominence of an
overdue care item.

`PROD-1014` The day **MUST** be recomputed on each entry to Today and on each completion,
so that Now and Next are always accurate.

`PROD-1015` The day **MUST** have a defined rollover boundary. Incomplete items do **not**
silently carry into the next day's task list; they are recorded as not completed for that
day and appear in that day's record (`PROD-1301`).

### 20.4 What the daily routine is not

`SAFE-1020` The daily routine is a **display and organization artifact**. It **MUST NOT**
be described, labelled or narrated as a treatment plan, a care protocol, a clinical
schedule, or medical advice (`SAFE-711`).

---

## 21. Reminders

### 21.1 Platform reality (category E — binding constraint on scope)

`TECH-460` A television is not a reliable personal alerting device. It is frequently off,
in use by another household member, or running another application. The product **MUST
NOT** be specified as though it will reliably alert a user at a medication time.

`SAFE-1100` The product **MUST NOT** claim, imply, or be marketed as providing reliable
medication alerting. Doing so would create a safety expectation the platform cannot
support and would risk an unsubstantiated claim (`HACK-960`, `SAFE-741`).

### 21.2 MVP reminder model — in-app surfacing (`F-X09`)

`PROD-1110` While the app is open, the product **MUST** surface the current state of the
day: the due item as **Now**, the following item as **Next**, and any unmarked past-due
item as **Overdue**.

`PROD-1111` Overdue presentation **MUST** be factual and calm: it states that an item is
not marked as done, with its time and source. It **MUST NOT** use alarm styling, alarming
language, or any language implying consequence or blame (`PROD-555`, `PROD-435`).

`SAFE-1112` An overdue medication item **MUST NOT** be accompanied by advice about what to
do (`SAFE-505`). Permitted actions are limited to: **Mark as taken**, **Mark as skipped**,
and a plain pointer to the care team if the user is unsure.

`PROD-1113` If the app is opened after a period of inactivity, it **MUST** show the current
true state of the day without implying the user was reminded earlier.

`PROD-1114` Reminders **MUST NOT** interrupt a guided wellness session. They surface on
return to Today.

### 21.3 Future reminder model (`F-X10`, `FUT-`)

`FUT-1120` **System-level notification while the app is not in the foreground.**
Feasibility is platform-dependent and differs between Fire OS and Vega OS. This is
deferred and **feasibility-gated**: it may only be built after the Architecture phase
confirms a supported, policy-compliant mechanism on the chosen target.

`FUT-1121` **Companion-device reminders** (caregiver or user phone), which is the
architecturally honest place for reliable alerting. Deferred with `FUT-1200`.

`FUT-1122` **Ambient on-TV nudge** while another app is in the foreground — only if a
supported, non-intrusive platform mechanism exists. Must respect `PRIV-704`: a nudge
visible to the room **MUST NOT** disclose health information.

### 21.4 Privacy constraint on all reminders

`PRIV-1130` A reminder rendered on a shared screen **MUST NOT** disclose medication names,
conditions, or other sensitive detail unless the profile owner has opted in. The default
reminder presentation outside an entered profile is non-specific (e.g. "You have an item
due") (`PRIV-702`, `PRIV-704`).

---

## 22. Activity Tracking

### 22.1 What is tracked

`PROD-1200` The product **MUST** record, per profile:

| Event | Fields |
|---|---|
| Care item completed | item ref, type, scheduled time, completion timestamp, `completed` |
| Care item skipped | item ref, type, scheduled time, timestamp, `skipped` |
| Care item overdue/not marked | item ref, type, scheduled time, end-of-day state |
| Appointment attended | item ref, date, timestamp |
| Wellness session completed | routine ref, segments completed, active duration, `complete`, timestamp, source (`generated`/`preset`) |
| Wellness session partial | as above with `partial` and the point of exit |
| Wellness slot unused | slot ref, date, `not done` |

### 22.2 Integrity rules

`PROD-1210` Tracking records **what the user reported**, with a timestamp. The product
**MUST NOT** present a completion record as verification that an action physically occurred
(`PROD-721`).

`PROD-1211` Records **MUST** be truthful and **MUST NOT** be rounded up, gamified, or
inflated. A partial session is recorded as partial (`PROD-605`).

`PROD-1212` A user **MUST** be able to correct a mistaken completion entry, and the
correction is itself recorded.

`SAFE-1213` Tracking data **MUST NOT** be used to generate clinical conclusions, risk
statements, predictions, or any statement about the user's health (`SAFE-015`,
`SAFE-703`, `SAFE-722`).

`SAFE-1214` Tracking **MUST NOT** be framed as monitoring or supervision of the user
(`SAFE-016`, `SAFE-741`).

### 22.3 Tone requirements

`PROD-1220` Acknowledgement of completion is calm and brief (`PROD-438`). No celebration
spectacle, no sound that could startle, no score.

`PROD-1221` Non-completion is neutral. The product **MUST NOT** use guilt, streak-loss
pressure, or any motivational framing that could distress a recovering user. Streaks exist
as information for wellness users, not as leverage.

### 22.4 What is not tracked

`PRIV-1230` The product **MUST NOT** track: passive behaviour, viewing habits, dwell time
for analytics, location, biometric data, or anything not required by a feature in this
specification (`PRIV-601`, `PROD-205`).

---

## 23. Progress

### 23.1 Purpose

`PROD-1300` Progress reflects **what the person actually did**, honestly, in a way that is
encouraging without being manipulative and informative without being clinical.

### 23.2 Content

`PROD-1301` Progress **MUST** provide: completed activities; routine completion for recent
days; history over a defined recent window; daily summaries; wellness progress; and
relevant available recorded health information with dates.

`PROD-1302` Presentation **MUST** be TV-appropriate: large, low-density, comprehensible at
distance. Dense charts and small-label graphs are prohibited (`PROD-401`, `HACK-415`).

`PROD-1303` Where a trend over time is shown, it **MUST** be a simple, large,
clearly-labelled representation of **behaviour** (sessions done, items completed), not of
clinical values.

### 23.3 Recorded-information comparison (`F-P06`)

`PROD-1310` The product **MAY** show a recorded value beside an earlier recorded value of
the same measure.

`SAFE-1311` Such a comparison **MUST**: show both observation dates; show both sources;
describe the change only in neutral factual terms (e.g. "recorded 128 on 12 Aug 2026;
recorded 122 on 20 Sep 2026"); and **MUST NOT** characterize the change as improvement,
worsening, progress, good, bad, normal or abnormal (`SAFE-008`, `SAFE-703`).

`SAFE-1312` The product **MUST NOT** compute or display clinical reference ranges, targets,
or in-range/out-of-range status, unless such a range is present verbatim in a confirmed
source and is displayed as quoted source content with its date.

### 23.4 Behavioural insight (`F-P05`)

`SAFE-703` Insights **MUST** be restricted to observable behaviour. The following are
**prohibited**: any claim that the user's health, condition, recovery, fitness level or risk
has changed; any causal claim linking their activity to a health outcome; any prediction.

Permitted examples: *"You completed a session on 5 of the last 7 days."* / *"Your morning
sessions are more consistent than your evening ones."*

Prohibited examples: *"Your heart health is improving."* / *"Your recovery is on track."* /
*"This routine is helping your blood pressure."*

`SAFE-1320` Insights **MUST** be visually separated and labelled as AI-generated
(`SAFE-141`).

---

## 24. Daily Health & Wellness Summary

### 24.1 Purpose

`PROD-1400` The product **MUST** maintain a **Daily Health & Wellness Summary** that gives
the user a truthful, simple, end-of-day picture.

### 24.2 Content

`PROD-1401` The summary may include: activities completed; routine completion; reminders
and actions completed; available recorded health information; relevant comparisons with
previous records; activity and progress information; a simple AI-generated summary; and the
next-day plan.

### 24.3 The four-region separation requirement

`SAFE-1410` The summary **MUST** structurally distinguish four kinds of content, and this
separation **MUST** be visible to the user — not merely present in the data model:

| Region | Contains | Provenance treatment |
|---|---|---|
| **1. Recorded facts** | What was completed, skipped, or not marked today; sessions done; appointments attended. Timestamped. | Application records. Stated plainly. |
| **2. Historical information** | Available recorded health values, each with its observation date and source. | `SAFE-520` — never presented as current. |
| **3. User activity** | What the user did: sessions, durations, items acted on. | Records of user-reported action (`PROD-1210`). |
| **4. AI interpretation** | A short plain-language summary and the next-day plan. | Visibly separated, explicitly labelled AI-generated (`SAFE-141`). |

`SAFE-1411` The four regions **MUST NOT** be blended into a single narrative paragraph.
Region 4 **MUST NOT** restate regions 1–3 in a way that obscures which is fact and which is
interpretation.

`SAFE-1412` Region 4 **MUST NOT** contain any health value that does not appear, with its
date, in region 1 or 2.

### 24.4 Prohibited summary content

`SAFE-703` / `SAFE-1420` The summary **MUST NOT** claim that a medical condition has
improved, worsened, stabilized, or changed in any way, unless appropriate verified
information supports such a conclusion **and** that conclusion is quoted from a confirmed
clinical source with its date. The product itself **MUST NOT** originate such a conclusion.

Also prohibited in the summary: predictions; risk statements; causal claims linking
activity to health outcomes; encouragement framed as clinical reassurance (e.g. *"you're
doing great, your heart is getting stronger"*); any comparison against clinical norms
(`SAFE-1312`).

Permitted encouragement is behavioural and honest: *"You completed everything on your plan
today."*

### 24.5 Next-day plan

`PROD-1430` The next-day plan is a **projection of already-confirmed care items** plus
**offered wellness slots**. It **MUST NOT** introduce a new clinical item, alter a
confirmed item, or imply a clinician-endorsed progression (`SAFE-004`, `SAFE-018`).

### 24.6 Availability and tone

`PROD-1440` The summary is reachable from Today in one action (`PROD-432`) and is readable
in full without horizontal navigation.

`PROD-1441` Tone is calm, brief, plain, and non-judgemental (`PROD-1221`, `PROD-436`).

`SAFE-1442` Where nothing was completed, the summary states that factually and offers a
neutral path forward. It **MUST NOT** express disappointment or concern about the user's
health.

---

## 25. User Profiles

### 25.1 User contexts

`PROD-1500` The product **MUST** support three user contexts:

| Context | Description | Surfaces shown |
|---|---|---|
| **CARE USER** | Follows a provided healthcare/care routine. | Today (care-led), Care Plan, Health Info, Documents, Wellness, Progress, Settings |
| **WELLNESS USER** | Primarily wants fitness/wellness guidance. | Today (wellness-led), Wellness, Progress, Settings |
| **BOTH** | Wants care routine support and general wellness. | All surfaces, with `PROD-030` distinction enforced |

`PROD-031` The product **MUST NOT** force every user through a medical workflow, and
**MUST NOT** force every user into a fitness-only workflow.

`PROD-1501` A Care User **MUST** still have access to wellness features — a recovering
person benefits from gentle movement — but wellness **MUST NOT** displace or dilute their
care plan, and `SAFE-037` applies.

`PROD-1502` The user context is chosen at profile creation, is explained in one plain line
per option, and is changeable later from Settings without data loss.

### 25.2 Profile model

`PROD-1510` A profile holds: display name; avatar; user context; day anchors (wake,
breakfast, lunch, evening, night); optional PIN; preferences and avoided movements; care
plan (Care/Both only); documents (Care/Both only); recorded measurements (Care/Both only);
activity records; summaries; care-team and emergency contact information (optional).

`PRIV-1511` Profiles **MUST** be isolated. No profile's health information, documents,
records, or summaries may be visible from, or influence, another profile
(`PRIV-703`).

`PRIV-1512` There is **no** shared household health store. Health information belongs to
exactly one profile.

### 25.3 Roles within a profile

`PROD-1520` Two roles act on a Care profile:

- **The profile owner** (the person the plan belongs to): views the plan, acts on items,
  completes activities, views summaries.
- **The caregiver** (`F-A14`): additionally performs setup, document intake, and review and
  confirmation of extracted items (`SAFE-501`).

`PROD-1521` In the MVP both roles operate **on the TV**, within the same profile. A formal
permission split and a remote caregiver experience are future scope (`FUT-1200`).

`SAFE-1522` Because confirmation is a safety-critical action (`SAFE-501`), the confirmation
UI **MUST** make clear that the person confirming is asserting that the extracted
information matches the document. It **MUST NOT** be reducible to a single unconsidered
press-through (`PROD-621`, `PROD-623`).

### 25.4 Profile lifecycle

`PROD-1530` Creating a profile requires only a name and a user context. Everything else is
optional and can be added later. Setup **MUST NOT** be a long form
(`PROD-424`, `PROD-427`).

`PROD-1531` Deleting a profile **MUST** require explicit confirmation, **MUST** state
plainly what will be removed, and **MUST** remove that profile's health information and
documents (`PRIV-602`, `PROD-631`).

---

## 26. Privacy & Security

The product may handle sensitive health information. These requirements are binding. They
state **what must be true**; mechanisms are decided in the Architecture phase.

### 26.1 Data minimization

`PRIV-601` **Minimum necessary data.** Collect and retain only the health information
required by a feature in this specification. No collection for analytics, model training,
model improvement, or unspecified future use.

`PRIV-1600` Every field in the data model **MUST** be justifiable by a specific feature ID.
Fields that cannot be justified **MUST** be removed.

### 26.2 Storage

`PRIV-1610` **Secure storage.** Health information, documents and extracted clinical data
**MUST** be stored using protection appropriate to sensitive personal health information on
the chosen platform.

`PRIV-1611` Health information **MUST NOT** be written to world-readable locations, shared
storage, or any location accessible to other applications on the device.

`PRIV-1612` Documents and clinical data **MUST NOT** be retained beyond what serves the
user, and the user **MUST** be able to delete them (`PRIV-602`).

`TECH-1613` Whether clinical data is stored on-device only, or on a server, is an
architecture decision (`OQ-04`) with direct privacy consequences. The decision **MUST** be
made explicitly and justified against this section — not arrived at incidentally.

### 26.3 Transmission

`PRIV-1620` **Secure transmission.** All network transmission of health information
**MUST** be encrypted in transit. Plaintext transmission is prohibited.

`PRIV-1621` Health information **MUST NOT** be transmitted to any third party that is not
required to deliver a specified feature, and any such transmission **MUST** be disclosed to
the user in plain language (`SAFE-950`).

`PRIV-1622` Where document content or clinical text is sent to an external AI or OCR
service, this **MUST** be disclosed, **MUST** be limited to the minimum content necessary,
and the provider's data-handling terms **MUST** be reviewed in the Architecture phase
(`OQ-06`). Where a provider's terms permit training on submitted content, that provider
**MUST NOT** be used for clinical content.

`HACK-1623` Any third-party SDK, API or data used **MUST** be used in accordance with its
terms and licensing, as the hackathon rules require (`HACK-812`).

### 26.4 Authentication and authorization

`PRIV-1630` **Authentication/authorization where required.** The MVP is a single-device,
single-household product; profile separation plus optional PIN (`PRIV-701`) is the
authorization boundary. If any server-side component or remote access is introduced, real
authentication and per-profile authorization become **mandatory**, not optional
(`FUT-1200`).

`PRIV-1631` A profile's health information **MUST NOT** be reachable without passing that
profile's entry gate (`PRIV-700`, `PRIV-701`).

### 26.5 Secrets

`PRIV-1640` **No secrets or API keys in client code or in the repository.** Not in source,
not in configuration files, not in commit history, not in build artifacts, not in demo
assets.

`PRIV-1641` The repository **MUST** contain a secrets-exclusion configuration from the
first commit, and a scan **MUST** be performed before submission (`PRIV-142`).

`TECH-1642` If any credentialed external service is used, the mechanism for keeping its
credential out of the client is an architecture decision and **MUST** be resolved before
that service is integrated (`OQ-07`).

### 26.6 Logging and diagnostics

`PRIV-1650` **No sensitive information in logs.** Logs, crash reports, analytics and
diagnostic output **MUST NOT** contain health information, document content, medication
names, extracted clinical text, or personally identifying information.

`PRIV-1651` Where logging is needed for development, it **MUST** use identifiers or
redaction rather than clinical content, and any verbose development logging **MUST** be
disabled in the submitted build.

`PRIV-1652` AI request/response logging is a specific risk: prompts in this product may
contain clinical text. Such logging **MUST** be off in the submitted build, or redacted.

### 26.7 Regulatory posture (stated honestly, not overclaimed)

`PRIV-1660` The MVP is a hackathon demonstration using synthetic data (`HACK-980`). This
specification therefore makes **no claim** of HIPAA, GDPR, UK GDPR, DPDP, MDR or FDA
compliance, and the product **MUST NOT** state or imply any such compliance or
certification.

`FUT-1661` Any real-world deployment handling actual patient information would require a
formal privacy, security and regulatory assessment appropriate to its jurisdiction and
intended use, conducted before launch. This is recorded as required future work and as a
known limitation (`FUT-1400`), not as something already satisfied.

`PRIV-1662` The product **MUST NOT** display badges, claims or language suggesting clinical
validation, certification, or regulatory approval it does not hold (`SAFE-952`).

---

## 27. Shared-TV Privacy

The application runs on a shared household screen. This creates a privacy obligation that
does not exist on a personal device. Per the product definition, this section defines the
**requirement** and leaves implementation detail to the Architecture phase — it is
deliberately not over-engineered.

### 27.1 Requirements

`PRIV-700` **Profile selection on launch.** The app **MUST** always open to Profile Select
and **MUST NOT** auto-enter a profile containing health information.

`PRIV-702` **No pre-entry disclosure.** Profile Select shows name and avatar only. No
condition, medication, adherence state, or health information is visible before entering a
profile.

`PRIV-701` **Optional PIN protection.** A profile holding care information **MAY** be
protected by a simple numeric PIN entered with the D-pad. It is optional, explainable in
one sentence, and has a clear non-punitive retry path.

`PRIV-703` **Profile switching.** Switching is always available from a consistent location
and **MUST** immediately clear the previous profile's health information from view. No
residual card, summary or cached screen may persist.

`PRIV-704` **Spoken output control.** Sensitive health information **MUST NOT** be spoken
aloud unless the profile owner has enabled it. The default is off. This applies to any
read-aloud, TTS, coaching audio, or voice response feature (`F-AI09`).

`PRIV-1130` **Non-specific ambient surfaces.** Anything visible outside an entered profile
— a reminder, a nudge, a resume prompt — **MUST** be non-specific and **MUST NOT** disclose
health detail.

`PRIV-1700` **Separation of private health information from general wellness content.**
Wellness content is not sensitive in the same way. The product **MUST** be able to offer
wellness features without exposing care information — so a household member can use the
wellness side without seeing another person's care plan.

`PRIV-1701` **Screen-visibility awareness.** Care surfaces **MUST NOT** be designed to
persist indefinitely on screen. Where the product remains open and idle on a care surface,
it **MUST** return to a non-disclosing state after a defined idle period
(`TECH-1702`).

`TECH-1702` The idle timeout duration and the return target are architecture decisions.
The requirement is that an unattended TV **MUST NOT** be left displaying another person's
medication list indefinitely.

### 27.2 Explicitly deferred

`FUT-1710` Per-item sensitivity classification, household roles and permissions, voice
identification of the speaker, and automatic viewer detection are **out of MVP scope** and
**MUST NOT** be built at this stage. They are preserved as future considerations.

---

## 28. Conceptual Data Model

**Conceptual only.** This describes the entities and relationships the product requires and
the invariants they must uphold. It **MUST NOT** be read as a schema, a storage choice, or
a technology decision. Field types, persistence, and normalization are Architecture-phase
concerns.

### 28.1 Entities

```
Profile
 ├── userContext: CARE | WELLNESS | BOTH
 ├── dayAnchors (wake, breakfast, lunch, evening, night)
 ├── pin? (optional)
 ├── preferences (goals, liked/avoided movements)
 ├── careTeamContact? (user-entered, display-only)
 │
 ├── Document *                       (CARE | BOTH only)
 │    ├── name, documentType, documentDate
 │    ├── receivedDate
 │    ├── processingState
 │    └── ExtractedProposal *
 │         ├── proposedItemType
 │         ├── proposedFields
 │         ├── sourceExcerptRef        ← what it came from
 │         ├── confidence
 │         └── reviewState: PROPOSED | CONFIRMED | EDITED_CONFIRMED
 │                        | DISCARDED | UNCLEAR
 │
 ├── CarePlanItem *                   (CARE | BOTH only; CONFIRMED only)
 │    ├── itemType: MEDICATION | PRESCRIBED_ACTIVITY | MEAL_INSTRUCTION
 │    │            | PRECAUTION | APPOINTMENT | OTHER_INSTRUCTION
 │    ├── displayFields (as transcribed)
 │    ├── originalText                 ← verbatim, immutable
 │    ├── timingExpression? (as given)
 │    ├── Provenance  (see 28.2)
 │    └── ChangeRecord *               (who changed what, when, prior value)
 │
 ├── HealthMeasurement *              (CARE | BOTH only)
 │    ├── measureName, value, unit, context
 │    ├── observationDate
 │    └── Provenance
 │
 ├── WellnessRoutine *
 │    ├── origin: GENERATED | PRESET
 │    ├── requestedBudget, totalDuration
 │    ├── RoutineSegment * (name, segmentType, duration|reps,
 │    │                     instructionLines, gentlerVariant?)
 │    └── validationResult                ← guardrail outcome (SAFE-917)
 │
 ├── DayPlan *  (per date)
 │    ├── ScheduledItem *   → CarePlanItem | WellnessSlot
 │    │    ├── placedTime, statedTimingExpression
 │    │    └── state: NOT_DUE | DUE | OVERDUE | COMPLETED | SKIPPED
 │    └── rolloverBoundary
 │
 ├── ActivityRecord *
 │    ├── recordType (per Section 22.1)
 │    ├── subjectRef, timestamp, outcome
 │    └── correctionOf?                 ← records corrections (PROD-1212)
 │
 └── DailySummary *  (per date)
      ├── region1_recordedFacts
      ├── region2_historicalInformation
      ├── region3_userActivity
      ├── region4_aiInterpretation      ← labelled, separated
      └── nextDayPlanRef
```

### 28.2 Provenance (required on every health datum)

Per `SAFE-970`, every `CarePlanItem`, `HealthMeasurement` and any displayed health value
carries: `dataClass`, `sourceType`, `sourceDocumentRef?`, `sourceExcerptRef?`,
`observationDate`, `recordedDate`, `confirmationState`, `confirmedBy?`, `confidence?`,
`originalText?`.

### 28.3 Invariants

These are binding on any architecture. An architecture that cannot express them **MUST** be
rejected (`SAFE-941`).

| ID | Invariant |
|---|---|
| `SAFE-940` | Every health datum's `dataClass` is exactly one of: confirmed clinical, self-reported, AI-generated, demo/synthetic. The four classes are never merged into one undifferentiated store. |
| `SAFE-1800` | An `AI-generated` datum has **no code path** by which it can become `confirmed clinical`. |
| `SAFE-1801` | A `CarePlanItem` exists **only** with `confirmationState ∈ {CONFIRMED, EDITED_CONFIRMED}`. Proposals are a separate entity (`ExtractedProposal`) and can never be read as plan items. |
| `SAFE-1802` | `originalText` is immutable once confirmed and is always retrievable from the UI. |
| `SAFE-1803` | A `DayPlan.ScheduledItem` may reference only a `CarePlanItem` or a `WellnessSlot` — never an `ExtractedProposal`. |
| `SAFE-1804` | Every `HealthMeasurement` has a non-null `observationDate`. A measurement without one cannot exist. |
| `SAFE-1805` | No entity stores a derived, interpolated, estimated or defaulted health value. Absent is representable and is the only valid response to missing source data. |
| `SAFE-1806` | `WellnessRoutine` carries a `validationResult`; a routine with a failed or absent validation cannot be presented to a user. |
| `SAFE-1807` | `DailySummary.region4_aiInterpretation` contains no health value absent from region 1 or region 2. |
| `PRIV-1808` | Every `Document`, `CarePlanItem`, `HealthMeasurement` and `DailySummary` belongs to exactly one `Profile` and is unreachable from another. |
| `PRIV-1809` | Every `demo_seed` datum is identifiable as such at the data layer. |

### 28.4 Deliberately absent from the model

To prevent scope and safety drift, the conceptual model contains **no**: `Diagnosis`
entity; `Condition` entity; clinical reference range; risk score; severity or stage;
computed dose; drug database; interaction table; clinical decision rule. Their absence is
intentional (`SAFE-972`, `SAFE-1312`, `SAFE-507`).

---

## 29. Conceptual System Architecture

**High level only, as required.** This section defines capabilities, boundaries and the
decisions that must be made. It **MUST NOT** be read as locking any technology. The
Architecture Specification will resolve the open decisions.

### 29.1 What is already fixed by official requirement

`HACK-800` The application **MUST** run on **Fire OS or Vega OS** — this is the hackathon's
Fire TV track requirement, and it is the only platform constraint that is fixed at this
stage.
> Official: *"Eligible projects for this category have to launch a demo-ready app that works on Fire OS or Vega OS."*

`HACK-801` **Framework is not constrained** by the hackathon. Official material states any
framework is acceptable — React Native, Android (Kotlin/Java), or web technologies —
provided it runs on Fire OS or Vega OS. **No framework is locked by this document.**

### 29.2 Conceptual components

```
┌──────────────────────────────────────────────────────────────────┐
│                  FIRE TV APPLICATION (10-ft UI)                  │
│   Profile Select · Today · Item Detail · Care Plan · Health Info │
│   Wellness · Session Player · Progress · Documents · Settings    │
│   ── D-pad focus/navigation model · safe zone · type scale ──    │
└───────────────┬──────────────────────────────────┬───────────────┘
                │                                  │
      ┌─────────▼──────────┐             ┌─────────▼──────────┐
      │  DAY / PLAN ENGINE │             │  SESSION RUNTIME   │
      │  builds DayPlan    │             │  timed step-by-step│
      │  from CONFIRMED    │             │  guidance, pause,  │
      │  items + slots     │             │  resume, recording │
      └─────────┬──────────┘             └─────────┬──────────┘
                │                                  │
      ┌─────────▼──────────────────────────────────▼──────────┐
      │              GUARDRAIL LAYER  (SAFE-920)              │
      │  regime enforcement · provenance checks · routine     │
      │  validation · refusal enforcement · FAILS CLOSED      │
      └─────────┬───────────────────────────────────┬─────────┘
                │                                   │
   ┌────────────▼───────────┐          ┌────────────▼──────────┐
   │   ASSIST-REGIME AI     │          │   GUIDE-REGIME AI     │
   │  transform only:       │          │  generate within      │
   │  structure documents,  │          │  safety envelope:     │
   │  simplify, summarize   │          │  routines, personalize│
   └────────────┬───────────┘          └───────────────────────┘
                │
   ┌────────────▼────────────┐
   │  DOCUMENT INGESTION     │  intake → text/region extraction →
   │  + EXTRACTION PIPELINE  │  proposals with sourceExcerptRef
   └────────────┬────────────┘
                │
   ┌────────────▼──────────────────────────────────────────────┐
   │              PROVENANCE-AWARE DATA STORE                  │
   │  Profiles · Documents · Proposals · CarePlanItems ·        │
   │  Measurements · Records · Summaries                       │
   │  ── enforces SAFE-940 / SAFE-1800..1809 invariants ──     │
   └───────────────────────────────────────────────────────────┘
```

### 29.3 Architectural principles (category E — recommendations)

`TECH-900` **The guardrail layer is a first-class component**, not a prompt convention. It
sits between AI and UI and cannot be bypassed (`SAFE-920`, `TECH-922`).

`TECH-901` **The two AI regimes are separately implemented** with separate interfaces and
separate constraints (`SAFE-900`). An ASSIST-regime call must be structurally incapable of
being answered with generated clinical content.

`TECH-902` **Provenance is enforced at the data layer**, not by UI convention. It should be
impossible to persist a health datum without provenance (`SAFE-521`, `SAFE-970`).

`TECH-903` **The input channel is decoupled from request understanding** (`PROD-451`), so
voice availability never gates a core journey.

`TECH-904` **AI provider is abstracted behind an internal interface**, so that provider
choice, and the on-device/cloud split, remain reversible decisions.

`TECH-905` **Document intake mechanism is an explicit design task** and **MUST NOT**
require TV typing (`PROD-410`). Candidate approaches — bundled synthetic documents for the
demo, a local network transfer, a companion upload path, or a pre-seeded store — are to be
compared in the Architecture phase against `PRIV-1620` and demo reliability.

`TECH-906` **The Day/Plan engine is deterministic.** Building the day from confirmed items
is ordinary logic, not an AI task. AI must not be in the path that decides what is on a
user's care plan today.

`TECH-907` **The Session runtime is deterministic.** Timing, advancement and recording are
not AI-driven.

`TECH-930` **Offline-first for the care path.** Confirmed plan, Today, completion tracking
and progress **MUST** function without network (`F-X06`). AI-dependent features degrade
gracefully to presets and confirmed data with an honest message (`PROD-439`).

`TECH-931` **Fail closed on safety, fail open on convenience.** A safety check that cannot
complete blocks the output. A convenience feature that cannot complete degrades quietly.

### 29.4 The platform-target decision (must be made, not assumed)

This is the most consequential architecture decision and is recorded as `OQ-01`. The
research findings that bear on it:

| Finding | Source | Consequence |
|---|---|---|
| Fire TV track accepts **Fire OS or Vega OS** | Official Devpost rules | Both are legitimate. Neither is required. |
| **Vega OS** is Linux-based, replaces Android-based Fire OS on newer devices (e.g. Fire TV Stick 4K Select), and **does not run Android APKs** | Official Amazon developer blog | A Vega app is purpose-built; it is not an Android app. |
| **Vega developer tooling requires macOS 10.15+ or Ubuntu 20.04+; Windows and WSL are not supported** | Official Vega install documentation | **The owner's development machine is Windows 11.** Vega development is therefore not possible on the current machine without a macOS/Linux environment. |
| Fire OS is Android-based | Official Fire TV documentation | Android toolchains are supported on Windows. |
| Official React Native TV, Vega, and Kotlin/Jetpack Compose starter samples exist | Official hackathon resources page | Starting points exist for multiple paths. |
| **Amazon Devices Builder Tools (ADBT)** — an MCP server and Agent Skills integrating Amazon device knowledge into AI coding assistants including Claude Code | Official hackathon resources page | Directly relevant to this project's development method; should be evaluated in the Architecture phase (`TECH-908`). |

`TECH-908` The Architecture phase **MUST** evaluate Amazon Devices Builder Tools (ADBT),
since this project is developed with an AI coding assistant and ADBT is the officially
provided integration for exactly that.

`TECH-940` The platform target **MUST** be decided explicitly in the Architecture phase,
with the Windows-host constraint, device availability, and demo-recording requirements
(`HACK-806`) weighed together. This specification does **not** pre-empt that decision.

**Advisory only (not a decision):** on the evidence above, a **Fire OS (Android-based)**
target is the lower-risk path from a Windows 11 development machine, while a **Vega OS**
target is the more forward-looking platform and would require a macOS or Linux
environment. Either satisfies `HACK-800`.

### 29.5 Deliberately not decided here

Per the product definition, the following are **NOT** chosen in this document and **MUST
NOT** be treated as decided: frontend framework; backend framework (or whether a backend
exists at all); database; AI provider and model; OCR/document-understanding provider; cloud
provider; authentication provider; state management; styling approach; build tooling.

Each is an Architecture-phase decision requiring explicit justification against this
specification.

---

## 30. MVP Scope

### 30.1 MVP principle

`PROD-1900` The MVP **MUST** demonstrate **both** major use cases as realistically as
possible: **(A) Care / Health Companion** and **(B) Wellness / Fitness Companion**. A
submission demonstrating only one is a failure against the product definition.

`PROD-1901` The MVP prioritizes: the actual Fire TV experience; simple navigation; the core
companion experience; meaningful AI interaction; a meaningful user flow; activity/routine
completion; progress; daily summary; and safe handling of health information.

`PROD-1902` **Nothing is deleted for being complex.** Features too large for the MVP move
to Section 31 with their intended role preserved (`RULE-003`).

`PROD-1903` **Smallest implementation that proves the concept** (`RULE-010`). Depth of
experience on the core loop beats breadth of features.

### 30.2 MVP — in scope

**Foundation**

- `F-X01` Profile Select as the entry point
- `F-X02` User-context selection (Care / Wellness / Both)
- `F-X03` Optional D-pad numeric PIN
- `F-X04` Profile switching
- `F-X05` Accessibility and 10-ft UI baseline (Section 12)
- `F-X06` Offline resilience for the care path
- `F-X07` Visible demo-data labelling
- `F-X08` Settings

**Seeded personas (synthetic)**

- One **Care** profile: a post-cardiac-and-stroke-event persona with a synthetic document
  set (discharge-style report, prescription, exercise instructions, diet instructions,
  precautions, follow-up, a lab result).
- One **Wellness** profile.
- Optionally one **Both** profile if it does not compromise depth.

**Care companion (ASSIST)**

- `F-A01` Document intake (mechanism per `TECH-905`; synthetic documents)
- `F-A02` Information extraction into proposals with source references and confidence
- `F-A03` Human review and confirmation — **demonstrated live on at least one document**
- `F-A04`–`F-A09` Medication, prescribed activity, meal, precaution, appointment display;
  Health Info dashboard with full provenance
- `F-A10` Plain-language explanation ("Why this?")
- `F-A11` Care task completion
- `F-A12` New-document change handling (basic)
- `F-A13` Care-team & emergency info card
- `F-A14` Caregiver review on the TV

**Wellness companion (GUIDE)**

- `F-G01` Natural-language request (subject to `TECH-450`; understanding layer required)
- `F-G02` Non-voice request path — **required, always available**
- `F-G03`–`F-G06` Routine generation/selection, preview with total duration, guided session
  player, pause/resume/exit
- `F-G07`, `F-G08` Breathing/relaxation and stretching/mobility routine types
- `F-G09` Precaution-aware gating
- `F-G10` Basic preference memory

**Progress & summary**

- `F-P01`–`F-P05` Activity log, completion view, streak, Daily Summary with four-region
  separation, behavioural insights
- `F-P06` Minimal recorded-information comparison (strictly per `SAFE-1311`)

**AI core**

- `F-AI01`–`F-AI08`, including the **guardrail layer** (`F-AI08`), which is **not
  optional** and **MUST NOT** be deferred (`SAFE-920`)

**Reminders**

- `F-X09` In-app due/overdue surfacing

### 30.3 MVP — explicitly deferred

Deferred to Section 31, **not** removed: remote caregiver companion (`F-A15`); manual
measurement entry (`F-A16`); versioned care-plan timeline (`F-A17`); illustrated exercise
guidance (`F-G11`); spoken coaching cues (`F-G12`); camera-based form feedback (`F-G13`);
weekly summary (`F-P07`); exportable summary (`F-P08`); read-aloud/TTS (`F-AI09`);
multi-language (`F-AI10`); system-level notifications (`F-X10`).

### 30.4 MVP quality bar

The MVP is **done** when Section 40's Definition of Done is satisfied. Specifically, it is
not sufficient for features to exist — the two core journeys (Journeys 2 and 3) must be
**rehearsable end-to-end on the target platform without failure**, because that is what the
submission consists of (`HACK-806`).

`PROD-1910` Depth over breadth: if a choice arises between adding a deferred feature and
making Journeys 2 and 3 reliable and polished, **reliability and polish win**.

---

## 31. Future Scope

Everything here is part of the product vision and is preserved with its intended role. It
is sequenced, not discarded.

### Phase 2 — Deepen the companion

| ID | Item | Intended role |
|---|---|---|
| `FUT-1200` | **Remote caregiver companion** (`F-A15`) | The caregiver is the realistic setup-and-oversight actor. A companion surface lets them add documents, confirm extractions and see adherence without being in the room. **Introduces server-side components and therefore makes `PRIV-1630` authentication mandatory.** |
| `FUT-1201` | **Manual measurement entry** (`F-A16`) | Lets a user or caregiver record a home reading as explicitly self-reported (`SAFE-940` class 2), so the dashboard reflects reality without inventing values. |
| `FUT-1202` | **Illustrated exercise guidance** (`F-G11`) | Visual demonstration substantially improves form and confidence, especially for older users. Deferred because asset production is large. |
| `FUT-1203` | **Spoken coaching cues** (`F-G12`) | Allows a user to look away from the screen mid-movement. Always paired with on-screen text (`PROD-604`) and subject to `PRIV-704`. |
| `FUT-1204` | **Read-aloud / TTS** (`F-AI09`) | Accessibility for low-vision and low reading endurance users. Opt-in for sensitive content (`PRIV-704`). |
| `FUT-1205` | **System-level reminders** (`F-X10`, `FUT-1120`) | The honest path to timely prompting. **Feasibility-gated** on platform support and `SAFE-1100`. |
| `FUT-1206` | **Weekly summary** (`F-P07`) | Week-level reflection; matches the rhythm of weekly checkups. |
| `FUT-1207` | **Exportable summary** (`F-P08`) | Lets the user choose to show a clinician what they actually did. Strictly the user's choice; no automatic transmission. |
| `FUT-1208` | **Richer preference learning** (`F-G10`) | Better personalization within the unchanged `SAFE-030`–`SAFE-037` envelope. |
| `FUT-1209` | **Rich document change diff** (`F-A12`) | Clearer side-by-side handling when a revised prescription arrives. Human decision remains mandatory (`SAFE-506`). |

### Phase 3 — Extend the platform

| ID | Item | Intended role |
|---|---|---|
| `FUT-1300` | **Camera-based form feedback** (`F-G13`) | Computer vision for rep counting and form cues — an explicitly named Fire TV priority area. Requires camera hardware most Fire TV sticks lack, plus a significant new privacy regime (`FUT-1305`). |
| `FUT-1301` | **Versioned care-plan timeline** (`F-A17`) | Full history of how the plan evolved across documents. |
| `FUT-1302` | **Multi-language support** (`F-AI10`) | Directly expands reach for the care use case. |
| `FUT-1303` | **Household multi-profile depth** | Roles, permissions, per-item sensitivity (`FUT-1710`). |
| `FUT-1304` | **Alexa+ / voice-assistant surface** (`TECH-453`) | A natural extension for hands-free interaction, and a separate hackathon track. Additive only; never a dependency of a core journey. |
| `FUT-1305` | **On-device vision privacy regime** | Prerequisite for `FUT-1300`: camera data handling, consent, and shared-room implications. Must precede any camera feature. |

### Phase 4 — Real-world readiness (prerequisites, not features)

| ID | Item | Intended role |
|---|---|---|
| `FUT-1400` | **Formal privacy, security and regulatory assessment** (`FUT-1661`) | **Mandatory before any real patient data is handled.** Jurisdiction- and intended-use specific. |
| `FUT-1401` | **Clinical review of all user-facing health copy** | An independent clinician reviews every string that touches health, to validate the `SAFE-` boundaries in practice. |
| `FUT-1402` | **Accessibility audit** including VoiceView end-to-end (`HACK-417`) | Verifies the Section 5.3 user base is genuinely served. |
| `FUT-1403` | **Extraction accuracy evaluation** | A measured accuracy and failure-mode profile for document extraction, since `SAFE-503` depends on calibrated confidence. |
| `FUT-1404` | **Wearable / device data integration** | Only with a clear user benefit and a clear provenance story (`SAFE-940`). Explicitly **not** pursued for its own sake (`OOS-2010`). |
| `FUT-1405` | **Clinical system / EHR interoperability** | Only if a genuine, consented, standards-based need emerges. Explicitly **not** pursued for its own sake (`OOS-2009`). |

### Preserved-but-unscheduled

`FUT-1500` Multiple care profiles per household with caregiver oversight across them.
`FUT-1501` Medication inventory / refill awareness — **display only**, never a dose or
supply decision (`SAFE-003`).
`FUT-1502` Appointment preparation summaries the user may take to a checkup.
`FUT-1503` Gentle adaptive scheduling that learns when the user actually engages.

---

## 32. Explicit Out-of-Scope

These are things the system **will not do**. This is distinct from Section 31 (deferred but
intended) and Section 8 (what the product is not).

`PROD-2000` **The healthcare / care use case is NOT out of scope.** It is a core pillar
(`ASSIST`) and a primary journey. No implementation phase may reclassify it.

### 32.1 Clinical and safety

| ID | Out of scope |
|---|---|
| `OOS-2001` | Autonomous diagnosis, or any diagnosis (`SAFE-001`). |
| `OOS-2002` | Autonomous treatment decisions, or any treatment decision (`SAFE-002`). |
| `OOS-2003` | Medication dose changes, calculations, conversions or normalization (`SAFE-003`, `SAFE-504`). |
| `OOS-2004` | Emergency medical triage, symptom assessment, urgency classification (`SAFE-013`, `SAFE-014`). |
| `OOS-2005` | Unsupported medical claims of any kind (`SAFE-006`, `SAFE-008`, `HACK-960`). |
| `OOS-2006` | Pretending to replace, speak for, or act with the authority of a doctor (`SAFE-007`). |
| `OOS-2007` | Drug interaction, contraindication, side-effect or substitution information (`SAFE-507`). |
| `OOS-2008` | Clinical reference ranges, targets, or in-range/out-of-range status the product itself computes (`SAFE-1312`). |
| `OOS-2020` | Continuous health monitoring, deterioration detection, or any safety-net function (`SAFE-016`, `SAFE-741`). |
| `OOS-2021` | Mental-health assessment, crisis support, or psychological intervention. |
| `OOS-2022` | Nutrition planning, calorie counting, or meal-plan generation for a Care User (`SAFE-512`). |
| `OOS-2023` | Physiotherapy or rehabilitation programming (`SAFE-031`). |
| `OOS-2024` | Pregnancy, paediatric, or any population-specific clinical guidance. |

### 32.2 Integrations

| ID | Out of scope |
|---|---|
| `OOS-2009` | **Unnecessary** hospital / EHR / clinical-system integrations. |
| `OOS-2010` | **Unnecessary** wearable or medical-device integrations. |
| `OOS-2011` | Pharmacy ordering, prescription fulfilment, or any purchasing of medication. |
| `OOS-2012` | Insurance, billing, claims or payment functionality. |
| `OOS-2013` | Telemedicine, video consultation, or any clinician communication channel. |
| `OOS-2014` | Lab ordering or result retrieval from providers. |

The word *unnecessary* in `OOS-2009` and `OOS-2010` is deliberate and matches the product
definition: these integrations are excluded because they are not needed to prove the
concept, not because they could never have value (`FUT-1404`, `FUT-1405`).

### 32.3 Product surface

| ID | Out of scope |
|---|---|
| `OOS-2015` | **Unnecessary social features** — feeds, sharing, leaderboards, followers, challenges, comparison with other users (`PROD-206`). |
| `OOS-2016` | **Unrelated entertainment features** — media catalogue, content discovery, streaming, games (`PROD-207`). |
| `OOS-2017` | Advertising, sponsored content, or monetization surfaces. |
| `OOS-2018` | Open-domain chatbot conversation (`PROD-202`, Section 17.5). |
| `OOS-2019` | A workout-video library as the primary value (`PROD-203`). |
| `OOS-2025` | Clinician-facing tooling or dashboards (`PROD-200`). |
| `OOS-2026` | Multi-tenant or enterprise healthcare deployment (`PROD-204`). |
| `OOS-2027` | A phone or web application as a primary experience. Fire TV is primary (`PROD-208`, `PROD-400`). Note: `FUT-1200` is a *companion* surface for a caregiver, not a second primary experience. |
| `OOS-2028` | Health-data collection for analytics or model training (`PRIV-601`, `PROD-205`). |
| `OOS-2029` | Any claim of regulatory compliance, clinical validation or certification (`PRIV-1660`, `PRIV-1662`). |

---

## 33. Hackathon Requirements

**Category A only.** Everything in this section was verified on **2026-09-27** against
primary sources: the official Devpost hackathon site (`amazonappdev2026.devpost.com`) and
official Amazon developer documentation (`developer.amazon.com`). Nothing here is inferred.
Where something could not be confirmed from a primary source it appears in Section 39 as an
Open Question, **not** as a requirement.

**Event:** Build, Ship, Shape: Amazon Developer Hackathon
**Primary track for this project:** **Fire TV**

### 33.1 Dates and deadlines

| ID | Requirement |
|---|---|
| `HACK-802` | Submission period: **31 August 2026, 10:15 am PT → 23 October 2026, 12:00 pm PT**. Judging: **9–20 November 2026**. Winners announced **on or around 3 December 2026**. |
| `HACK-830` | Once the submission period has ended, no changes or alterations to the submission may be made. Draft versions may be saved before the deadline. |
| `HACK-831` | AWS promotional credits (up to **$150**) may be requested by registered participants until **21 October 2026, 12:00 pm PT**. |

**Owner note:** as of today (2026-09-27) there are approximately **26 days** until the
submission deadline. This directly justifies `PROD-1903` (smallest implementation that
proves the concept) and `PROD-1910` (depth over breadth).

### 33.2 Track and platform requirement

| ID | Requirement |
|---|---|
| `HACK-803` | Each submission specifies **one primary track**. Mini challenges (AWS Builder, Open Source) are optional and additive. A project can win at most **one track prize and one mini challenge prize**. |
| `HACK-800` | **Fire TV track:** *"Eligible projects for this category have to launch a demo-ready app that works on Fire OS or Vega OS."* |
| `HACK-801` | **Any framework is acceptable** — React Native, Android (Kotlin/Java), or web technologies — provided it runs on Fire OS or Vega OS. Restated in the rules as: *"The requirement is that the project runs on Fire OS or Vega OS."* |
| `HACK-804` | Fire TV **priority areas** named by the organizers: AI-enhanced viewing, **sports**, **fitness**, family entertainment, **multi-modal UX**, computer vision. |

**Alignment note (not a requirement):** this product sits directly in the named
**fitness** and **multi-modal UX** priority areas, with no reshaping of the product
concept required. Computer vision is a credible Phase-3 extension (`FUT-1300`).

### 33.3 Submission requirements

| ID | Requirement |
|---|---|
| `HACK-805` | **Code repository.** A URL to a code repository on GitHub. *"The repository must contain all necessary source code, assets, and instructions required for the project to be functional."* |
| `HACK-805a` | Repository accessibility: **either** public with an open-source license clearly visible in the About section, **or** private and shared with `testing@devpost.com` **and** the named Amazon reviewer GitHub accounts (`chris-trag`, `knmeiss`, `giolaq`, `anishamalde`, `mosesroth`, `emersonsklar`). |
| `HACK-806` | **Demonstration video.** Should be **less than 3 minutes** (*"Judges are not required to watch beyond three minutes"*). Must include footage showing the project **functioning on the device for which it was built**. Must be uploaded and **publicly visible on YouTube or Vimeo**. Must not contain third-party trademarks, copyrighted music, or other copyrighted material without permission. |
| `HACK-806a` | **Fire TV specific:** the demo video must show the project *"running on an actual Fire TV device or the Fire TV/Vega simulator."* |
| `HACK-807` | **Text description** explaining the features and functionality of the project. |
| `HACK-808` | **Product feedback (required).** Describe which developer tools / APIs / SDKs were used; what worked well; what needs improvement; the onboarding experience; and likelihood to build with these tools again. |
| `HACK-809` | **Track identification.** Specify the primary track and any mini challenges entered. |
| `HACK-810` | **English.** All submission materials (video, written description, code documentation) must be in English, or an English translation must be provided. |
| `HACK-811` | **Availability for judging.** The project must be made available free of charge and without restriction for testing, evaluation and use by the Sponsor, Administrator and Judges until the judging period ends, and must be accessible to judges via the repository and demo video. |

### 33.4 Project eligibility requirements

| ID | Requirement |
|---|---|
| `HACK-812` | **Third-party integrations.** *"If a Project integrates any third-party SDK, APIs and/or data, Entrant must be authorized to use them in accordance with any terms and conditions or licensing requirements."* |
| `HACK-813` | **New or significantly updated.** Projects must be newly created, or — if pre-existing — significantly updated after the start of the submission period, with the updates explained and demonstrated. *(This project is new as of 2026-09-27, so this is satisfied by construction.)* |
| `HACK-814` | **Originality and ownership.** The submission must be the entrant's original work product, solely owned by them, and must not violate the intellectual property or other rights of any other person or entity. |
| `HACK-815` | **Open-source use permitted** provided applicable licenses are complied with and the entrant creates software that enhances and builds upon the underlying open-source product. |
| `HACK-816` | **No sponsor-supported derivation.** The project must not have been developed with, or derived from a project developed with, financial or preferential support from the Sponsor or Administrator. |
| `HACK-817` | **Hardware access.** Where a project runs on proprietary or non-widely-available hardware, the Sponsor/Administrator reserve the right to require physical access to the hardware on request. |
| `HACK-818` | **Multiple submissions** are permitted, but each must be unique and substantially different. *(Not applicable — one submission planned.)* |
| `HACK-819` | **Eligibility.** Open to individuals at or above the age of majority in their jurisdiction, teams, and organizations, excluding residents of listed sanctioned/excluded jurisdictions and employees/family of Sponsor, Administrator and Judges. **The owner must confirm personal eligibility against the official rules** (`OQ-11`). |
| `HACK-820` | **IP retained.** *"All Submissions remain the intellectual property of the individuals or organizations that developed them."* Entrants grant the Sponsor a non-exclusive license to use the entry for judging, and Sponsor/Devpost may promote the submission and use contributors' names, likenesses, voices and images in promotional materials during the hackathon period and for three years thereafter. |

### 33.5 Judging criteria (design targets)

Stage One is a pass/fail baseline: the project must reasonably fit the theme and reasonably
apply the required APIs/SDKs. Stage Two uses four **equally weighted** criteria at **25%**
each.

| ID | Criterion (25% each) | Official wording | How this product targets it |
|---|---|---|---|
| `HACK-821` | **Tech Implementation** | *"How well is the project built, and how effectively does it use the required tech? Does it effectively leverage the required APIs, SDKs, or device capabilities for the specified track…"* | Genuine Fire TV app on Fire OS or Vega OS (`HACK-800`); real D-pad focus model; the guardrail layer as substantive engineering (`SAFE-920`); provenance enforced at the data layer (`TECH-902`). |
| `HACK-822` | **Design** | *"Does the project deliver a complete, coherent product experience? Is the interaction model intuitive and well-considered for the target device or platform?"* | Section 12 in full: safe zone, type scale, focus, predictable Back, one primary action per screen, no-typing requirement, calm tone. |
| `HACK-823` | **Potential Impact** | *"Does the project make a credible, specific case for solving customer needs? Could it realistically serve an audience beyond the hackathon?"* | Section 4's problem statement; two concrete personas; a real, large, underserved population (post-event recovery at home) plus a broad wellness audience. |
| `HACK-824` | **Quality of the Idea** | *"Is this a creative, imaginative use of the required tools? Does the team demonstrate a genuine understanding of the developer ecosystem and the end-user needs within their chosen track?"* | Reframing the TV as a care-and-wellness companion; **multi-modal UX** (D-pad-first with voice as enhancement) is a named priority area; the two-regime AI safety model is a distinctive, defensible idea. |
| `HACK-825` | **Tie-breaking** | Tied submissions are compared on the first applicable criterion, then the next; if still tied, judges vote. | — |

### 33.6 Optional scoring opportunities

| ID | Opportunity |
|---|---|
| `HACK-826` | **Friction logs.** *"Submissions with friction log entries score up to 10% bonus,"* applied during Stage 1 downselection and passed to Stage 2 judges. A friction log entry records: task attempted, steps, expected vs actual result, severity, workaround, and an actionable suggestion. **Recommendation:** keep a friction log from the first day of development (`DOD-32`). |
| `HACK-827` | **Feature requests (optional).** Description, importance to the project, and a priority rating (Critical / Important / Nice-to-have). |
| `HACK-828` | **AWS Builder mini challenge (optional).** Incorporate AWS services (e.g. Bedrock, AgentCore, Strands SDK, Kiro, SageMaker) with documented integrations, described in the Product Feedback response. Prize: $5,000 + $5,000 AWS credits. |
| `HACK-829` | **Open Source mini challenge (optional).** Create a new open-source project, or contribute to an existing public repo during the hackathon window, alongside the primary track submission. Requires contribution URL, project repo URL, GitHub username, and a description of the work. Prize: $5,000 + $5,000 AWS credits. |

**Advisory (category E):** the **AWS Builder** mini challenge is a natural fit if a cloud AI
service is chosen in the Architecture phase, and the **Open Source** mini challenge is
satisfiable at low cost if this repository is published under an open-source license
(which also satisfies `HACK-805a` via the public route). Neither is a requirement, and
neither may be allowed to distort the product (`RULE-004`).

### 33.7 Restrictions that were checked and found NOT to exist

Recorded explicitly so that no future work invents a constraint (per the owner's
instruction not to assume prohibition):

| Checked | Finding |
|---|---|
| Publishing to the Amazon Appstore | **Not required by the official rules.** The requirement is a **demo-ready** app plus repository and video. Appstore *content policy* remains relevant as good practice and for any future real publication (`HACK-960`, `HACK-961`). |
| A particular framework or language | **Not required.** Any framework is acceptable if it runs on Fire OS or Vega OS (`HACK-801`). |
| Vega OS specifically | **Not required.** Fire OS is equally eligible (`HACK-800`). |
| Physical Fire TV hardware for the demo | **Not required.** The official Fire TV / Vega **simulator** is explicitly acceptable for the demo video (`HACK-806a`). |
| Use of AWS services | **Not required** for the Fire TV track. Only relevant to the optional AWS Builder mini challenge (`HACK-828`). |
| Alexa integration | **Not required** for the Fire TV track. Alexa+ is a separate track (`HACK-803`). |
| A team (vs. an individual) | **Not required.** Individuals may enter (`HACK-819`). |
| Health/medical app category restrictions in the hackathon rules | **None found.** No hackathon rule was found prohibiting or restricting health-related projects. Appstore content policy on medical claims applies as product discipline (`HACK-960`). |
| Open-source licensing of the project | **Not required** if the private-repo-with-reviewer-access route is used (`HACK-805a`). |

### 33.8 Sources

- Official rules — https://amazonappdev2026.devpost.com/rules
- Official hackathon site — https://amazonappdev2026.devpost.com/
- Official resources — https://amazonappdev2026.devpost.com/resources
- Fire TV Design and User Experience Guidelines — https://developer.amazon.com/docs/fire-tv/design-and-user-experience-guidelines.html
- Fire TV Display and Layout — https://developer.amazon.com/docs/fire-tv/display-and-layout.html
- Fire TV voice-enablement overview — https://developer.amazon.com/docs/fire-tv/voice-enable-your-app-and-content.html
- Accessibility on Amazon Fire devices — https://developer.amazon.com/apps-and-games/blogs/2025/11/guide-to-accessibility-on-amazon-fire-devices
- Building for Fire TV on Vega OS — https://developer.amazon.com/apps-and-games/blogs/2026/07/guide-to-building-for-fire-tv-on-vega-os
- Install the Vega Developer Tools — https://developer.amazon.com/docs/vega/0.23/install-vega-sdk.html
- Amazon Appstore Restricted Content Policy — https://developer.amazon.com/docs/policy-center/restricted-content.html
- Amazon Appstore Content Policy — https://developer.amazon.com/docs/policy-center/understanding-content-policy.html

---

## 34. Demo Requirements

The demo is the submission. This section is a product requirement derived from
`HACK-806`/`HACK-806a`, and it constrains what must be built.

### 34.1 Hard constraints

| ID | Requirement |
|---|---|
| `HACK-806` | Video **under 3 minutes**, publicly visible on YouTube or Vimeo, showing the project functioning on its target device. |
| `HACK-806a` | Footage must show the app running on an **actual Fire TV device or the official Fire TV / Vega simulator**. Screen mock-ups, design renders, or a desktop browser window are **not** acceptable evidence. |
| `HACK-806b` | No third-party trademarks, copyrighted music, or copyrighted material without permission. **Use silence, original audio, or explicitly licensed audio.** |
| `PROD-2100` | The demo **MUST** show **both** core journeys — care companion and wellness companion — because both are core to the product (`PROD-1900`). |

### 34.2 Required demo content

`PROD-2101` The demo **MUST** include, at minimum:

1. **The care journey (Journey 2):** Profile Select → Today with a Now card carrying visible
   source and date → acting on a medication item → "Why this?" plain-language explanation →
   completion → a prescribed activity with its precaution.
2. **The document-to-plan moment:** at least one document's extracted proposal shown beside
   its source text, in **Needs Review**, being **confirmed by a human**, and then appearing
   in the plan. This is the product's central trust mechanism (`SAFE-501`) and its most
   distinctive engineering claim — it must be visible, not described.
3. **The wellness journey (Journey 3):** a request stated for a 10–20 minute window → the
   proposed routine with segment durations and explicit total → the guided session player
   running with automatic advancement → completion recorded.
4. **The Daily Summary** showing the four-region separation (`SAFE-1410`) — specifically,
   AI-generated text visibly distinct from recorded facts.
5. **Evidence of the safety boundary:** at least one moment demonstrating a refusal or a
   provenance guarantee — e.g. an out-of-scope clinical question being declined and
   redirected, or a historical value shown with its date and explicitly not as a current
   reading.

`PROD-2102` The demo **MUST** be executed on the **non-voice path** for at least the
wellness request, to evidence `PROD-403`. Voice, if implemented, is shown as an addition.

### 34.3 Demo integrity requirements

| ID | Requirement |
|---|---|
| `PRIV-981` | All data shown **MUST** be synthetic and **MUST** be visibly identified as demo data (`HACK-980`). No real person's records, names, or documents. |
| `SAFE-2110` | Narration and on-screen text **MUST NOT** make any medical claim or imply clinical capability (`SAFE-962`, `HACK-960`). Describe it as organizing information a doctor provided — never as managing, monitoring, or improving health. |
| `PROD-2111` | The demo **MUST NOT** show functionality that does not exist. No staged screens, no simulated results presented as real behaviour. |
| `PROD-2112` | The demo **MUST** be **rehearsed end-to-end** on the target platform before recording. Both core journeys must run without failure (`PROD-1910`). |
| `PRIV-2113` | No API keys, credentials, personal email addresses, or private paths may be visible in any frame (`PRIV-1640`). |

### 34.4 Repository readiness for judging

| ID | Requirement |
|---|---|
| `HACK-805` | The repository **MUST** contain all source code, assets, and the instructions required to make the project functional. |
| `PROD-2120` | A `README.md` **MUST** provide: what the product is; the safety boundary stated plainly; setup and run instructions that a judge can follow; how to run the demo personas; an explicit statement that all data is synthetic; and the platform target and how to launch it (device or simulator). |
| `HACK-805a` | Repository access **MUST** be configured by the deadline via one of the two permitted routes. **This is a submission-blocking step, not a formality.** |
| `HACK-808` | The product feedback response **MUST** be written. It is a required submission field and is also where the AWS Builder mini challenge is described if entered (`HACK-828`). |
| `HACK-826` | A friction log **SHOULD** be maintained from day one, given the stated bonus. |

### 34.5 Timing advisory (category E)

`TECH-2130` Under 3 minutes covering two journeys is tight. Recommended allocation:
~20s framing the problem; ~70s care journey including the confirmation moment; ~50s
wellness journey; ~20s summary and safety boundary; ~10s close. **Build the demo script
early and let it inform build priority** — this is the practical mechanism for enforcing
`PROD-1910`.

---

## 35. Product Success Criteria

### 35.1 Product-quality criteria (measurable)

| ID | Criterion | Target |
|---|---|---|
| `SC-01` | Time to answer "what do I do now?" from Today appearing | ≤ 5 seconds, no navigation (`PROD-100`) |
| `SC-02` | Remote actions to start a wellness session from Today (preset path) | ≤ 3 (`PROD-120`) |
| `SC-03` | Remote actions to reach any MVP destination from Today | ≤ 3 (`PROD-432`) |
| `SC-04` | Care items rendered without visible source and date | **0** (`PROD-102`, `SAFE-521`) |
| `SC-05` | Generated routine total duration vs requested budget | Within defined tolerance (`PROD-121`) |
| `SC-06` | Guided session completable without mid-session remote input | Yes (`PROD-122`) |
| `SC-07` | Interactive elements unreachable by D-pad | **0** (`HACK-414`, `PROD-150`) |
| `SC-08` | Screens with elements in the outer 5% safe-zone margin | **0** (`HACK-410`) |
| `SC-09` | Body text below 14sp | **0** (`HACK-411`) |
| `SC-10` | Core journeys completable with voice fully disabled | Both (`PROD-151`, `PROD-403`) |
| `SC-11` | Keyboard text entry required in any core journey | **None** (`PROD-410`) |
| `SC-12` | Core care path functional with no network | Yes (`F-X06`, `TECH-930`) |

### 35.2 Safety criteria (zero-tolerance — any failure blocks release)

| ID | Criterion | Target |
|---|---|---|
| `SC-20` | Invented clinical content, doctor instructions, or health values across the full demo path | **0** (`SAFE-140`) |
| `SC-21` | Extracted items reaching the plan without human confirmation | **0** (`SAFE-501`) |
| `SC-22` | Dose strings altered, recomputed or normalized | **0** (`SAFE-504`) |
| `SC-23` | Historical values presented as current | **0** (`SAFE-520`) |
| `SC-24` | AI-generated content visually indistinguishable from confirmed clinical information | **0** (`SAFE-141`) |
| `SC-25` | Out-of-scope clinical questions answered rather than refused and redirected | **0** (`SAFE-916`) |
| `SC-26` | Clinical improvement/deterioration claims in summaries or insights | **0** (`SAFE-703`) |
| `SC-27` | Generated routines containing `SAFE-034` prohibited movements | **0** (`SAFE-917`) |
| `SC-28` | AI outputs reaching the UI without passing the guardrail layer | **0** (`SAFE-920`) |

### 35.3 Privacy criteria (zero-tolerance)

| ID | Criterion | Target |
|---|---|---|
| `SC-30` | Real patient data in the repository | **0** (`HACK-980`) |
| `SC-31` | Secrets or API keys in code, config, or commit history | **0** (`PRIV-1640`) |
| `SC-32` | Health information in logs, crash reports or diagnostics | **0** (`PRIV-1650`) |
| `SC-33` | Health information visible before profile entry | **0** (`PRIV-702`) |
| `SC-34` | Health information reachable across profiles | **0** (`PRIV-1511`) |
| `SC-35` | Unlabelled synthetic data | **0** (`PRIV-981`) |

### 35.4 Hackathon criteria

| ID | Criterion |
|---|---|
| `SC-40` | Runs on Fire OS or Vega OS and is demonstrated on a real device or the official simulator (`HACK-800`, `HACK-806a`). |
| `SC-41` | All six mandatory submission elements complete before the deadline (Section 33.3). |
| `SC-42` | Demo video under 3 minutes, publicly visible, showing both core journeys (`HACK-806`, `PROD-2100`). |
| `SC-43` | Repository accessible to judges via a permitted route (`HACK-805a`). |

### 35.5 Qualitative success

`SC-50` A person matching Persona A, shown the Today screen without explanation, can state
what they need to do next.
`SC-51` A person matching Persona B completes a session on first use without assistance.
`SC-52` A clinician reviewing the care surfaces would not object to what is shown to the
patient — because nothing clinical originates in the product.
`SC-53` A caregiver reviewing the confirmation flow trusts that nothing entered the plan
without a human checking it.
`SC-54` The product feels like a calm companion, not a hospital system, a chatbot, or a
workout-video app (`PROD-202`, `PROD-203`, `PROD-200`).

---

## 36. Development Principles

These are binding on all development.

| ID | Principle |
|---|---|
| `DP-01` | **This document is the product source of truth.** Where code and this document disagree, this document is correct and the code is a defect — unless the owner has approved a change here first. |
| `DP-02` | **Phase by phase.** Implement in the order established by MVP scope and the demo script. Do not begin a later phase while a core journey is unreliable. |
| `DP-03` | **Smallest implementation that proves the concept** (`RULE-010`). |
| `DP-04` | **Depth over breadth** (`PROD-1910`). A reliable, polished core loop beats more features. |
| `DP-05` | **Safety is not a phase.** `SAFE-` requirements are implemented alongside the features they govern, never deferred to a hardening pass. The guardrail layer ships with the first AI feature. |
| `DP-06` | **Provenance first.** Build the provenance-carrying data model before building any surface that displays health information. Retrofitting provenance is not acceptable. |
| `DP-07` | **Fire TV first, always.** Every UI decision is evaluated at 10 feet with a D-pad, not on a development monitor with a mouse. Test focus traversal as you build, not at the end. |
| `DP-08` | **Explain major architectural changes before making them** (`RULE-012`). |
| `DP-09` | **Clearly identify mock, seed and demo data** (`RULE-013`, `PRIV-981`). |
| `DP-10` | **Maintain separation between verified data and AI-generated content** (`RULE-014`, `SAFE-940`). |
| `DP-11` | **Maintain safety and privacy boundaries throughout development** (`RULE-015`) — including in scratch code, debug screens and test fixtures. A debug screen that dumps clinical data violates `PRIV-1650`. |
| `DP-12` | **No unrequested features, refactors or abstractions.** Three similar lines beat a premature abstraction. |
| `DP-13` | **No backwards-compatibility shims or dead code.** This is a new project with no users; delete rather than deprecate. |
| `DP-14` | **Test the boundaries, not just the happy path.** Every `SAFE-` requirement with a zero-tolerance criterion in Section 35.2 needs a test that would fail if the boundary broke. |
| `DP-15` | **Rehearse the demo continuously.** From the first working screen, the demo path is the integration test (`PROD-2112`). |
| `DP-16` | **Keep a friction log from day one** (`HACK-826`). |
| `DP-17` | **Verify platform claims against official documentation** before relying on them. Fire OS and Vega OS differ materially; assumptions carried from general Android or web development may be wrong. |

---

## 37. Claude Code Rules

Binding operating rules for any AI development agent working on this project. These
restate the owner's development principles and add the operational detail needed to follow
them.

### 37.1 The fifteen rules

| ID | Rule |
|---|---|
| `RULE-001` | **`PROJECT_MASTER_SPEC.md` is the product source of truth.** Read it before making product decisions. Cite requirement IDs when implementing or when explaining a choice. |
| `RULE-002` | **Do not change the product concept without explicit approval.** The pillars (Section 9), the two situations (Section 6), the user types (Section 25), the Fire TV-first stance (Section 12) and the safety boundaries (Section 18) are fixed. |
| `RULE-003` | **Do not remove major features silently.** If something cannot be built now, move it to Section 31 with its role preserved and **say so explicitly**. |
| `RULE-004` | **Do not add unrelated features.** Including features that might score well in the hackathon but are not in this specification. |
| `RULE-005` | **Do not redesign the product during implementation.** If implementation reveals that a requirement is wrong, stop and raise it. Do not resolve it unilaterally. |
| `RULE-006` | **Do not make unsupported medical claims** — in code, copy, comments, commit messages, README, demo narration or store metadata (`SAFE-962`). |
| `RULE-007` | **Do not invent health data.** No placeholder vitals that look real, no filled-in gaps, no plausible-looking defaults. Absent means absent (`SAFE-502`). |
| `RULE-008` | **Do not invent doctor instructions.** Not in seed data presented as clinical, not in prompts, not in fallbacks (`SAFE-005`). |
| `RULE-009` | **Keep Fire TV as the primary experience.** Do not build a web app first and adapt it. Do not add a second primary platform (`PROD-400`, `OOS-2027`). |
| `RULE-010` | **Prefer the smallest implementation that proves the product concept.** |
| `RULE-011` | **Implement phase by phase.** Do not begin Section 31 work while Section 30 is incomplete. |
| `RULE-012` | **Explain major architectural changes before making them.** State what changes, why, what it affects, and what the alternatives were. Then wait. |
| `RULE-013` | **Clearly identify mock, seed and demo data** at the data layer and in the UI (`PRIV-981`). |
| `RULE-014` | **Maintain separation between verified data and AI-generated content** (`SAFE-940`). This separation must be visible in the code structure, not only in the rendered output. |
| `RULE-015` | **Maintain safety and privacy boundaries throughout development**, including in temporary, debug and test code. |

### 37.2 Operational rules

| ID | Rule |
|---|---|
| `RULE-020` | **No code before approval.** No application code, scaffolding, dependency installation, or project initialization until this document is approved and an `ARCHITECTURE_SPEC.md` is approved. |
| `RULE-021` | **No competing specifications.** Do not create additional product specs, alternative plans, or parallel design documents. This file is the single product spec; the architecture spec is the single architecture document. |
| `RULE-022` | **No unnecessary files.** No summary documents, status reports, notes files, or analysis documents unless the owner asks. |
| `RULE-023` | **Do not lock a technology choice that Section 29.5 leaves open** without raising it and getting approval. |
| `RULE-024` | **Prompt instructions are not a safety implementation.** Every `SAFE-` requirement needs enforcement in code, not only in a prompt (`TECH-922`). |
| `RULE-025` | **Never commit secrets.** Verify before every commit (`PRIV-1640`). |
| `RULE-026` | **Never place real patient data in the repository** (`HACK-980`). |
| `RULE-027` | **Verify Fire TV and Vega platform claims against official documentation.** Do not rely on general Android or web knowledge, or on memory, for platform behaviour (`DP-17`). |
| `RULE-028` | **When uncertain about a product question, ask.** When uncertain about a safety question, **choose the more conservative option and flag it**. Never resolve a safety ambiguity toward more capability. |
| `RULE-029` | **Test on the target platform, not only in a development environment.** A screen that has never rendered on Fire TV or the simulator is unverified (`DP-07`). |
| `RULE-030` | **Do not claim a feature works without having run it.** Type-checking and unit tests verify code, not product behaviour. |

### 37.3 Escalation triggers — stop and ask

An agent **MUST** stop and consult the owner when any of the following arises:

1. A requirement in this document appears wrong, contradictory, or impossible.
2. A `SAFE-` requirement appears to conflict with a feature requirement.
3. A technology decision left open in Section 29.5 needs to be made.
4. An Open Question from Section 39 becomes blocking.
5. The platform target decision (`OQ-01`) needs resolving.
6. A feature turns out to be infeasible within the timeline.
7. Scope needs to change to meet the deadline.
8. Any change to Sections 6, 9, 12, 18, 25, 30 or 32 seems warranted.

---

## 38. Risks

Each risk has an ID, an assessment, and a mitigation. Ordered by severity.

### 38.1 Safety risks

| ID | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| `R-01` | **AI generates or implies clinical content** — a hallucinated instruction, an invented value, an unsupported reassurance. | **Critical** — the product's central promise fails; potential real harm if used with real data. | Medium without controls | The two-regime model (`SAFE-900`); guardrail layer that fails closed (`SAFE-920`); ASSIST-regime AI constrained to transform confirmed text only (`SAFE-915`); zero-tolerance criteria `SC-20`–`SC-28` with tests (`DP-14`). |
| `R-02` | **Document extraction error reaches the plan** — a misread dose or frequency. | **Critical** | Medium-high (OCR and extraction are imperfect) | Mandatory human confirmation (`SAFE-501`); source text shown beside every proposal (`PROD-621`); `UNCLEAR` rather than guessing (`SAFE-503`); dose text never normalized (`SAFE-504`); one-item-at-a-time review that resists press-through (`SAFE-1522`). |
| `R-03` | **User over-trusts the product** and treats it as clinical authority or a safety net. | **High** | Medium | Explicit in-context transparency (`SAFE-950`); prohibition on overstating role (`SAFE-952`, `SAFE-741`); refusals that redirect to the clinician (`SAFE-916`); calm non-authoritative tone. |
| `R-04` | **Historical value read as a current measurement.** | **High** | Medium | `SAFE-520`, `SAFE-931`, `SAFE-1804`; observation date mandatory and always displayed; recency window defined per measure (`TECH-974`). |
| `R-05` | **Generated wellness routine unsafe for a recovering user.** | **High** | Low-medium | Conservative envelope (`SAFE-030`–`SAFE-037`); deterministic validation before display (`SAFE-917`); precaution surfacing (`SAFE-032`); extra conservatism for Care/Both users (`SAFE-037`); standing stop instruction (`SAFE-606`). |
| `R-06` | **Reminder reliability is over-promised**, and a user relies on the TV to prompt a dose. | **High** | Medium | `TECH-460`, `SAFE-1100`: no alerting claim; in-app surfacing only in MVP; out-of-app notification explicitly feasibility-gated (`FUT-1120`). |

### 38.2 Privacy risks

| ID | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| `R-07` | **Health information disclosed on a shared screen** to other household members or visitors. | High | Medium-high (inherent to the medium) | Section 27 in full: profile gate (`PRIV-700`), no pre-entry disclosure (`PRIV-702`), optional PIN (`PRIV-701`), idle return to non-disclosing state (`PRIV-1701`), non-specific ambient surfaces (`PRIV-1130`), opt-in spoken output (`PRIV-704`). |
| `R-08` | **Clinical text sent to a third-party AI/OCR provider** whose terms permit training on it. | High | Medium | `PRIV-1622`: disclosure, minimum content, mandatory terms review; providers permitting training on submitted content are excluded. Recorded as `OQ-06`. |
| `R-09` | **Secrets or clinical data leak via the repository, logs, or the demo video.** | High | Medium | `PRIV-1640`–`PRIV-1652`, `PRIV-2113`; pre-submission scan (`DOD-13`); verbose logging off in the submitted build. |

### 38.3 Platform and technical risks

| ID | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| `R-10` | **Windows development host cannot build for Vega OS** — official Vega tooling requires macOS 10.15+ or Ubuntu 20.04+; Windows and WSL are not supported. The owner's machine is Windows 11. | **High** — could invalidate a platform choice late | **Confirmed constraint**, not a possibility | Treat as a primary input to the platform decision (`OQ-01`, `TECH-940`). Fire OS is equally eligible (`HACK-800`) and Android tooling is supported on Windows. Decide **before** any code is written. |
| `R-11` | **No physical Fire TV device available**, risking an unconvincing demo. | High | Medium | The official simulator is explicitly acceptable for the demo (`HACK-806a`). Confirm simulator availability for the chosen target early (`OQ-02`). |
| `R-12` | **Free-form voice input is not available on Fire TV**, undermining a headline interaction. | Medium | **Likely** — no official API was found (`TECH-450`) | Input channel decoupled from understanding (`PROD-451`, `TECH-903`); non-voice path is mandatory and complete (`PROD-403`, `F-G02`); demo runs on the non-voice path (`PROD-2102`). Voice becomes an enhancement, not a dependency. |
| `R-13` | **Timeline** — approximately 26 days remain to the deadline for a product with two full journeys, a document pipeline, and a guardrail layer. | **High** | **High** | `PROD-1903`, `PROD-1910`, `DP-04`: smallest implementation, depth over breadth. Demo script drives build order (`TECH-2130`, `DP-15`). Section 30.3 deferrals are already aggressive and must be respected. |
| `R-14` | **Document pipeline consumes disproportionate effort** relative to its share of the demo. | Medium-high | Medium-high | Scope it to the seeded synthetic document set; confirmation UX matters more to the judging criteria than extraction breadth; pre-processed proposals are an acceptable MVP fallback provided the **confirmation gate is real and demonstrated live**. |
| `R-15` | **10-ft UI is underestimated** and the result reads as a web app on a TV. | Medium-high (directly hits the 25% Design criterion) | Medium | Section 12 as a hard checklist; `SC-07`–`SC-09` as verifiable gates; test focus traversal continuously (`DP-07`, `RULE-029`). |
| `R-16` | **Offline/degraded paths untested**, and the demo fails on a network hiccup. | High (demo-fatal) | Medium | `TECH-930`, `F-X06`; Journey 7 degraded paths are specified, not incidental; rehearse the demo offline. |
| `R-17` | **AI latency breaks the 10-ft experience** — a user waiting on a TV with no feedback. | Medium | Medium | `PROD-439` honest loading states with timeout paths; deterministic Day/Plan and Session engines keep AI off the critical path (`TECH-906`, `TECH-907`); preset fallbacks. |

### 38.4 Product and submission risks

| ID | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| `R-18` | **Scope drift toward a generic fitness app**, because wellness is easier to build than the care pipeline. | **High** — loses the product's distinctiveness and violates the owner's explicit instruction | Medium | `RULE-002`, `RULE-003`, `PROD-1900`; the demo must show both journeys (`PROD-2100`); the care journey gets the larger demo allocation (`TECH-2130`). |
| `R-19` | **Submission mechanics missed** — repository access not configured, video not public, product feedback not written. | **Critical** — disqualification or unjudged submission | Medium (easy to leave to the end) | Section 40 Definition of Done treats each as a blocking item (`DOD-21`–`DOD-33`); `HACK-805a` flagged as submission-blocking. |
| `R-20` | **Demo video exceeds 3 minutes** or fails to show the device. | High | Medium | `TECH-2130` allocation; `HACK-806a` as a recording requirement; rehearse to time. |
| `R-21` | **Copyrighted music in the demo video.** | Medium-high | Medium | `HACK-806b`: silence, original, or explicitly licensed audio only. |
| `R-22` | **App name or description reads as a clinical claim**, engaging Appstore metadata policy. | Medium | Low-medium | `HACK-961`, `SAFE-963`; recorded as `OQ-09` for owner decision. |
| `R-23` | **Two use cases produce an incoherent product** that serves neither well. | Medium-high (hits the Design criterion) | Medium | `PROD-030` visual/structural distinction; `PROD-503` context-aware surfaces; Today as the single convergence point (`PROD-500`); Journey 4 specified explicitly. |

---

## 39. Open Questions

Each question blocks something specific. **Owner decisions are marked.** Questions marked
*Architecture phase* are to be resolved in `ARCHITECTURE_SPEC.md`.

### 39.1 Blocking — must be resolved before the Architecture Specification

| ID | Question | Why it matters | Resolve by |
|---|---|---|---|
| `OQ-01` | **Fire OS or Vega OS?** | The single most consequential decision. Both are eligible (`HACK-800`). Vega does not run Android APKs and its tooling **requires macOS or Linux** — the development machine is Windows 11 (`R-10`). Fire OS is Android-based and supported on Windows. | **Owner + Architecture phase**, before any code |
| `OQ-02` | **Is a physical Fire TV device available? If not, is the official simulator for the chosen target usable on the development machine?** | `HACK-806a` requires footage on a device or the official simulator. Note the Vega Virtual Device inherits the macOS/Linux host constraint. | **Owner**, immediately |
| `OQ-03` | **Is a macOS or Linux environment available** (machine, VM, or cloud host) if Vega OS is chosen? | Determines whether `OQ-01` is genuinely open or effectively decided. | **Owner**, immediately |
| `OQ-04` | **On-device only, or a server component?** | Drives `PRIV-1610`, `PRIV-1630`, `PRIV-1640` and overall complexity against a 26-day timeline. An on-device-only MVP is materially simpler and more privacy-protective. | Architecture phase |
| `OQ-05` | **What voice capability is actually available** to an app on the chosen target for free-form natural-language input? | `TECH-450`: no official API was found. Determines whether voice is demonstrable at all. Must not block core journeys either way (`PROD-451`). | Architecture phase, against current official docs |
| `OQ-06` | **Which AI provider, and do its terms permit sending clinical text?** | `PRIV-1622` excludes providers that may train on submitted content. Also determines on-device vs cloud and latency (`R-17`). | Architecture phase |
| `OQ-07` | **If a credentialed external service is used, how is the credential kept out of the client?** | `PRIV-1640` is absolute. May force `OQ-04` toward a server component. | Architecture phase |

### 39.2 Product decisions — owner

| ID | Question | Context | Default if undecided |
|---|---|---|---|
| `OQ-08` | **Should the product adopt the stricter health-app obligations described by secondary sources** (explicit diagnosis disclaimer, accuracy-claim substantiation) even though they were not confirmed verbatim in primary Amazon policy? | Section 18.5. The product's own `SAFE-` rules already meet or exceed them. | **Yes** — adopt them as product discipline. No cost, and it reduces `R-22`. |
| `OQ-09` | **Should the user-facing display name and description differ from the internal project name "AI Assistant Healthcare"?** | `HACK-961`: Appstore content policy applies to titles and descriptions. A name implying clinical capability invites scrutiny (`R-22`). | Keep "AI Assistant Healthcare" as the internal project name; decide the display name before any store-facing metadata exists. **No change without owner approval** (`RULE-002`). |
| `OQ-10` | **Enter the optional mini challenges** (AWS Builder `HACK-828`, Open Source `HACK-829`)? | Additive prizes; Open Source is near-free if the repo is public, which also satisfies `HACK-805a`. Neither may distort the product (`RULE-004`). | Decide once `OQ-04`/`OQ-06` are settled. Do not let either shape the product. |
| `OQ-11` | **Confirm personal eligibility** against the official rules (jurisdiction, age of majority, no conflict of interest). | `HACK-819`. A late discovery here wastes the entire effort. | **Owner, immediately.** |
| `OQ-12` | **Is a third seeded "Both" persona worth building**, or do two personas (Care, Wellness) serve the demo better? | Journey 4 is specified, but demo time is scarce (`TECH-2130`) and depth beats breadth (`PROD-1910`). | Two personas for the MVP; add Both only if it does not reduce polish. |
| `OQ-13` | **Is pre-processing the synthetic documents acceptable for the MVP**, provided the human confirmation gate is real and demonstrated live? | `R-14`. Keeps the safety-critical mechanism intact while controlling pipeline effort. | Acceptable, **only** if the confirmation gate is genuinely functional and shown in the demo (`PROD-2101` item 2). |
| `OQ-14` | **Does the caregiver need a distinct on-TV role in the MVP**, or is a single profile-level actor sufficient? | `PROD-1521`. A permission split adds complexity for limited demo value. | Single actor for MVP; `FUT-1200` carries the real split. |

### 39.3 Design detail — Architecture / design phase

| ID | Question |
|---|---|
| `OQ-20` | Recency window per measure type, for historical-vs-current presentation (`TECH-974`). |
| `OQ-21` | Duration tolerance for generated routines vs the requested budget (`PROD-121`). |
| `OQ-22` | Idle timeout duration and return target for care surfaces (`TECH-1702`). |
| `OQ-23` | Document intake mechanism (`TECH-905`) — bundled assets, local transfer, companion upload, or pre-seeded store. |
| `OQ-24` | Day rollover boundary and how unmarked items are recorded at end of day (`PROD-1015`). |
| `OQ-25` | Whether Amazon Devices Builder Tools (ADBT) is adopted for development (`TECH-908`). |
| `OQ-26` | Exact type scale, colour tokens and focus treatment satisfying `HACK-410`–`HACK-415` and `PROD-434`, `PROD-435`. |
| `OQ-27` | Whether VoiceView support is in MVP scope or Phase 4 (`HACK-417`, `FUT-1402`). |

---

## 40. Definition of Done

The project is **done** when every item below is satisfied. Each item is blocking. Items are
grouped, and each cites what it verifies.

### 40.1 Product completeness

| ID | Item | Verifies |
|---|---|---|
| `DOD-01` | Both core journeys — care companion (Journey 2) and wellness companion (Journey 3) — run end-to-end on the target platform without failure. | `PROD-1900`, `PROD-2112` |
| `DOD-02` | The document-to-plan flow works: intake → extraction → proposal with source reference → **human confirmation** → appears in the plan. | `F-A01`–`F-A03`, `SAFE-501` |
| `DOD-03` | All MVP features in Section 30.2 are implemented, or a deferral has been explicitly raised and approved (`RULE-003`). | Section 30.2 |
| `DOD-04` | All three user contexts (Care / Wellness / Both) are selectable and produce correctly differentiated surfaces. | `PROD-1500`, `PROD-503` |
| `DOD-05` | The Daily Summary renders with the four regions visibly separated. | `SAFE-1410` |
| `DOD-06` | Degraded paths behave as specified — no network, unreadable document, no voice, repeated Back, interrupted session, empty state. | Journey 7 |

### 40.2 Fire TV experience

| ID | Item | Verifies |
|---|---|---|
| `DOD-07` | Full D-pad traversal of every screen: every interactive element reachable, focus always visible, focus never lost. | `HACK-413`, `HACK-414`, `PROD-440`, `SC-07` |
| `DOD-08` | Safe zone verified at 1080p — nothing in the outer 5%. | `HACK-410`, `SC-08` |
| `DOD-09` | No body text below 14sp; primary card text substantially above the minimum. | `HACK-411`, `PROD-434`, `SC-09` |
| `DOD-10` | Both journeys completed with voice fully disabled, and with no keyboard text entry. | `PROD-403`, `PROD-410`, `SC-10`, `SC-11` |
| `DOD-11` | Back behaves predictably from every screen, including mid-session. | `PROD-430` |
| `DOD-12` | No status encoded in colour alone; colour treatment follows official guidance. | `PROD-435`, `HACK-415` |

### 40.3 Safety and privacy

| ID | Item | Verifies |
|---|---|---|
| `DOD-13` | **All Section 35.2 safety criteria met at zero.** Each has a test that would fail if the boundary broke. | `SC-20`–`SC-28`, `DP-14` |
| `DOD-14` | **All Section 35.3 privacy criteria met at zero**, including a repository scan for secrets and real patient data. | `SC-30`–`SC-35`, `PRIV-1641` |
| `DOD-15` | The guardrail layer is implemented in code (not prompts alone), fails closed, and no AI output reaches the UI without passing it. | `SAFE-920`, `SAFE-921`, `TECH-922`, `RULE-024` |
| `DOD-16` | The `SAFE-940` separation invariant is expressible and enforced at the data layer; no code path can promote AI-generated content to confirmed clinical information. | `SAFE-940`, `SAFE-1800`, `TECH-902` |
| `DOD-17` | Every health value displayed carries source, date and context; no card renders without provenance. | `SAFE-970`, `SAFE-521`, `SC-04` |
| `DOD-18` | Transparency statements appear in first-run orientation and remain accessible from Settings. | `SAFE-950`, `SAFE-951` |
| `DOD-19` | Verbose and AI request/response logging are off in the submitted build. | `PRIV-1651`, `PRIV-1652` |
| `DOD-20` | All data is synthetic and visibly labelled as demo data. | `HACK-980`, `PRIV-981` |

### 40.4 Hackathon submission (each item is submission-blocking)

| ID | Item | Verifies |
|---|---|---|
| `DOD-21` | App runs on **Fire OS or Vega OS** and has been run on a real Fire TV device or the official Fire TV / Vega simulator. | `HACK-800`, `HACK-806a` |
| `DOD-22` | **Repository** contains all source code, assets and functional instructions, with a `README.md` per `PROD-2120`. | `HACK-805`, `PROD-2120` |
| `DOD-23` | **Repository access configured** by one permitted route — public with a visible open-source license, **or** private and shared with `testing@devpost.com` plus the named Amazon reviewer accounts. | `HACK-805a` |
| `DOD-24` | **Demo video** under 3 minutes, publicly visible on YouTube or Vimeo, showing the app running on the device/simulator, covering both journeys and the confirmation moment, with no copyrighted audio. | `HACK-806`, `HACK-806b`, `PROD-2100`, `PROD-2101` |
| `DOD-25` | **Text description** of features and functionality written. | `HACK-807` |
| `DOD-26` | **Product feedback** response written, covering tools used, what worked, what needs improvement, onboarding, and likelihood to build again. | `HACK-808` |
| `DOD-27` | **Track identified** as Fire TV, with any mini challenges declared. | `HACK-809` |
| `DOD-28` | All materials in **English**. | `HACK-810` |
| `DOD-29` | Project is **free and accessible** to judges for testing through the end of the judging period. | `HACK-811` |
| `DOD-30` | Third-party SDK / API / data usage is authorized and license-compliant; any open-source licenses are complied with. | `HACK-812`, `HACK-815` |
| `DOD-31` | No API keys, credentials, personal addresses or private paths visible in any video frame. | `PRIV-2113` |
| `DOD-32` | **Friction log** maintained and submitted, for the stated bonus. | `HACK-826` |
| `DOD-33` | Submitted before **23 October 2026, 12:00 pm PT**. No changes possible after. | `HACK-802`, `HACK-830` |

### 40.5 Documentation and governance

| ID | Item | Verifies |
|---|---|---|
| `DOD-34` | `ARCHITECTURE_SPEC.md` exists, was approved before implementation, and records the resolution of every blocking Open Question in Section 39.1. | `RULE-020`, `RULE-023` |
| `DOD-35` | No unapproved deviation from this document exists. Where implementation diverged, this document was updated with owner approval first. | `DP-01`, `RULE-002` |
| `DOD-36` | No competing specification or unnecessary documentation files were created. | `RULE-021`, `RULE-022` |
| `DOD-37` | Every deferred feature is recorded in Section 31 with its intended role preserved — none silently deleted. | `RULE-003`, `PROD-1902` |

---

## Appendix A — Final validation against the owner's checklist

Performed before finalizing this document, as required.

| # | Check | Status | Where satisfied |
|---|---|---|---|
| 1 | Healthcare / care use case preserved | **PASS** | Pillar ASSIST (§9); Situation 1 (§6.1); §15; Journeys 1, 2, 6; `PROD-2000` states it is explicitly **not** out of scope |
| 2 | Wellness / fitness use case preserved | **PASS** | Pillar GUIDE (§9); Situation 2 (§6.2); §16; Journey 3 |
| 3 | Fire TV remains the primary platform | **PASS** | `PROD-400`, `PROD-401`; §12 in full; §13, §14; `OOS-2027` |
| 4 | Companion concept preserved | **PASS** | §2, §3; `PROD-202`, `PROD-203`, `PROD-200`; `SC-54` |
| 5 | Doctor-provided information remains an important source | **PASS** | `PROD-010`–`PROD-013`; `SAFE-500`; §19; the confirmation gate (`SAFE-501`) |
| 6 | Medication / care instructions not silently removed | **PASS** | `F-A04`–`F-A08` all MVP; §15.2 specifies each item type |
| 7 | Health information handled with source / date / context | **PASS** | `SAFE-970` provenance model; `SAFE-520`, `SAFE-521`; `SC-04` |
| 8 | Not turned into a generic fitness application | **PASS** | `PROD-1900` (MVP must show both); `RULE-002`, `RULE-003`; `R-18` names this as a tracked risk with mitigations |
| 9 | AI safety boundaries explicit | **PASS** | §18 (19 prohibitions, 10 obligations, the separation invariant, transparency duties); §17 regimes; guardrail layer |
| 10 | Privacy requirements explicit | **PASS** | §26 (minimization, storage, transmission, auth, secrets, logging, regulatory posture); §27 shared-TV |
| 11 | Official hackathon requirements verified | **PASS** | §33, verified 2026-09-27 against Devpost official rules and `developer.amazon.com`; sources listed in §33.8 |
| 12 | Hackathon requirements separated from product requirements | **PASS** | Six-prefix ID scheme (`HACK-` / `PROD-` / `SAFE-` / `PRIV-` / `TECH-` / `FUT-`) used throughout |
| 13 | No unsupported hackathon restrictions invented | **PASS** | §33.7 lists nine restrictions **checked and found not to exist**; §18.5 explicitly declines to assert unverified Appstore obligations, recording them as `OQ-08` |
| 14 | No final technology stack prematurely locked | **PASS** | §29.5 lists what is deliberately undecided; `RULE-023`; the only fixed constraint is `HACK-800` (Fire OS or Vega OS), which is an official requirement |
| 15 | MVP and future scope clearly separated | **PASS** | §30 (MVP) and §31 (four phases), with a Phase column on every feature in §11 |
| 16 | Useful to a future Claude Code development agent | **PASS** | Stable requirement IDs; §37 operating rules with escalation triggers; §28 invariants; §35 measurable criteria; §40 blocking Definition of Done |

### Concerns identified, and how they were handled

Per the owner's instruction, each concern is named, explained, bounded, and the original
product intent preserved.

1. **Windows host cannot build for Vega OS.** Official Vega tooling requires macOS 10.15+
   or Ubuntu 20.04+; Windows and WSL are unsupported. *Why it matters:* it could invalidate
   a platform choice after work has begun. *Boundary:* recorded as `R-10` and `OQ-01`–`OQ-03`;
   Fire OS is equally eligible under `HACK-800`, so **the Fire TV-first product intent is
   fully preserved** — only the OS variant is open.
2. **No documented free-form voice input on Fire TV.** *Why it matters:* the product
   definition describes a spoken natural-language request. *Boundary:* `TECH-450`,
   `PROD-451` — the understanding layer is decoupled from the input channel, and the
   non-voice path is mandatory and complete. **Voice is preserved as "where technically
   supported and appropriate"**, exactly as the product definition states, and the owner's
   own requirement that the app work without voice is upheld.
3. **A TV cannot reliably alert a user at a medication time.** *Why it matters:* promising
   it would create a false safety expectation. *Boundary:* §21 — in-app surfacing in MVP,
   out-of-app notification feasibility-gated as `FUT-1120`; `SAFE-1100` forbids the claim.
   **Reminders are preserved as a product capability**, scoped honestly.
4. **AI in a clinical context can hallucinate.** *Why it matters:* the central risk to the
   product. *Boundary:* the two-regime model (`SAFE-900`), a code-level guardrail layer
   that fails closed (`SAFE-920`), and a mandatory human confirmation gate (`SAFE-501`).
   **Document processing is preserved in full** — a human confirms rather than the AI
   deciding.
5. **Appstore content policy applies to app metadata, not only app content.** *Why it
   matters:* a name or description implying clinical capability is a rejection risk.
   *Boundary:* `SAFE-963`, `OQ-09` — the internal project name is retained unchanged and no
   display-name change is made without owner approval.
6. **Stricter health-app obligations could not be verified from primary sources.** *Why it
   matters:* the owner instructed that nothing be asserted as required without official
   support. *Boundary:* §18.5 records them as `OQ-08` rather than as requirements, while
   noting the product's own rules already meet or exceed them.
7. **Approximately 26 days remain to the deadline.** *Why it matters:* scope realism.
   *Boundary:* `R-13`; `PROD-1903`, `PROD-1910`, `DP-04`; aggressive §30.3 deferrals.
   **No feature was deleted** — everything deferred appears in §31 with its role intact.

---

## Appendix B — Change control

| ID | Rule |
|---|---|
| `CC-01` | This document is versioned. Any change increments the version and records the date and rationale below. |
| `CC-02` | Changes to §6 (situations), §9 (pillars), §12 (Fire TV stance), §18 (safety boundaries), §25 (user types), §30 (MVP scope) or §32 (out of scope) require **explicit owner approval** (`RULE-002`). |
| `CC-03` | §18 may not be weakened. It may only be strengthened or clarified. |
| `CC-04` | Deferring a feature requires moving it to §31 with its intended role preserved, and stating the deferral explicitly (`RULE-003`). |
| `CC-05` | `HACK-` items must be re-verified against primary sources before submission, in case official rules were updated after 2026-09-27. |

### Version history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-09-27 | Initial specification. Hackathon and platform requirements verified against official Devpost rules and `developer.amazon.com`. **Status: awaiting owner approval.** |

---

**END OF PROJECT MASTER SPEC**

No application code, scaffolding, dependencies or UI may be created until this document is
approved and an `ARCHITECTURE_SPEC.md` has been produced and approved (`RULE-020`).
