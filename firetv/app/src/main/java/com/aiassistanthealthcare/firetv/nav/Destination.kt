package com.aiassistanthealthcare.firetv.nav

/**
 * The six sections one level below Today (PROJECT_MASTER_SPEC.md 13.1, PROD-502;
 * ARCHITECTURE_MVP_PLAN.md 8.1). Names are the spec's. Care Plan, Health Info
 * and Documents are Care/Both-only (PROD-503); that per-profile visibility is
 * NOT applied here because no profile or user context exists yet.
 */
enum class SectionArea(val title: String) {
    CARE_PLAN("Care Plan"),
    HEALTH_INFO("Health Info"),
    WELLNESS("Wellness"),
    PROGRESS("Progress"),
    DOCUMENTS("Documents"),
    SETTINGS("Settings"),
}

/**
 * Where the user is. Profile Select is always the entry point (PRIV-700, 14.1);
 * Today is home and the convergence point (PROD-500); sections are siblings
 * one level below Today (PROD-502). Deeper screens (Item Detail, Review,
 * Session Player, ...) are not part of the shell.
 */
sealed class Destination(val key: String) {
    data object ProfileSelect : Destination("profile_select")
    data object Today : Destination("today")
    data class Section(val area: SectionArea) : Destination("section:${area.name}")

    companion object {
        fun fromKey(key: String): Destination? = when {
            key == ProfileSelect.key -> ProfileSelect
            key == Today.key -> Today
            key.startsWith("section:") ->
                SectionArea.entries.firstOrNull { it.name == key.removePrefix("section:") }
                    ?.let(::Section)
            else -> null
        }
    }
}
