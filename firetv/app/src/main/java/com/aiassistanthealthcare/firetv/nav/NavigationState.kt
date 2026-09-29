package com.aiassistanthealthcare.firetv.nav

import androidx.compose.runtime.saveable.Saver
import androidx.compose.runtime.saveable.listSaver

/**
 * Pure navigation state and transitions -- no Android or Compose types, so it
 * is unit-testable on the JVM. Held by the shell in `rememberSaveable`.
 *
 * Back model (PROD-430, plan 8.3): Back moves exactly one level toward Today.
 * From Today, Back requests exit WITH confirmation. While the exit
 * confirmation is showing, Back dismisses it (never a dead end, PROD-504).
 * Back on Profile Select is not specified by the spec; it is treated like
 * Today (exit with confirmation) -- see the A1 report.
 *
 * [returnFocusTo] is a focus hint only: after Back from a section, the Today
 * screen puts focus on that section's entry so focus lands somewhere sensible
 * and visible (PROD-440).
 */
data class NavigationState(
    val current: Destination = Destination.ProfileSelect,
    val exitConfirmVisible: Boolean = false,
    val exitRequested: Boolean = false,
    val returnFocusTo: SectionArea? = null,
) {
    private val interactive: Boolean
        get() = !exitConfirmVisible && !exitRequested

    /** Enter the app after Profile Select. Only valid from Profile Select. */
    fun enterToday(): NavigationState =
        if (interactive && current == Destination.ProfileSelect) {
            copy(current = Destination.Today, returnFocusTo = null)
        } else {
            this
        }

    /** Open a section. Sections are entered only from Today (PROD-502). */
    fun openSection(area: SectionArea): NavigationState =
        if (interactive && current == Destination.Today) {
            copy(current = Destination.Section(area), returnFocusTo = null)
        } else {
            this
        }

    fun back(): NavigationState = when {
        exitRequested -> this
        exitConfirmVisible -> copy(exitConfirmVisible = false)
        current is Destination.Section -> copy(current = Destination.Today, returnFocusTo = current.area)
        else -> copy(exitConfirmVisible = true, returnFocusTo = null) // Today / Profile Select
    }

    fun dismissExit(): NavigationState =
        if (exitConfirmVisible) copy(exitConfirmVisible = false) else this

    fun confirmExit(): NavigationState =
        if (exitConfirmVisible) copy(exitConfirmVisible = false, exitRequested = true) else this

    companion object {
        /** Survives configuration change / process recreation. `exitRequested` is deliberately not saved. */
        val Saver: Saver<NavigationState, Any> = listSaver(
            save = { listOf(it.current.key, it.exitConfirmVisible, it.returnFocusTo?.name ?: "") },
            restore = { saved ->
                NavigationState(
                    current = Destination.fromKey(saved[0] as String) ?: Destination.ProfileSelect,
                    exitConfirmVisible = saved[1] as Boolean,
                    returnFocusTo = SectionArea.entries.firstOrNull { it.name == saved[2] as String },
                )
            },
        )
    }
}
