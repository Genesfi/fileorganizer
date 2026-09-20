package com.example.fileorganizer.ui

import android.app.Application
import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.*
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.fileorganizer.data.HistoryBatchEntity
import com.example.fileorganizer.data.HistoryDao
import com.example.fileorganizer.data.SettingsManager
import com.example.fileorganizer.domain.*
import com.google.gson.Gson
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.LocalDateTime
import javax.inject.Inject

@HiltViewModel
class MainViewModel @Inject constructor(
    application: Application,
    private val historyDao: HistoryDao,
    private val settingsManager: SettingsManager
) : AndroidViewModel(application) {

    var selectedFolderUri by mutableStateOf<Uri?>(null)
    var selectedFolderPath by mutableStateOf("")
    var isSimulate by mutableStateOf(false)
    var isRunning by mutableStateOf(false)
    var groupName by mutableStateOf("")
    var progress by mutableStateOf(0f)
    var statusText by mutableStateOf("Ready")
    
    val logs = mutableStateListOf<OrganizationEvent.Log>()
    var statsFiles by mutableStateOf(0)
    var statsSize by mutableStateOf(0L)
    var statsTopCategory by mutableStateOf("-")

    private var organizationJob: Job? = null
    private val gson = Gson()

    val categories: StateFlow<List<FileCategory>> = settingsManager.categoriesFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), settingsManager.getDefaultCategories())

    val settings: StateFlow<FilterSettings> = settingsManager.settingsFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), settingsManager.getDefaultSettings())

    fun onFolderSelected(uri: Uri) {
        selectedFolderUri = uri
        selectedFolderPath = uri.path ?: uri.toString()
        
        // Take persistable permission
        getApplication<Application>().contentResolver.takePersistableUriPermission(
            uri,
            Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        )
    }

    fun runOrganization() {
        val uri = selectedFolderUri ?: return
        
        organizationJob?.cancel()
        
        progress = 0f
        logs.clear()
        statsFiles = 0
        statsSize = 0L
        statsTopCategory = "-"

        organizationJob = viewModelScope.launch {
            // FORCE REFRESH: Get latest data from storage before starting
            val latestCategories = settingsManager.categoriesFlow.first()
            val latestSettings = settingsManager.settingsFlow.first()

            val organizer = FileOrganizer(
                getApplication(), 
                uri, 
                latestCategories, 
                latestSettings, 
                isSimulate,
                groupName
            )

            isRunning = true
            try {
                organizer.start().collect { event ->
                    when (event) {
                        is OrganizationEvent.Progress -> {
                            progress = event.percentage
                            statusText = event.status
                        }
                        is OrganizationEvent.Log -> {
                            logs.add(event)
                            updateStats(event)
                        }
                        is OrganizationEvent.Complete -> {
                            statusText = if (event.success) "Finished" else "Failed"
                            event.batch?.let { saveToHistory(it) }
                        }
                    }
                }
            } catch (e: Exception) {
                if (organizationJob?.isCancelled == false) {
                    logs.add(OrganizationEvent.Log("Error: ${e.message}", LogType.ERROR))
                    statusText = "Error"
                }
            } finally {
                isRunning = false
            }
        }
    }

    fun stopOrganization() {
        organizationJob?.cancel()
        isRunning = false
        statusText = "Stopped"
        logs.add(OrganizationEvent.Log("Operation stopped by user.", LogType.ERROR))
    }

    private fun updateStats(log: OrganizationEvent.Log) {
        if (log.type == LogType.SUCCESS || (isSimulate && log.type == LogType.WARNING)) {
            statsFiles++
        }
    }

    private fun saveToHistory(batch: FileHistoryBatch) {
        viewModelScope.launch {
            historyDao.insertBatch(HistoryBatchEntity(
                timestamp = batch.timestamp.toString(),
                movedFilesJson = gson.toJson(batch.movedFiles)
            ))
        }
    }

    fun undoLast() {
        viewModelScope.launch(Dispatchers.IO) {
            val last = historyDao.getLastBatch() ?: run {
                logs.add(OrganizationEvent.Log("No undo history available.", LogType.INFO))
                return@launch
            }

            val type = object : com.google.gson.reflect.TypeToken<List<MovedFile>>() {}.type
            val movedList: List<MovedFile> = try {
                gson.fromJson(last.movedFilesJson, type)
            } catch (_: Exception) {
                emptyList()
            }

            if (movedList.isEmpty()) {
                historyDao.deleteBatch(last.id)
                logs.add(OrganizationEvent.Log("Undo batch was empty.", LogType.INFO))
                return@launch
            }

            logs.add(OrganizationEvent.Log("Reverting batch with ${movedList.size} items...", LogType.NORMAL))
            var revertedCount = 0
            val contentResolver = getApplication<Application>().contentResolver

            for (mf in movedList) {
                val destUriStr = mf.destinationUri
                val srcParentUriStr = mf.sourceParentUri

                if (destUriStr == null || srcParentUriStr == null) {
                    continue
                }

                try {
                    val destUri = Uri.parse(destUriStr)
                    val srcParentUri = Uri.parse(srcParentUriStr)
                    val destParentUri = mf.destinationParentUri?.let { Uri.parse(it) }

                    val destDoc = if (mf.isDirectory) {
                        androidx.documentfile.provider.DocumentFile.fromTreeUri(getApplication(), destUri)
                    } else {
                        androidx.documentfile.provider.DocumentFile.fromSingleUri(getApplication(), destUri)
                    }
                    val srcParentDoc = androidx.documentfile.provider.DocumentFile.fromTreeUri(getApplication(), srcParentUri)

                    if (destDoc != null && destDoc.exists() && srcParentDoc != null && srcParentDoc.exists()) {
                        var restored = false
                        val moveSourceParentUri = destParentUri ?: destDoc.parentFile?.uri

                        // Attempt 1: Native DocumentsContract moveDocument
                        if (moveSourceParentUri != null) {
                            try {
                                val movedBackUri = android.provider.DocumentsContract.moveDocument(
                                    contentResolver,
                                    destUri,
                                    moveSourceParentUri,
                                    srcParentUri
                                )
                                if (movedBackUri != null) {
                                    restored = true
                                    mf.originalFileName?.let { origName ->
                                        if (origName != destDoc.name) {
                                            try {
                                                android.provider.DocumentsContract.renameDocument(contentResolver, movedBackUri, origName)
                                            } catch (_: Exception) {}
                                        }
                                    }
                                }
                            } catch (_: Exception) {}
                        }

                        // Attempt 2: Fallback copy and delete
                        if (!restored) {
                            if (mf.isDirectory) {
                                restored = copyDirectoryRecursively(destDoc, srcParentDoc, contentResolver)
                                if (restored) {
                                    destDoc.delete()
                                }
                            } else {
                                val targetName = mf.originalFileName ?: destDoc.name ?: "restored_file"
                                val mimeType = destDoc.type ?: "application/octet-stream"
                                val restoredDoc = srcParentDoc.createFile(mimeType, targetName)

                                if (restoredDoc != null) {
                                    contentResolver.openInputStream(destUri)?.use { input ->
                                        contentResolver.openOutputStream(restoredDoc.uri)?.use { output ->
                                            input.copyTo(output)
                                        }
                                    }
                                    destDoc.delete()
                                    restored = true
                                }
                            }
                        }

                        if (restored) {
                            revertedCount++
                            val itemLabel = if (mf.isDirectory) "folder" else "file"
                            logs.add(OrganizationEvent.Log("Restored $itemLabel: ${mf.originalFileName ?: mf.destinationPath}", LogType.SUCCESS))
                        }
                    }
                } catch (e: Exception) {
                    logs.add(OrganizationEvent.Log("Failed to restore ${mf.destinationPath}: ${e.message}", LogType.ERROR))
                }
            }

            historyDao.deleteBatch(last.id)
            logs.add(OrganizationEvent.Log("Undo finished: restored $revertedCount of ${movedList.size} items.", LogType.NORMAL))
        }
    }

    private fun copyDirectoryRecursively(
        sourceDir: androidx.documentfile.provider.DocumentFile,
        targetParentDir: androidx.documentfile.provider.DocumentFile,
        contentResolver: android.content.ContentResolver
    ): Boolean {
        val dirName = sourceDir.name ?: return false
        val newDir = targetParentDir.findFile(dirName) ?: targetParentDir.createDirectory(dirName) ?: return false
        for (child in sourceDir.listFiles()) {
            if (child.isDirectory) {
                copyDirectoryRecursively(child, newDir, contentResolver)
            } else {
                val childName = child.name ?: "file"
                val mimeType = child.type ?: "application/octet-stream"
                val newFile = newDir.createFile(mimeType, childName) ?: continue
                contentResolver.openInputStream(child.uri)?.use { input ->
                    contentResolver.openOutputStream(newFile.uri)?.use { output ->
                        input.copyTo(output)
                    }
                }
            }
        }
        return true
    }

    fun updateSettings(newSettings: FilterSettings) {
        viewModelScope.launch {
            settingsManager.saveSettings(newSettings)
        }
    }
}
