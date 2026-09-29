package com.aiassistanthealthcare.firetv.design

import androidx.compose.ui.graphics.Color

/**
 * Single owner of the 10-foot design tokens (ARCHITECTURE_MVP_PLAN.md 8.4:
 * "a single design/ module owns the token set so these are structurally
 * enforced rather than per-screen discipline").
 *
 * Text sizes are plain floats (sp) so they can be asserted in JVM unit tests.
 * HACK-411: body text >= 14sp is a FLOOR, not a target; PROD-434: primary card
 * text is substantially larger. HACK-416: sp for text, dp for spacing.
 */
object AppType {
    const val MIN_SP = 14f // HACK-411 floor: nothing on a shell screen goes below this
    const val CAPTION_SP = 16f
    const val BODY_SP = 20f
    const val PRIMARY_SP = 26f // card / button labels (PROD-434)
    const val HEADING_SP = 32f
    const val TITLE_SP = 40f

    val all = listOf(CAPTION_SP, BODY_SP, PRIMARY_SP, HEADING_SP, TITLE_SP)
}

/**
 * Cool-leaning, low-saturation palette (HACK-415). Focus is signalled by
 * scale + border width + border colour + background together, never colour
 * alone (HACK-413, PROD-435).
 */
object AppColors {
    val Background = Color(0xFF0F1318)
    val Surface = Color(0xFF1A2029)
    val SurfaceFocused = Color(0xFF2A3644)
    val Border = Color(0xFF3A4654)
    val BorderFocused = Color(0xFFBFD9FF)
    val OnSurface = Color(0xFFE8EDF3)
    val OnSurfaceMuted = Color(0xFFB4BFCC)
}

/** Focus treatment constants shared by every focusable shell component. */
object FocusStyle {
    const val SCALE_FOCUSED = 1.06f
    const val BORDER_DP_FOCUSED = 4
    const val BORDER_DP_RESTING = 1
}

/** HACK-410: nothing within the outer 5% of any screen edge. */
const val SAFE_ZONE_FRACTION = 0.05f
