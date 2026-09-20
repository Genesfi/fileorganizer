package com.example.fileorganizer.domain

import androidx.documentfile.provider.DocumentFile
import java.time.Instant
import java.time.ZoneId
import java.util.regex.Pattern

class FilterEngine(
    private val categories: List<FileCategory>,
    private val settings: FilterSettings
) {
    fun getCategory(docFile: DocumentFile): String? {
        val fileName = docFile.name ?: return null
        val ext = fileName.substringAfterLast(".", "").lowercase()
        val fileNameLower = fileName.lowercase()

        // Match categories that have this extension
        val matchedCategories = categories.filter { cat ->
            cat.extensions.any { 
                it.removePrefix(".").lowercase() == ext 
            }
        }

        if (matchedCategories.isEmpty()) {
            // Check if "Others" is in included_categories
            return if (settings.includedCategories.contains("Others")) "Others" else null
        }

        // Check which matched categories are active (in includedCategories)
        val activeMatches = matchedCategories.filter { settings.includedCategories.contains(it.name) }
        if (activeMatches.isEmpty()) return null

        // 1. Look for a category that has keyword matching enabled and matches the filename
        for (cat in activeMatches) {
            if (cat.isKeywordMatchingEnabled && cat.keywords.isNotEmpty()) {
                val matched = cat.keywords.any { kw ->
                    matchesKeyword(fileName, kw)
                }
                if (matched) {
                    return cat.name
                }
            }
        }

        // 2. If no keyword-specific category matched, fall back to first category that does NOT have keyword matching enabled
        for (cat in activeMatches) {
            if (!cat.isKeywordMatchingEnabled) {
                return cat.name
            }
        }

        // 3. If all active matches require keywords but none matched, we return null (not organized).
        // Matches organizer.py line 96-97: do NOT fallback to Others!
        return null
    }

    /**
     * Matches folder name against included categories that have keyword matching enabled.
     * Corresponds to organizer.py get_folder_category().
     */
    fun getFolderCategory(folderName: String): String? {
        for (cat in categories) {
            if (settings.includedCategories.contains(cat.name)) {
                if (cat.isKeywordMatchingEnabled && cat.keywords.isNotEmpty()) {
                    val matched = cat.keywords.any { kw ->
                        matchesKeyword(folderName, kw)
                    }
                    if (matched) {
                        return cat.name
                    }
                }
            }
        }
        return null
    }

    /**
     * Checks if a target string matches a keyword.
     * Supports special keyword tags:
     * - "[japanese]", "[jp]", "[kana]": matches if the text contains any Japanese Hiragana or Katakana.
     */
    private fun matchesKeyword(targetName: String, keyword: String): Boolean {
        val trimmed = keyword.trim()
        if (trimmed.isEmpty()) return false
        val trimmedLower = trimmed.lowercase()

        if (trimmedLower == "[japanese]" || trimmedLower == "[jp]" || trimmedLower == "[kana]") {
            return targetName.any { ch ->
                (ch in '\u3040'..'\u309F') || (ch in '\u30A0'..'\u30FF')
            }
        }

        return trimmedLower in targetName.lowercase()
    }

    fun isValidFolder(folderDoc: DocumentFile, category: String?): Pair<Boolean, String> {
        if (category == null) return false to "category_excluded"
        if (!settings.includedCategories.contains(category)) return false to "category_excluded"

        val folderName = folderDoc.name ?: return false to "invalid_name"
        val folderNameLower = folderName.lowercase()

        // 1. Check except folders
        val docUriString = folderDoc.uri.toString()
        for (excl in settings.exceptFolders) {
            if (excl.isNotBlank() && (folderName.equals(excl, ignoreCase = true) || docUriString.contains(excl))) {
                return false to "excluded_folder"
            }
        }

        // 2. Regex check
        val cat = categories.find { it.name == category }
        if (cat?.isRegexEnabled == true && settings.filenameRegex.isNotBlank()) {
            try {
                if (!Pattern.compile(settings.filenameRegex).matcher(folderName).find()) {
                    return false to "regex_mismatch"
                }
            } catch (_: Exception) {
                return false to "regex_error"
            }
        }

        // 3. Blacklist check
        if (settings.blacklist.isNotEmpty()) {
            for (kw in settings.blacklist) {
                val trimmed = kw.trim().lowercase()
                if (trimmed.isNotEmpty() && trimmed in folderNameLower) {
                    return false to "blacklisted_keyword"
                }
            }
        }

        // 4. Keyword check
        if (cat != null && cat.isKeywordMatchingEnabled && cat.keywords.isNotEmpty()) {
            val matched = cat.keywords.any { kw ->
                matchesKeyword(folderName, kw)
            }
            if (!matched) {
                return false to "keyword_mismatch"
            }
        }

        // 5. Date filter
        if (settings.enableDatetimeFilter) {
            val mtime = Instant.ofEpochMilli(folderDoc.lastModified()).atZone(ZoneId.systemDefault()).toLocalDateTime()
            if (settings.dateFrom != null && mtime.isBefore(settings.dateFrom)) return false to "date_range_mismatch"
            if (settings.dateTo != null && mtime.isAfter(settings.dateTo)) return false to "date_range_mismatch"
        }

        return true to "ok"
    }

    fun isValid(docFile: DocumentFile, category: String?): Pair<Boolean, String> {
        if (category == null) return false to "category_excluded"
        if (!settings.includedCategories.contains(category)) return false to "category_excluded"

        val fileName = docFile.name ?: return false to "invalid_name"
        val fileNameLower = fileName.lowercase()

        // 1. Check except folders
        val docUriString = docFile.uri.toString()
        for (excl in settings.exceptFolders) {
            if (excl.isNotBlank() && (fileName == excl || docUriString.contains(excl))) {
                return false to "excluded_folder"
            }
        }

        // 2. Regex check (if active for this category)
        val cat = categories.find { it.name == category }
        if (cat?.isRegexEnabled == true && settings.filenameRegex.isNotBlank()) {
            try {
                if (!Pattern.compile(settings.filenameRegex).matcher(fileName).find()) {
                    return false to "regex_mismatch"
                }
            } catch (e: Exception) {
                return false to "regex_error"
            }
        }

        // 3. Blacklist check (global)
        if (settings.blacklist.isNotEmpty()) {
            for (kw in settings.blacklist) {
                val trimmed = kw.trim().lowercase()
                if (trimmed.isNotEmpty() && trimmed in fileNameLower) {
                    return false to "blacklisted_keyword"
                }
            }
        }

        // 4. Category Keywords filter check (if active for this category)
        if (cat != null && cat.isKeywordMatchingEnabled && cat.keywords.isNotEmpty()) {
            val matched = cat.keywords.any { kw ->
                matchesKeyword(fileName, kw)
            }
            if (!matched) {
                return false to "keyword_mismatch"
            }
        }

        // 5. Size filter
        if (settings.enableSizeFilter) {
            val size = docFile.length()
            val minBytes = toBytes(settings.minSize, settings.minSizeUnit)
            val maxBytes = toBytes(settings.maxSize, settings.maxSizeUnit)

            if (size < minBytes) return false to "too_small"
            if (maxBytes > 0 && size > maxBytes) return false to "too_large"
        }

        // 6. Date filter
        if (settings.enableDatetimeFilter) {
            val mtime = Instant.ofEpochMilli(docFile.lastModified()).atZone(ZoneId.systemDefault()).toLocalDateTime()
            if (settings.dateFrom != null && mtime.isBefore(settings.dateFrom)) return false to "date_range_mismatch"
            if (settings.dateTo != null && mtime.isAfter(settings.dateTo)) return false to "date_range_mismatch"
        }

        return true to "ok"
    }

    private fun toBytes(valUnits: Long, unit: String): Long {
        return when (unit.uppercase()) {
            "KB" -> valUnits * 1024L
            "MB" -> valUnits * 1024L * 1024L
            "GB" -> valUnits * 1024L * 1024L * 1024L
            else -> valUnits
        }
    }
}
