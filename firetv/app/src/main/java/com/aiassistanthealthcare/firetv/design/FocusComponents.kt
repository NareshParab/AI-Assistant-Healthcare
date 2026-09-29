package com.aiassistanthealthcare.firetv.design

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.tv.material3.Text

/**
 * The one reusable focusable control of the shell (a button/card).
 *
 * Focus is shown by scale + border width + border colour + background changing
 * TOGETHER, never colour alone (HACK-413, PROD-435). Select (D-pad centre /
 * Enter) activates [onSelect] via `clickable`; there is no touch-only
 * affordance. Text is at least [AppType.PRIMARY_SP] (PROD-434).
 *
 * [requestInitialFocus]: exactly one control per screen should set this, so a
 * screen never opens with nothing focused (PROD-440).
 *
 * Callers should give this a bounded width (not full-bleed): the focused scale
 * grows the control by a few dp on each side, and that growth must stay inside
 * the safe zone.
 */
@Composable
fun FocusCard(
    label: String,
    onSelect: () -> Unit,
    modifier: Modifier = Modifier,
    requestInitialFocus: Boolean = false,
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isFocused by interactionSource.collectIsFocusedAsState()
    val focusRequester = remember { FocusRequester() }

    LaunchedEffect(Unit) {
        if (requestInitialFocus) focusRequester.requestFocus()
    }

    val shape = RoundedCornerShape(12.dp)
    Box(
        modifier = modifier
            .focusRequester(focusRequester)
            .scale(if (isFocused) FocusStyle.SCALE_FOCUSED else 1f)
            .background(if (isFocused) AppColors.SurfaceFocused else AppColors.Surface, shape)
            .border(
                width = (if (isFocused) FocusStyle.BORDER_DP_FOCUSED else FocusStyle.BORDER_DP_RESTING).dp,
                color = if (isFocused) AppColors.BorderFocused else AppColors.Border,
                shape = shape,
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                role = Role.Button,
                onClick = onSelect,
            )
            .heightIn(min = 64.dp),
        contentAlignment = Alignment.CenterStart,
    ) {
        Text(
            text = label,
            fontSize = AppType.PRIMARY_SP.sp,
            color = AppColors.OnSurface,
            modifier = Modifier.padding(horizontal = 24.dp, vertical = 12.dp),
        )
    }
}
