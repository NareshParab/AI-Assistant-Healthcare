package com.aiassistanthealthcare.firetv.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

/**
 * Append-only, profile-scoped access to ActivityRecord (PRIV-1808: every
 * device entity carries profileId and all queries are profile-scoped).
 * No update and no delete here: records are immutable and corrections are new
 * rows (PROD-1212). Profile-level deletion (PROD-1531) belongs to the profile
 * lifecycle work, not this skeleton.
 */
@Dao
interface ActivityRecordDao {

    /** ABORT on a duplicate id: an existing record can never be overwritten. */
    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insert(record: ActivityRecordEntity)

    @Query("SELECT * FROM activity_record WHERE profileId = :profileId AND id = :id")
    suspend fun get(profileId: String, id: String): ActivityRecordEntity?

    @Query("SELECT * FROM activity_record WHERE profileId = :profileId ORDER BY timestamp DESC")
    suspend fun listForProfile(profileId: String): List<ActivityRecordEntity>
}
