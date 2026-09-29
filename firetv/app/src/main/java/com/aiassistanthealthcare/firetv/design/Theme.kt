package com.aiassistanthealthcare.firetv.design

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Text

/** App-wide TV theme: dark, cool, low-saturation (HACK-415). */
@Composable
fun AppTheme(content: @Composable () -> Unit) {
    MaterialTheme {
        Box(modifier = Modifier.fillMaxSize().background(AppColors.Background)) {
            content()
        }
    }
}

/**
 * Common frame for every shell screen: safe-zone padding (HACK-410), a title,
 * and vertical (single-axis, PROD-501) content. Screens supply only content.
 */
@Composable
fun ScreenScaffold(
    title: String,
    subtitle: String? = null,
    content: @Composable () -> Unit,
) {
    SafeZone {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(text = title, fontSize = AppType.TITLE_SP.sp, color = AppColors.OnSurface)
            if (subtitle != null) {
                Text(
                    text = subtitle,
                    fontSize = AppType.BODY_SP.sp,
                    color = AppColors.OnSurfaceMuted,
                    modifier = Modifier.padding(bottom = 8.dp),
                )
            }
            content()
        }
    }
}
