package com.aiassistanthealthcare.firetv.nav

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import com.aiassistanthealthcare.firetv.design.AppTheme
import com.aiassistanthealthcare.firetv.ui.ExitConfirmScreen
import com.aiassistanthealthcare.firetv.ui.ProfileSelectPlaceholder
import com.aiassistanthealthcare.firetv.ui.SectionPlaceholder
import com.aiassistanthealthcare.firetv.ui.TodayPlaceholder

/**
 * Launcher entry for the real app shell (task A1). Added ALONGSIDE the P1
 * MainActivity and the P2 validation activity, both untouched.
 */
class ShellActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { AppShell(onExit = { finish() }) }
    }
}

/**
 * Hosts the destinations. Navigation is a sealed-class destination model
 * ([Destination]) plus pure state ([NavigationState]) in `rememberSaveable`,
 * with a single [BackHandler] -- no navigation library. Back is always handled
 * here, so it can never fall through to an unexpected default.
 */
@Composable
fun AppShell(onExit: () -> Unit) {
    var nav by rememberSaveable(stateSaver = NavigationState.Saver) {
        mutableStateOf(NavigationState())
    }

    BackHandler(enabled = !nav.exitRequested) { nav = nav.back() }

    LaunchedEffect(nav.exitRequested) {
        if (nav.exitRequested) onExit()
    }

    AppTheme {
        if (nav.exitConfirmVisible) {
            ExitConfirmScreen(
                onStay = { nav = nav.dismissExit() },
                onLeave = { nav = nav.confirmExit() },
            )
        } else {
            when (val destination = nav.current) {
                Destination.ProfileSelect ->
                    ProfileSelectPlaceholder(onContinue = { nav = nav.enterToday() })

                Destination.Today ->
                    TodayPlaceholder(
                        returnFocusTo = nav.returnFocusTo,
                        onOpenSection = { nav = nav.openSection(it) },
                    )

                is Destination.Section ->
                    SectionPlaceholder(area = destination.area, onBack = { nav = nav.back() })
            }
        }
    }
}
