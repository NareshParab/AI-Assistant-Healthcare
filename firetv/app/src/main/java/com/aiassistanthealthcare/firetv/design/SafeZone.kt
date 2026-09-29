package com.aiassistanthealthcare.firetv.design

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

/**
 * Wraps content so nothing sits in the outer 5% of any edge (HACK-410).
 * Every shell screen goes through this via [ScreenScaffold]; screens do not
 * apply their own edge padding.
 */
@Composable
fun SafeZone(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val horizontal = maxWidth * SAFE_ZONE_FRACTION
        val vertical = maxHeight * SAFE_ZONE_FRACTION
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = horizontal, vertical = vertical),
        ) {
            content()
        }
    }
}
