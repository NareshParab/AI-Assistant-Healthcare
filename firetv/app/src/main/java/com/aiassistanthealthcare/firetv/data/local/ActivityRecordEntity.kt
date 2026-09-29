package com.aiassistanthealthcare.firetv.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * ActivityRecord -- ARCHITECTURE_MVP_PLAN.md 3.2: "Any completion event (care
 * or wellness)". Store: Device. Columns are exactly the plan's key fields:
 * `id`, `profileId`, `recordType`, `subjectRef`, `timestamp`, `outcome`,
 * `correctionOf?`. Provenance note in the plan: "record of *user report*, not
 * verification (PROD-1210)".
 *
 * Deliberate modelling choices (each is a choice, not something the plan
 * states, and is listed in the A1 report):
 * - All text-typed; `timestamp` is an ISO-8601 UTC string, matching the API
 *   contract's timestamp convention (API_CONTRACT.md section 1).
 * - `subjectRef` is a plain string, not a foreign key: it points at a CareTask
 *   or an ActivitySession, neither of which exists yet.
 * - Rows are immutable. There is no update in the DAO: a correction is a NEW
 *   row whose `correctionOf` names the row it corrects (PROD-1212: "the
 *   correction is itself recorded").
 * - `profileId` is indexed and every DAO query is profile-scoped (PRIV-1808).
 */
@Entity(
    tableName = "activity_record",
    indices = [Index(value = ["profileId"])],
)
data class ActivityRecordEntity(
    @PrimaryKey val id: String,
    val profileId: String,
    val recordType: String,
    val subjectRef: String,
    val timestamp: String,
    val outcome: String,
    val correctionOf: String?,
)
