package com.example.fileorganizer.data

import com.example.fileorganizer.domain.FileCategory
import com.example.fileorganizer.domain.FilterSettings
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.reflect.TypeToken

class TemplateManager {
    private val gson = Gson()

    fun exportToJson(categories: List<FileCategory>, settings: FilterSettings): String {
        val root = JsonObject()
        
        // Match Python structure: "types": {"Category": ["ext1", "ext2"]}
        val typesObj = JsonObject()
        val keywordsObj = JsonObject()
        val keywordApplyTypesObj = JsonObject()
        val regexApplyTypesObj = JsonObject()
        val subfoldersObj = JsonObject()
        
        categories.forEach { cat ->
            typesObj.add(cat.name, gson.toJsonTree(cat.extensions))
            keywordsObj.add(cat.name, gson.toJsonTree(cat.keywords))
            keywordApplyTypesObj.addProperty(cat.name, cat.isKeywordMatchingEnabled)
            regexApplyTypesObj.addProperty(cat.name, cat.isRegexEnabled)
            val subPattern = cat.subfolderPattern ?: settings.subfolders[cat.name]
            if (!subPattern.isNullOrEmpty()) {
                subfoldersObj.addProperty(cat.name, subPattern)
            }
        }
        
        // Also add any other subfolder patterns from settings
        settings.subfolders.forEach { (catName, pattern) ->
            if (!subfoldersObj.has(catName)) {
                subfoldersObj.addProperty(catName, pattern)
            }
        }
        
        root.add("types", typesObj)
        root.add("keywords", keywordsObj)
        root.add("keyword_apply_types", keywordApplyTypesObj)
        root.add("regex_apply_types", regexApplyTypesObj)
        root.add("subfolders", subfoldersObj)

        root.addProperty("filename_regex", settings.filenameRegex)
        root.add("included_categories", gson.toJsonTree(settings.includedCategories))
        root.add("except_folders", gson.toJsonTree(settings.exceptFolders))
        root.add("blacklist", gson.toJsonTree(settings.blacklist))
        root.addProperty("scan_subfolders", settings.scanSubfolders)
        root.addProperty("enable_size_filter", settings.enableSizeFilter)
        root.addProperty("min_size", settings.minSize)
        root.addProperty("min_size_unit", settings.minSizeUnit)
        root.addProperty("max_size", settings.maxSize)
        root.addProperty("max_size_unit", settings.maxSizeUnit)
        root.addProperty("enable_move_subfolder", settings.enableMoveSubfolder)
        root.addProperty("disable_suffix_on_subfolder", settings.disableSuffixOnSubfolder)
        root.addProperty("enable_output_date", settings.enableOutputDate)
        root.addProperty("output_date", settings.outputDate)
        root.addProperty("skip_exact_duplicates", settings.skipExactDuplicates)
        root.addProperty("organize_folders_mode", settings.organizeFoldersMode)
        
        return gson.toJson(root)
    }

    fun importFromJson(jsonString: String): Pair<List<FileCategory>, FilterSettings>? {
        return try {
            val root = gson.fromJson(jsonString, JsonObject::class.java) ?: return null
            val types = root.getAsJsonObject("types") ?: return null
            val keywords = root.getAsJsonObject("keywords") ?: JsonObject()
            val keywordApplyTypes = root.getAsJsonObject("keyword_apply_types") ?: JsonObject()
            val regexApplyTypes = root.getAsJsonObject("regex_apply_types") ?: JsonObject()
            val subfoldersJson = root.getAsJsonObject("subfolders") ?: JsonObject()

            val subfoldersMap = mutableMapOf<String, String>()
            subfoldersJson.entrySet().forEach { (k, v) ->
                try {
                    subfoldersMap[k] = v.asString
                } catch (_: Exception) {}
            }
            
            val categories = types.entrySet().map { (name, exts) ->
                val catKeywords = if (keywords.has(name)) {
                    try { gson.fromJson(keywords.get(name), Array<String>::class.java).toList() } catch (e: Exception) { emptyList() }
                } else emptyList()
                
                val isKeywordEnabled = if (keywordApplyTypes.has(name)) {
                    keywordApplyTypes.get(name).asBoolean
                } else {
                    catKeywords.isNotEmpty()
                }

                val isRegexEnabled = if (regexApplyTypes.has(name)) {
                    regexApplyTypes.get(name).asBoolean
                } else false

                val subPattern = subfoldersMap[name]
                
                FileCategory(
                    name = name,
                    extensions = try { gson.fromJson(exts, Array<String>::class.java).toList() } catch (e: Exception) { emptyList() },
                    keywords = catKeywords,
                    isKeywordMatchingEnabled = isKeywordEnabled,
                    isRegexEnabled = isRegexEnabled,
                    subfolderPattern = subPattern
                )
            }

            val includedCats = if (root.has("included_categories")) {
                val list = try { gson.fromJson(root.get("included_categories"), Array<String>::class.java)?.toList() ?: emptyList() } catch (e: Exception) { emptyList() }
                list.filter { catName -> categories.any { it.name == catName } || catName == "Others" }
            } else {
                categories.map { it.name }
            }

            val settings = FilterSettings(
                includedCategories = includedCats,
                exceptFolders = try { gson.fromJson(root.get("except_folders"), Array<String>::class.java)?.toList() ?: emptyList() } catch (e: Exception) { emptyList() },
                blacklist = if (root.has("blacklist")) {
                    val blElem = root.get("blacklist")
                    if (blElem.isJsonArray) {
                        try { gson.fromJson(blElem, Array<String>::class.java)?.toList() ?: emptyList() } catch (e: Exception) { emptyList() }
                    } else if (blElem.isJsonPrimitive) {
                        blElem.asString.split("\n").map { it.trim() }.filter { it.isNotEmpty() }
                    } else emptyList()
                } else emptyList(),
                filenameRegex = root.get("filename_regex")?.asString ?: ".*",
                scanSubfolders = root.get("scan_subfolders")?.asBoolean ?: false,
                enableSizeFilter = root.get("enable_size_filter")?.asBoolean ?: false,
                minSize = root.get("min_size")?.asLong ?: 0L,
                minSizeUnit = root.get("min_size_unit")?.asString ?: "MB",
                maxSize = root.get("max_size")?.asLong ?: 0L,
                maxSizeUnit = root.get("max_size_unit")?.asString ?: "MB",
                enableMoveSubfolder = root.get("enable_move_subfolder")?.asBoolean ?: subfoldersMap.isNotEmpty(),
                disableSuffixOnSubfolder = root.get("disable_suffix_on_subfolder")?.asBoolean ?: false,
                enableOutputDate = root.get("enable_output_date")?.asBoolean ?: false,
                outputDate = root.get("output_date")?.asString ?: "",
                skipExactDuplicates = root.get("skip_exact_duplicates")?.asBoolean ?: true,
                organizeFoldersMode = root.get("organize_folders_mode")?.asBoolean ?: false,
                subfolders = subfoldersMap
            )

            categories to settings
        } catch (e: Exception) {
            null
        }
    }
}
