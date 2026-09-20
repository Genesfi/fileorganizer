package com.example.fileorganizer.domain

import java.time.LocalDateTime

data class FileCategory(
    val name: String,
    val extensions: List<String>,
    val keywords: List<String> = emptyList(),
    val isKeywordMatchingEnabled: Boolean = false,
    val isRegexEnabled: Boolean = false,
    val subfolderPattern: String? = null
)

data class FilterSettings(
    val includedCategories: List<String> = emptyList(),
    val exceptFolders: List<String> = emptyList(),
    val filenameRegex: String = ".*",
    val blacklist: List<String> = emptyList(),
    
    val enableSizeFilter: Boolean = false,
    val minSize: Long = 0,
    val minSizeUnit: String = "MB",
    val maxSize: Long = 0,
    val maxSizeUnit: String = "MB",
    
    val enableDatetimeFilter: Boolean = false,
    val dateFrom: LocalDateTime? = null,
    val dateTo: LocalDateTime? = null,
    
    val enableOutputDate: Boolean = false,
    val outputDate: String = "",
    val language: String = "English",
    val skipExactDuplicates: Boolean = true,
    val scanSubfolders: Boolean = false,
    val enableMoveSubfolder: Boolean = false,
    val disableSuffixOnSubfolder: Boolean = false,
    val organizeFoldersMode: Boolean = false,
    val subfolders: Map<String, String> = emptyMap()
)

data class MovedFile(
    val sourceUri: String,
    val sourceParentUri: String? = null,
    val destinationUri: String? = null,
    val destinationParentUri: String? = null,
    val destinationPath: String, // Relative to root
    val category: String,
    val size: Long,
    val originalFileName: String? = null,
    val isDirectory: Boolean = false
)

data class FileHistoryBatch(
    val id: Long = 0,
    val timestamp: LocalDateTime,
    val movedFiles: List<MovedFile>,
    val groupFolder: String? = null
)
