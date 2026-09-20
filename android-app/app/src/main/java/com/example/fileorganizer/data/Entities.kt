package com.example.fileorganizer.data

import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.TypeConverter
import com.example.fileorganizer.domain.MovedFile
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

@Entity(tableName = "history_batches")
data class HistoryBatchEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestamp: String,
    val movedFilesJson: String,
    val groupFolder: String? = null
)

class Converters {
    private val formatter = DateTimeFormatter.ISO_LOCAL_DATE_TIME
    private val gson = Gson()

    @TypeConverter
    fun fromTimestamp(value: String?): LocalDateTime? {
        return value?.let { LocalDateTime.parse(it, formatter) }
    }

    @TypeConverter
    fun toTimestamp(date: LocalDateTime?): String? {
        return date?.format(formatter)
    }

    @TypeConverter
    fun fromMovedFiles(value: String): List<MovedFile> {
        val type = object : TypeToken<List<MovedFile>>() {}.type
        return gson.fromJson(value, type)
    }

    @TypeConverter
    fun toMovedFiles(list: List<MovedFile>): String {
        return gson.toJson(list)
    }
}
