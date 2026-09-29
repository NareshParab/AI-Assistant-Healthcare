package com.aiassistanthealthcare.firetv.ui

import android.content.Intent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.aiassistanthealthcare.firetv.P2FocusValidationActivity
import com.aiassistanthealthcare.firetv.design.FocusCard
import com.aiassistanthealthcare.firetv.design.ScreenScaffold
import com.aiassistanthealthcare.firetv.nav.SectionArea

/**
 * Shell screens. Every one is a clearly labelled PLACEHOLDER: structure only,
 * no healthcare content, no data, no features. Each uses [ScreenScaffold]
 * (safe zone + title) and gives exactly one control the initial focus.
 *
 * Controls use a bounded width so the focus-scale growth stays inside the
 * safe zone.
 */
private val ControlWidth = Modifier.widthIn(max = 560.dp).fillMaxWidth()

private const val PLACEHOLDER_NOTE = "Placeholder screen - no content yet."

@Composable
fun ProfileSelectPlaceholder(onContinue: () -> Unit) {
    ScreenScaffold(title = "Profile Select (placeholder)", subtitle = PLACEHOLDER_NOTE) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            FocusCard(
                label = "Continue to Today",
                onSelect = onContinue,
                modifier = ControlWidth,
                requestInitialFocus = true,
            )
        }
    }
}

/**
 * Today (home): entry to the six sibling sections, in the spec's order. Also
 * one clearly labelled DEV item that opens the untouched P2 validation screen
 * (a separate Activity) so it stays reachable from the shell.
 */
@Composable
fun TodayPlaceholder(
    returnFocusTo: SectionArea?,
    onOpenSection: (SectionArea) -> Unit,
) {
    val context = LocalContext.current
    val initial = returnFocusTo ?: SectionArea.entries.first()

    ScreenScaffold(title = "Today (placeholder)", subtitle = PLACEHOLDER_NOTE) {
        // Scrollable so a taller list can never push a control off-screen;
        // focus moving into view scrolls it automatically.
        Column(
            modifier = Modifier.verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            SectionArea.entries.forEach { area ->
                FocusCard(
                    label = area.title,
                    onSelect = { onOpenSection(area) },
                    modifier = ControlWidth,
                    requestInitialFocus = area == initial,
                )
            }
            FocusCard(
                label = "DEV: P2 focus validation",
                onSelect = {
                    context.startActivity(Intent(context, P2FocusValidationActivity::class.java))
                },
                modifier = ControlWidth,
            )
        }
    }
}

@Composable
fun SectionPlaceholder(area: SectionArea, onBack: () -> Unit) {
    ScreenScaffold(title = "${area.title} (placeholder)", subtitle = PLACEHOLDER_NOTE) {
        FocusCard(
            label = "Back to Today",
            onSelect = onBack,
            modifier = ControlWidth,
            requestInitialFocus = true,
        )
    }
}

/** Back on Today (or Profile Select) asks before leaving (PROD-430). Non-punitive, no timeout (PROD-437). */
@Composable
fun ExitConfirmScreen(onStay: () -> Unit, onLeave: () -> Unit) {
    ScreenScaffold(title = "Leave the app?") {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            FocusCard(
                label = "Stay",
                onSelect = onStay,
                modifier = ControlWidth,
                requestInitialFocus = true,
            )
            FocusCard(label = "Leave", onSelect = onLeave, modifier = ControlWidth)
        }
    }
}
