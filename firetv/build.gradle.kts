// Root build file — P1 validation project.
// Version choices are pinned deliberately to a single, mutually-compatible,
// mature release era (Oct 2024) rather than the latest available versions,
// to minimize dependency-resolution risk in this minimal POC. See P1 report
// for the reasoning (AGP 9.x raises the SDK Build Tools floor to 36.0.0,
// which conflicts with the locked minSdk 29 / targetSdk 34 / build-tools
// 34.0.0 already installed per ARCHITECTURE_MVP_PLAN.md D3).
plugins {
    id("com.android.application") version "8.7.0" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false
    // Room's annotation processor (Room is locked by D6). KSP versions are
    // "<kotlin version>-<ksp release>"; this one matches Kotlin 2.0.21 exactly,
    // so the toolchain is unchanged.
    id("com.google.devtools.ksp") version "2.0.21-1.0.28" apply false
}
