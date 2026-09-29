package com.aiassistanthealthcare.firetv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Text

/**
 * P2 -- D-pad / focus / safe-zone validation POC.
 *
 * Validates ARCHITECTURE_MVP_PLAN.md Section 12's P2 success criteria only:
 * "All cards reachable by D-pad; focus always visible and never lost;
 * nothing in the outer 5%; body text >=14sp; primary text comfortably
 * readable at distance." See also Section 8.2 (focus model) and 8.4
 * (safe zone / typography rules) for the specific rules implemented below.
 *
 * This is NOT a product screen. No navigation, no data model, no backend,
 * no real content -- placeholder validation controls only, per the task
 * scope. Reached from its own home-screen launcher tile (see
 * AndroidManifest.xml) so it is exercised with the D-pad alone, exactly
 * like a real Fire TV session, and so MainActivity.kt (P1) stays
 * byte-for-byte unchanged.
 *
 * Layout note: the 6-card grid below is built from plain Compose
 * Row/Column, not androidx.tv.foundation's lazy grid DSL. Compose's core
 * focus system performs direction-aware focus search based on each
 * element's actual screen position, which is what D-pad navigation
 * depends on -- that behaviour does not require the TV lazy-grid
 * component, whose main value is scrolling/virtualization for large
 * lists. For a small, always-fully-composed, non-scrolling 6-item grid,
 * plain Row/Column gives the same real D-pad traversal behaviour with a
 * smaller, better-understood API surface.
 */
class P2FocusValidationActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            // Back is handled explicitly (not left to an implicit default):
            // pressing Back on this validation screen predictably exits
            // back to the TV home screen, never dead-ends, never crashes.
            P2FocusValidationScreen(onBack = { finish() })
        }
    }
}

private const val GRID_COLUMNS = 3
private const val GRID_ROWS = 2
private const val CARD_COUNT = GRID_COLUMNS * GRID_ROWS // 6, satisfies the "6+" requirement

// HACK-411's floor vs. the intended primary card text size, shown side by
// side so both can be judged for 10-foot legibility in the same frame.
private val FLOOR_TEXT_SP = 14.sp
private val PRIMARY_TEXT_SP = 22.sp

@Composable
fun P2FocusValidationScreen(onBack: () -> Unit = {}) {
    var showSafeZone by remember { mutableStateOf(true) }
    val firstCardFocusRequester = remember { FocusRequester() }

    LaunchedEffect(Unit) {
        // Arrival focus: a TV screen should never open with nothing
        // focused (PROD-440 spirit -- focus must never be "lost").
        firstCardFocusRequester.requestFocus()
    }

    // Explicit Back handling: predictable (always exits this screen),
    // never a dead end, never a crash.
    BackHandler(onBack = onBack)

    MaterialTheme {
        Box(modifier = Modifier.fillMaxSize()) {
            Column(modifier = Modifier.fillMaxSize().padding(48.dp)) {
                Text(text = "P2 Focus / Safe-Zone Validation", fontSize = 28.sp)

                Row(modifier = Modifier.padding(top = 16.dp, bottom = 8.dp)) {
                    Text(
                        text = "14sp floor: The quick brown fox jumps",
                        fontSize = FLOOR_TEXT_SP,
                        modifier = Modifier.padding(end = 40.dp),
                    )
                    Text(
                        text = "22sp primary: The quick brown fox jumps",
                        fontSize = PRIMARY_TEXT_SP,
                    )
                }

                Text(
                    text = "Focused card: scale + border + background all change together, " +
                        "never colour alone (HACK-413 / PROD-435).",
                    fontSize = 16.sp,
                    modifier = Modifier.padding(bottom = 16.dp),
                )

                ValidationCard(
                    label = if (showSafeZone) "Safe zone: ON  (Select to hide)" else "Safe zone: OFF  (Select to show)",
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp)
                        .aspectRatio(6f),
                    onSelect = { showSafeZone = !showSafeZone },
                )

                for (row in 0 until GRID_ROWS) {
                    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                        for (col in 0 until GRID_COLUMNS) {
                            val index = row * GRID_COLUMNS + col
                            val cardModifier = if (index == 0) {
                                Modifier.focusRequester(firstCardFocusRequester)
                            } else {
                                Modifier
                            }
                            ValidationCard(
                                label = "Card ${index + 1}",
                                modifier = cardModifier
                                    .weight(1f)
                                    .padding(8.dp)
                                    .aspectRatio(1.6f),
                                onSelect = { /* validation POC only -- no action */ },
                            )
                        }
                    }
                }
            }

            // Overlay is a pure Canvas draw above the content, never part
            // of the focusable tree, so toggling it can never disturb
            // whatever currently has focus.
            if (showSafeZone) {
                SafeZoneOverlay(modifier = Modifier.fillMaxSize())
            }
        }
    }
}

/**
 * One focusable validation control. Used for both the grid cards and the
 * safe-zone toggle, so every focusable element on this screen shows the
 * identical, explicit focus treatment: scale + border + background all
 * change together on focus (HACK-413, PROD-435) -- never colour alone.
 */
@Composable
private fun ValidationCard(
    label: String,
    modifier: Modifier = Modifier,
    onSelect: () -> Unit,
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isFocused by interactionSource.collectIsFocusedAsState()

    val scaleValue = if (isFocused) 1.12f else 1f
    val borderWidth = if (isFocused) 4.dp else 1.dp
    val borderColor = if (isFocused) Color(0xFFFFD400) else Color(0xFF3A3A3A)
    val backgroundColor = if (isFocused) Color(0xFF2C2C2C) else Color(0xFF141414)

    Box(
        modifier = modifier
            .scale(scaleValue)
            .background(backgroundColor, RoundedCornerShape(12.dp))
            .border(borderWidth, borderColor, RoundedCornerShape(12.dp))
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onSelect,
            ),
        contentAlignment = Alignment.Center,
    ) {
        Text(text = label, fontSize = PRIMARY_TEXT_SP, color = Color.White)
    }
}

/**
 * Draws a rectangle outline exactly at the 5%-of-edge inset boundary
 * (HACK-410: "avoid placing any of your app's UI elements within the
 * outer 5% of any edge"). Anything drawn outside this outline is a safe-
 * zone violation; everything else on screen should sit inside it.
 */
@Composable
private fun SafeZoneOverlay(modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        val marginX = size.width * 0.05f
        val marginY = size.height * 0.05f
        drawRect(
            color = Color.Red,
            topLeft = Offset(marginX, marginY),
            size = Size(size.width - 2 * marginX, size.height - 2 * marginY),
            style = Stroke(width = 3.dp.toPx()),
        )
    }
}
