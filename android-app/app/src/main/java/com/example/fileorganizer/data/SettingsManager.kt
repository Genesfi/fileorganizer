package com.example.fileorganizer.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import com.example.fileorganizer.domain.FileCategory
import com.example.fileorganizer.domain.FilterSettings
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

class SettingsManager(private val context: Context) {
    private val gson = Gson()

    companion object {
        val CATEGORIES_KEY = stringPreferencesKey("categories")
        val SETTINGS_KEY = stringPreferencesKey("filter_settings")
        val SELECTED_TEMPLATE_KEY = stringPreferencesKey("selected_template")
    }

    val categoriesFlow: Flow<List<FileCategory>> = context.dataStore.data.map { preferences ->
        val json = preferences[CATEGORIES_KEY]
        if (json == null) {
            getDefaultCategories()
        } else {
            val type = object : TypeToken<List<FileCategory>>() {}.type
            gson.fromJson(json, type)
        }
    }

    val settingsFlow: Flow<FilterSettings> = context.dataStore.data.map { preferences ->
        val json = preferences[SETTINGS_KEY]
        if (json == null) {
            FilterSettings(includedCategories = getDefaultCategories().map { it.name } + "Others")
        } else {
            gson.fromJson(json, FilterSettings::class.java)
        }
    }

    val selectedTemplateFlow: Flow<String> = context.dataStore.data.map { preferences ->
        preferences[SELECTED_TEMPLATE_KEY] ?: "None"
    }

    suspend fun saveCategories(categories: List<FileCategory>) {
        context.dataStore.edit { preferences ->
            preferences[CATEGORIES_KEY] = gson.toJson(categories)
        }
    }

    suspend fun saveSettings(settings: FilterSettings) {
        context.dataStore.edit { preferences ->
            preferences[SETTINGS_KEY] = gson.toJson(settings)
        }
    }

    suspend fun saveSelectedTemplate(name: String) {
        context.dataStore.edit { preferences ->
            preferences[SELECTED_TEMPLATE_KEY] = name
        }
    }

    suspend fun resetToDefaults() {
        context.dataStore.edit { preferences ->
            preferences.remove(CATEGORIES_KEY)
            preferences.remove(SETTINGS_KEY)
            preferences.remove(SELECTED_TEMPLATE_KEY)
        }
    }

    fun getDefaultCategories() = listOf(
        FileCategory("Images", listOf("jpg", "jpeg", "png", "gif", "bmp", "svg", "webp")),
        FileCategory("Videos", listOf("mp4", "mkv", "avi", "mov", "flv", "wmv")),
        FileCategory("Documents", listOf("pdf", "doc", "docx", "txt", "rtf", "odt", "xls", "xlsx", "ppt", "pptx")),
        FileCategory("Audio", listOf("mp3", "wav", "flac", "m4a", "ogg")),
        FileCategory("Archives", listOf("zip", "rar", "7z", "tar", "gz"))
    )
    
    fun getDefaultSettings() = FilterSettings(
        includedCategories = getDefaultCategories().map { it.name } + "Others"
    )
}
