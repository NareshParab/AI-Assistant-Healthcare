package com.aiassistanthealthcare.firetv.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

/**
 * Device-side canonical store for CONFIRMED data (D6). Skeleton only.
 *
 * Contains ONLY entities that ARCHITECTURE_MVP_PLAN.md 3.2 defines precisely
 * enough to model without guessing. The rest of the device entities are
 * deliberately absent and listed as open questions in the A1 report.
 *
 * Schema export is on; the JSON is committed under app/schemas. No
 * destructive-migration fallback is configured: a schema change must be an
 * explicit migration, never a silent wipe of clinical data.
 */
@Database(
    entities = [ActivityRecordEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun activityRecordDao(): ActivityRecordDao

    companion object {
        const val FILE_NAME = "firetv.db"

        /** Plain builder; nothing calls this yet (no repository layer in A1). */
        fun build(context: Context): AppDatabase =
            Room.databaseBuilder(context.applicationContext, AppDatabase::class.java, FILE_NAME)
                .build()
    }
}
