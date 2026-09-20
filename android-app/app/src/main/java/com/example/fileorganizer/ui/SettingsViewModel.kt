package com.example.fileorganizer.ui

import android.app.Application
import androidx.compose.runtime.*
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.fileorganizer.data.SettingsManager
import com.example.fileorganizer.data.TemplateManager
import com.example.fileorganizer.domain.FileCategory
import com.example.fileorganizer.domain.FilterSettings
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.io.File
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    application: Application,
    private val settingsManager: SettingsManager,
    private val templateManager: TemplateManager
) : AndroidViewModel(application) {

    val categories: StateFlow<List<FileCategory>> = settingsManager.categoriesFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val settings: StateFlow<FilterSettings> = settingsManager.settingsFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), FilterSettings())

    var activeCategory by mutableStateOf<FileCategory?>(null)
    var editFolderName by mutableStateOf("")
    var editExtensions by mutableStateOf("")
    var editKeywords by mutableStateOf("")
    var editRegex by mutableStateOf("")
    var editSubfolder by mutableStateOf("")
    
    var templates = mutableStateListOf<String>()
    var selectedTemplate by mutableStateOf("None")

    init {
        loadTemplates()
        viewModelScope.launch {
            val currentSettings = settingsManager.settingsFlow.first()
            editRegex = currentSettings.filenameRegex
        }
        viewModelScope.launch {
            settingsManager.selectedTemplateFlow.collect {
                selectedTemplate = it
            }
        }
    }

    private fun loadTemplates() {
        templates.clear()
        templates.add("None")
        
        // Load from internal storage
        val dir = File(getApplication<Application>().filesDir, "templates")
        if (!dir.exists()) dir.mkdirs()
        dir.list()?.filter { it.endsWith(".json") }?.forEach { 
            templates.add(it.removeSuffix(".json"))
        }
        
        // Load from assets
        try {
            getApplication<Application>().assets.list("templates")?.filter { it.endsWith(".json") }?.forEach {
                val name = it.removeSuffix(".json")
                if (!templates.contains(name)) {
                    templates.add(name)
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun onCategorySelected(category: FileCategory) {
        activeCategory = category
        editFolderName = category.name
        editExtensions = category.extensions.joinToString(", ")
        editKeywords = category.keywords.joinToString(", ")
        editSubfolder = category.subfolderPattern ?: settings.value.subfolders[category.name] ?: ""
    }

    fun updateCategory() {
        val currentActive = activeCategory ?: return
        val newCategories = categories.value.map {
            if (it.name == currentActive.name) {
                it.copy(
                    name = editFolderName,
                    extensions = editExtensions.split(",").map { e -> e.trim() }.filter { e -> e.isNotEmpty() },
                    keywords = editKeywords.split(",").map { k -> k.trim() }.filter { k -> k.isNotEmpty() },
                    subfolderPattern = editSubfolder.trim().ifBlank { null }
                )
            } else it
        }
        val newSubfolders = settings.value.subfolders.toMutableMap()
        if (editSubfolder.trim().isNotBlank()) {
            newSubfolders[editFolderName] = editSubfolder.trim()
        } else {
            newSubfolders.remove(editFolderName)
        }
        viewModelScope.launch(Dispatchers.IO) {
            settingsManager.saveCategories(newCategories)
            settingsManager.saveSettings(settings.value.copy(subfolders = newSubfolders))
        }
    }

    fun addCategory() {
        if (editFolderName.isEmpty()) return
        val newCat = FileCategory(
            name = editFolderName,
            extensions = editExtensions.split(",").map { e -> e.trim() }.filter { e -> e.isNotEmpty() },
            keywords = editKeywords.split(",").map { k -> k.trim() }.filter { k -> k.isNotEmpty() },
            subfolderPattern = editSubfolder.trim().ifBlank { null }
        )
        val newCategories = categories.value + newCat
        val newSubfolders = settings.value.subfolders.toMutableMap()
        if (editSubfolder.trim().isNotBlank()) {
            newSubfolders[editFolderName] = editSubfolder.trim()
        }
        viewModelScope.launch(Dispatchers.IO) {
            settingsManager.saveCategories(newCategories)
            settingsManager.saveSettings(settings.value.copy(subfolders = newSubfolders))
        }
    }

    fun prepareNewCategory() {
        activeCategory = null
        editFolderName = ""
        editExtensions = "zip, rar, 7z"
        editKeywords = ""
        editSubfolder = ""
    }

    fun deleteCategory() {
        val currentActive = activeCategory ?: return
        val newCategories = categories.value.filter { it.name != currentActive.name }
        viewModelScope.launch(Dispatchers.IO) {
            settingsManager.saveCategories(newCategories)
        }
        activeCategory = null
    }

    fun toggleCategoryRegex(categoryName: String) {
        val newCategories = categories.value.map {
            if (it.name == categoryName) it.copy(isRegexEnabled = !it.isRegexEnabled) else it
        }
        viewModelScope.launch(Dispatchers.IO) {
            settingsManager.saveCategories(newCategories)
        }
    }

    fun toggleCategoryKeywords(categoryName: String) {
        val newCategories = categories.value.map {
            if (it.name == categoryName) it.copy(isKeywordMatchingEnabled = !it.isKeywordMatchingEnabled) else it
        }
        viewModelScope.launch(Dispatchers.IO) {
            settingsManager.saveCategories(newCategories)
        }
    }

    fun saveRegex() {
        viewModelScope.launch(Dispatchers.IO) {
            val current = settings.value
            settingsManager.saveSettings(current.copy(filenameRegex = editRegex))
        }
    }

    fun updateSettings(newSettings: FilterSettings) {
        viewModelScope.launch(Dispatchers.IO) {
            settingsManager.saveSettings(newSettings)
        }
    }

    fun saveTemplate(name: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val json = templateManager.exportToJson(categories.value, settings.value)
            val dir = File(getApplication<Application>().filesDir, "templates")
            if (!dir.exists()) dir.mkdirs()
            File(dir, "$name.json").writeText(json)
            
            launch(Dispatchers.Main) {
                loadTemplates()
                selectedTemplate = name
            }
            settingsManager.saveSelectedTemplate(name)
        }
    }

    fun deleteTemplate(name: String) {
        if (name == "None") return
        
        viewModelScope.launch(Dispatchers.IO) {
            // Check if it's an asset (we can't delete assets)
            val assets = try { getApplication<Application>().assets.list("templates") ?: emptyArray() } catch (e: Exception) { emptyArray() }
            if (assets.contains("$name.json")) return@launch

            val dir = File(getApplication<Application>().filesDir, "templates")
            val file = File(dir, "$name.json")
            if (file.exists()) file.delete()
            
            launch(Dispatchers.Main) {
                loadTemplates()
            }
            settingsManager.saveSelectedTemplate("None")
        }
    }

    fun loadTemplate(name: String) {
        // Reset local edit state immediately
        activeCategory = null
        editFolderName = ""
        editExtensions = ""
        editKeywords = ""
        editSubfolder = ""

        if (name == "None") {
            viewModelScope.launch {
                settingsManager.resetToDefaults()
                editRegex = ".*"
            }
            return
        }
        
        viewModelScope.launch(Dispatchers.IO) {
            var json: String? = null
            
            // Try to load from internal storage first
            val dir = File(getApplication<Application>().filesDir, "templates")
            val file = File(dir, "$name.json")
            if (file.exists()) {
                json = file.readText()
            } else {
                // Try to load from assets
                try {
                    json = getApplication<Application>().assets.open("templates/$name.json").bufferedReader().use { it.readText() }
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }

            if (json != null) {
                val pair = templateManager.importFromJson(json)
                if (pair != null) {
                    // CRITICAL: We use a custom save that replaces everything to avoid merging
                    settingsManager.saveCategories(pair.first)
                    settingsManager.saveSettings(pair.second)
                    settingsManager.saveSelectedTemplate(name)
                    
                    launch(Dispatchers.Main) {
                        editRegex = pair.second.filenameRegex
                    }
                }
            }
        }
    }
}
