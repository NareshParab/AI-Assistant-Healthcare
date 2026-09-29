# Friction Log

Per `HACK-826` (Build, Ship, Shape hackathon): submissions with friction log
entries score up to a 10% bonus. This is a running log, appended to as work
proceeds — not written retroactively at submission time.

Format per entry: task attempted, steps, expected vs. actual result,
severity, workaround, actionable suggestion for Amazon/tooling maintainers.

---

## P1 — Fire TV Hello World (Kotlin + Jetpack Compose for TV)

### FL-001 — Android Gradle Plugin 9.x raises the SDK Build Tools floor to 36.0.0

**Task:** Choose an AGP version for a fresh project targeting the locked
`minSdk 29` / `targetSdk 34` (ARCHITECTURE_MVP_PLAN.md D3).
**Steps:** Installed the current-generation AGP release; attempted to build
against the already-installed `build-tools;34.0.0`.
**Expected:** AGP would build cleanly against any reasonably recent
build-tools version.
**Actual:** AGP 9.0+ requires **SDK Build Tools ≥ 36.0.0** as a hard floor,
regardless of the project's own `compileSdk`/`targetSdk` settings, and
defaults `targetSdk` to `compileSdk` unless overridden — a materially
different toolchain than what D3 assumed.
**Severity:** Medium — would have forced an unplanned platform-35/36 SDK
install and closer coupling to a very new AGP line for a hackathon MVP.
**Workaround:** Used the mature **AGP 8.7.0** line instead (Gradle 8.9,
build-tools 34.0.0, JDK 17 — an exact match to what was already installed),
avoiding the AGP-9 migration surface (built-in-Kotlin-by-default, new DSL)
entirely for this project.
**Suggestion:** Android tooling docs should surface the AGP-9 build-tools
floor change more prominently in "getting started" guidance — it is easy to
hit on a brand-new project with no prior AGP version pinned.

### FL-002 — `androidx.tv:tv-material` / `tv-foundation` require `compileSdk ≥ 35` regardless of `targetSdk`

**Task:** Add Compose-for-TV dependencies to a project with `compileSdk 34`.
**Steps:** Added `androidx.tv:tv-foundation:1.0.0` and
`androidx.tv:tv-material:1.1.0`; ran `assembleDebug`.
**Expected:** Build would succeed since `targetSdk` (34) was unaffected.
**Actual:** Build failed with 16 AAR-metadata errors — every resolved
Compose/TV dependency declares a `compileSdk ≥ 35` floor. This is a
build-time-only requirement, separate from `minSdk`/`targetSdk`.
**Severity:** Low once understood, but non-obvious on first encounter —
easy to misread as a requirement to raise `targetSdk` (which is locked by
D3 and would need approval to change).
**Workaround:** Raised `compileSdk` to 35 only; `minSdk`/`targetSdk`
unchanged. Installed `platforms;android-35` + `build-tools;35.0.0`
alongside the existing 34 versions.
**Suggestion:** None needed beyond documenting the distinction clearly in
this repo (`firetv/app/build.gradle.kts` now carries an inline comment).

### FL-003 — Gradle wrapper's distribution-URL self-check times out on a slow connection, even though the actual download succeeds

**Task:** Bootstrap `gradlew`/`gradlew.bat` for the project via
`gradle wrapper --gradle-version 8.9`.
**Steps:** Ran the wrapper task with default settings.
**Expected:** Wrapper files generated without needing network access beyond
the one distribution download already completed.
**Actual:** The `wrapper` task performs its own `HEAD` request to verify
the distribution URL, with a hardcoded **10-second timeout**
(`networkTimeout=10000`). On this connection (observed ~150–700 KB/s
throughout setup), that HEAD request itself timed out, even though a full
136 MB `GET` of the same URL had just succeeded moments earlier.
**Severity:** Medium — blocks every fresh `gradlew` invocation on a slow or
high-latency connection, not just the first one, since the same check runs
via the wrapper's own bootstrap logic.
**Workaround:** Set `validateDistributionUrl=false` and
`networkTimeout=30000` in `gradle-wrapper.properties`.
**Suggestion:** Gradle's wrapper `HEAD`-check timeout should scale with (or
default higher than) typical broadband conditions, or fall back to
skipping validation on timeout rather than failing the whole task.

### FL-004 — Multiple large, slow downloads dominated setup time

**Task:** Install JDK 17, Android SDK command-line tools, and the Gradle
8.9 distribution.
**Steps:** Standard `winget`/direct-download installs.
**Expected:** Minutes, based on typical broadband speeds for ~150–200 MB
combined.
**Actual:** Each download took 3–6 minutes on this connection; total
environment setup time was dominated by network wait, not by any actual
configuration difficulty.
**Severity:** Low (environmental, not a tooling defect) — recorded because
it materially affected how development time was budgeted early on.
**Workaround:** None needed; waited out the downloads.
**Suggestion:** N/A — connection-specific.

---

## P2 — D-pad / focus / safe-zone validation

### FL-005 — First P2 attempt: command execution failed session-wide before build/test/commit

**Task:** Implement and validate P2 in a single session.
**Steps:** Wrote `P2FocusValidationScreen.kt`, the `AndroidManifest.xml` /
`strings.xml` companion changes, and this file's P1 entries — all via
file-write tools. Then attempted to run the Gradle build.
**Expected:** Build, manual validation, friction-log update, commit, push,
all in the same session.
**Actual:** Every command-execution tool call (shell/PowerShell) began
failing with a platform-level error — *"the server-side auto mode
classifier gave no verdict"* — and did not recover after several retries
spaced across the session. No build, no test, no emulator check, no git
operation of any kind was possible. The session was stopped at that
checkpoint rather than retried indefinitely, with an explicit status report
that nothing had been built, validated, committed, or pushed.
**Severity:** High for that session (total loss of the ability to verify
anything), zero lasting impact — no incorrect claim was made, and no
partial/corrupt commit resulted, because nothing was committed.
**Workaround:** None available client-side; the issue resolved itself by
the next session, and this second attempt reused the already-written P2
files rather than rewriting them from scratch.
**Suggestion:** None actionable here — a platform-side transient failure,
not a project or tooling defect.

### FL-006 — Incorrect top-level import of `RowScope.weight` broke compilation

**Task:** Build a 3-column x 2-row static grid of focusable cards using
plain Compose `Row`/`Column` (a deliberate choice over
`androidx.tv.foundation`'s lazy grid DSL — see the doc comment in
`P2FocusValidationScreen.kt`).
**Steps:** Added `import androidx.compose.foundation.layout.weight` to use
`.weight(1f)` inside a `Row { }` to distribute the three cards evenly per
row; ran `assembleDebug`.
**Expected:** Compiles — `weight` is a standard Compose layout modifier.
**Actual:** Compilation failed: `Cannot access 'val
RowColumnParentData?.weight: Float': it is internal in file.` `weight` is a
member extension function on `RowScope`/`ColumnScope`, already implicitly
in scope inside a `Row { }`/`Column { }` lambda — no top-level import
exists or is needed for it, and the import path I guessed resolved to a
different, internal declaration of the same name in that package.
**Severity:** Low — caught immediately by the compiler, one-line fix.
**Workaround:** Removed the unnecessary import entirely; `.weight(1f)`
resolves correctly via the implicit `RowScope` receiver with no import.
**Suggestion:** None needed; recorded because it is a plausible mistake for
anyone unfamiliar with which Compose layout modifiers are top-level
functions vs. scope-receiver extensions.

### FL-007 — `lintDebug` crashes on a bundled `androidx.lifecycle` lint detector, unrelated to project code

**Task:** Run `./gradlew lintDebug` per the P2 validation task's "run lint
if configured" step.
**Steps:** Ran `lintDebug` on the debug variant after a successful
`assembleDebug`.
**Expected:** Lint completes (pass or with findings).
**Actual:** Lint crashed with `IncompatibleClassChangeError` inside the
bundled `androidx.lifecycle.lint.NonNullableMutableLiveDataDetector`,
reported by lint itself as *"this is a bug in lint or one of the libraries
it depends on"* — a UAST/Kotlin-Analysis-API version mismatch between that
detector and the project's Kotlin Gradle Plugin (2.0.21). The crash occurs
while analyzing `MainActivity.kt`, a P1 file untouched by this task,
confirming the failure is a tooling incompatibility, not a defect in P2's
(or P1's) code.
**Severity:** Medium — lint could not be run at all for this checkpoint;
no lint results (clean or otherwise) exist for this codebase yet.
**Workaround:** None applied. The suggested workaround (disabling
`NullSafeMutableLiveData` in `android { lint { ... } }`) would touch
`build.gradle.kts`, which is out of scope for a P2-only task that must not
touch locked build configuration without being asked. Left unresolved and
reported here instead.
**Suggestion:** Either pin a Kotlin Gradle Plugin / AGP combination known
to be lint-compatible, or disable the specific crashing detector once a
build-configuration change is in scope, in a future phase.

### FL-008 — No Android TV emulator or physical device available on this machine for P2's manual checklist

**Task:** Manually validate D-pad focus/safe-zone behaviour per
Section 12 P2.
**Steps:** Ran `adb devices -l`.
**Expected:** Either a running emulator or a connected device to drive via
`adb shell input keyevent`.
**Actual:** Empty device list. No AVD has ever been created on this
machine (only SDK platform-tools/platforms/build-tools were installed;
no system image or emulator package). The physical Fire TV device is held
by a teammate, per the project's stated hardware-ownership split, and is
explicitly out of scope for this task.
**Severity:** Expected/anticipated by the task itself, not a defect.
**Workaround:** None attempted — setting up an emulator (a multi-GB system
image install) was judged out of scope for this task without being asked,
since the task's own Step 2 language treats "no device/emulator available"
as a valid, reportable outcome ("build-verified only"), not something to
resolve unilaterally.
**Suggestion:** A follow-up task, scoped explicitly to emulator setup, is
the appropriate next step if runtime D-pad behaviour needs to be verified
before physical-device validation happens.

---

## A1 - App shell, TV theme/focus base, Room skeleton

### FL-009 - The Android project template ships with no unit-test runner configured

**Task:** Add JVM unit tests for the pure navigation-state logic, with the
project's own rule of "no new test libraries beyond what is already there".
**Steps:** Inspected `firetv/app/build.gradle.kts` before writing tests, then
ran `testDebugUnitTest` planning.
**Expected:** A project created for Android development to already carry a
JVM test dependency.
**Actual:** There is no `testImplementation` line at all in the P1/P2 project.
`testDebugUnitTest` has nothing that can discover or run a test until JUnit
is added, so "use only what is already in the project" is unsatisfiable for
any test.
**Severity:** Low - one line to fix, but it directly conflicts with the
no-new-dependency rule, so it needed an explicit owner decision.
**Workaround:** Owner approved `testImplementation("junit:junit:4.13.2")`
(test scope only). Nothing else was added for testing.
**Suggestion:** Record test-runner availability as part of the P1 toolchain
checklist so later tasks do not hit a dependency-approval stop.
