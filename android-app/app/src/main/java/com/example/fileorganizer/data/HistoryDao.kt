package com.example.fileorganizer.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface HistoryDao {
    @Query("SELECT * FROM history_batches ORDER BY id DESC")
    fun getAllHistory(): Flow<List<HistoryBatchEntity>>

    @Insert
    suspend fun insertBatch(batch: HistoryBatchEntity)

    @androidx.room.Update
    suspend fun updateBatch(batch: HistoryBatchEntity)

    @Query("DELETE FROM history_batches WHERE id = :id")
    suspend fun deleteBatch(id: Long)

    @Query("DELETE FROM history_batches")
    suspend fun clearAll()

    @Query("SELECT * FROM history_batches ORDER BY id DESC LIMIT 1")
    suspend fun getLastBatch(): HistoryBatchEntity?
}
