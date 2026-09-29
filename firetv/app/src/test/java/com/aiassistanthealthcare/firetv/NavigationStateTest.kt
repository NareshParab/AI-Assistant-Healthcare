package com.aiassistanthealthcare.firetv

import com.aiassistanthealthcare.firetv.design.AppType
import com.aiassistanthealthcare.firetv.design.SAFE_ZONE_FRACTION
import com.aiassistanthealthcare.firetv.nav.Destination
import com.aiassistanthealthcare.firetv.nav.NavigationState
import com.aiassistanthealthcare.firetv.nav.SectionArea
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

/** Pure JVM tests: destination transitions and Back behaviour (spec 13.2, PROD-430/504). */
class NavigationStateTest {

    private fun atToday() = NavigationState().enterToday()

    @Test
    fun startsAtProfileSelect() {
        assertEquals(Destination.ProfileSelect, NavigationState().current)
    }

    @Test
    fun enterTodayMovesFromProfileSelectToToday() {
        assertEquals(Destination.Today, NavigationState().enterToday().current)
    }

    @Test
    fun enterTodayIsIgnoredOutsideProfileSelect() {
        val today = atToday()
        assertSame(today, today.enterToday())
    }

    @Test
    fun sectionsOpenOnlyFromToday() {
        val fromProfile = NavigationState().openSection(SectionArea.WELLNESS)
        assertEquals(Destination.ProfileSelect, fromProfile.current)

        SectionArea.entries.forEach { area ->
            assertEquals(Destination.Section(area), atToday().openSection(area).current)
        }
    }

    @Test
    fun sectionsAreSiblingsNotADeepTree() {
        val inSection = atToday().openSection(SectionArea.CARE_PLAN)
        assertSame(inSection, inSection.openSection(SectionArea.PROGRESS)) // no sibling-to-sibling jump
    }

    @Test
    fun spec_sectionNamesAndOrderMatchMasterSpec13_1() {
        assertEquals(
            listOf("Care Plan", "Health Info", "Wellness", "Progress", "Documents", "Settings"),
            SectionArea.entries.map { it.title },
        )
    }

    @Test
    fun backFromSectionReturnsToTodayAndHintsFocus() {
        val back = atToday().openSection(SectionArea.PROGRESS).back()
        assertEquals(Destination.Today, back.current)
        assertEquals(SectionArea.PROGRESS, back.returnFocusTo)
        assertFalse(back.exitConfirmVisible)
    }

    @Test
    fun backOnTodayAsksToExitInsteadOfExiting() {
        val back = atToday().back()
        assertEquals(Destination.Today, back.current)
        assertTrue(back.exitConfirmVisible)
        assertFalse(back.exitRequested)
    }

    @Test
    fun backOnProfileSelectAlsoAsksToExit() {
        val back = NavigationState().back()
        assertEquals(Destination.ProfileSelect, back.current)
        assertTrue(back.exitConfirmVisible)
        assertFalse(back.exitRequested)
    }

    @Test
    fun backWhileExitConfirmIsShowingDismissesIt() {
        val dismissed = atToday().back().back()
        assertFalse(dismissed.exitConfirmVisible)
        assertFalse(dismissed.exitRequested)
        assertEquals(Destination.Today, dismissed.current)
    }

    @Test
    fun confirmingExitRequestsExitOnlyAfterTheConfirmation() {
        val asked = atToday().back()
        assertFalse(asked.exitRequested)
        val left = asked.confirmExit()
        assertTrue(left.exitRequested)
        assertFalse(left.exitConfirmVisible)
    }

    @Test
    fun confirmExitWithoutAskingDoesNothing() {
        val today = atToday()
        assertSame(today, today.confirmExit())
        assertFalse(today.confirmExit().exitRequested)
    }

    @Test
    fun stayDismissesTheExitPrompt() {
        val stayed = atToday().back().dismissExit()
        assertFalse(stayed.exitConfirmVisible)
        assertEquals(Destination.Today, stayed.current)
    }

    @Test
    fun nothingNavigatesWhileTheExitPromptIsShowing() {
        val asked = atToday().back()
        assertSame(asked, asked.openSection(SectionArea.SETTINGS))
        val askedAtProfileSelect = NavigationState().back()
        assertSame(askedAtProfileSelect, askedAtProfileSelect.enterToday())
    }

    @Test
    fun backNeverSkipsPastTodayFromASection() {
        // Section -> Today -> (exit prompt): never straight out of the app.
        val s = atToday().openSection(SectionArea.SETTINGS)
        val step1 = s.back()
        assertEquals(Destination.Today, step1.current)
        assertFalse(step1.exitConfirmVisible)
        val step2 = step1.back()
        assertTrue(step2.exitConfirmVisible)
        assertFalse(step2.exitRequested)
    }

    @Test
    fun repeatedBackAfterExitRequestedIsHarmless() {
        val left = atToday().back().confirmExit()
        assertSame(left, left.back())
    }

    @Test
    fun openingASectionClearsTheFocusHint() {
        val s = atToday().openSection(SectionArea.PROGRESS).back().openSection(SectionArea.SETTINGS)
        assertNull(s.returnFocusTo)
    }

    @Test
    fun destinationKeysRoundTrip() {
        val all = listOf(Destination.ProfileSelect, Destination.Today) +
            SectionArea.entries.map { Destination.Section(it) }
        all.forEach { assertEquals(it, Destination.fromKey(it.key)) }
        assertNull(Destination.fromKey("nonsense"))
        assertNull(Destination.fromKey("section:NOPE"))
    }

    // --- design tokens (HACK-410, HACK-411, PROD-434) -------------------------

    @Test
    fun typographyRespectsTheFloorAndPrimaryIsSubstantiallyLarger() {
        assertTrue(AppType.MIN_SP >= 14f)
        AppType.all.forEach { assertTrue("size $it below floor", it >= AppType.MIN_SP) }
        assertTrue(AppType.PRIMARY_SP >= AppType.MIN_SP * 1.5f)
    }

    @Test
    fun safeZoneIsFivePercent() {
        assertEquals(0.05f, SAFE_ZONE_FRACTION, 0f)
    }
}
