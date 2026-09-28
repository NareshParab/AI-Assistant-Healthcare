package com.aiassistanthealthcare.firetv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Text

/**
 * P1 — Fire TV Hello World.
 *
 * Sole purpose: prove that Windows -> Gradle -> Kotlin -> Jetpack Compose
 * for TV -> APK -> Fire OS target succeeds end to end. No navigation, no
 * focus handling, no product logic. See ARCHITECTURE_MVP_PLAN.md section 12
 * for what P1 validates and what P2 (a separate, later step) will add.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            P1ValidationScreen()
        }
    }
}

@Composable
fun P1ValidationScreen() {
    // androidx.tv.material3.MaterialTheme / Text — the Compose-for-TV
    // library (androidx.tv:tv-material), not the phone/tablet Material3
    // library, per the locked D2 framework decision.
    MaterialTheme {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(48.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = "AI Assistant Healthcare",
                fontSize = 48.sp,
            )
            Text(
                text = "P1 - Fire TV Hello World: running",
                fontSize = 24.sp,
                modifier = Modifier.padding(top = 24.dp),
            )
        }
    }
}
