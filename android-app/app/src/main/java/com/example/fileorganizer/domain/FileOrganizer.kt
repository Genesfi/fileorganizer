package com.example.fileorganizer.domain

import android.content.Context
import android.net.Uri
import android.provider.DocumentsContract
import androidx.documentfile.provider.DocumentFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.yield
import java.security.MessageDigest
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

sealed class OrganizationEvent {
    data class Progress(val percentage: Float, val status: String) : OrganizationEvent()
    data class Log(
        val message: String,
        val type: LogType,
        val sourceName: String? = null,
        val targetPath: String? = null,
        val category: String? = null
    ) : OrganizationEvent()
    data class Complete(val success: Boolean, val batch: FileHistoryBatch?) : OrganizationEvent()
}

enum class LogType { NORMAL, SUCCESS, WARNING, ERROR, INFO }

class FileOrganizer(
    private val context: Context,
    private val rootUri: Uri,
    private val categories: List<FileCategory>,
    private val settings: FilterSettings,
    private val isSimulate: Boolean,
    private val groupName: String = ""
) {
    private val filterEngine = FilterEngine(categories, settings)

    fun start(): Flow<OrganizationEvent> = flow {
        val folderMode = settings.organizeFoldersMode
        val itemTypeLabel = if (folderMode) "folders" else "files"
        emit(OrganizationEvent.Log("Scanning target directory for $itemTypeLabel...", LogType.NORMAL))
        
        val rootDoc = DocumentFile.fromTreeUri(context, rootUri)
        if (rootDoc == null || !rootDoc.exists() || !rootDoc.isDirectory) {
            emit(OrganizationEvent.Log("Invalid folder selected.", LogType.ERROR))
            emit(OrganizationEvent.Complete(false, null))
            return@flow
        }

        val itemsToScan = mutableListOf<Pair<DocumentFile, DocumentFile>>() // item to its parent
        if (folderMode) {
            scanFoldersMode(rootDoc, itemsToScan) { status ->
                emit(OrganizationEvent.Progress(0f, status))
            }
        } else {
            scanFilesMode(rootDoc, itemsToScan) { status ->
                emit(OrganizationEvent.Progress(0f, status))
            }
        }
        
        emit(OrganizationEvent.Log("Found ${itemsToScan.size} $itemTypeLabel to organize.", LogType.NORMAL))
        
        if (itemsToScan.isEmpty()) {
            emit(OrganizationEvent.Log("No $itemTypeLabel found to organize.", LogType.INFO))
            emit(OrganizationEvent.Complete(true, null))
            return@flow
        }

        // Handle Group Folder
        var currentRoot = rootDoc
        if (groupName.isNotBlank()) {
            val existingGroup = rootDoc.findFile(groupName)
            currentRoot = if (existingGroup != null && existingGroup.isDirectory) {
                existingGroup
            } else if (!isSimulate) {
                rootDoc.createDirectory(groupName) ?: rootDoc
            } else {
                rootDoc
            }
            
            if (currentRoot == rootDoc && !isSimulate && groupName.isNotBlank()) {
                emit(OrganizationEvent.Log("Warning: Could not create group folder '$groupName', using root instead.", LogType.WARNING))
            }
        }

        val total = itemsToScan.size
        var processed = 0
        var movedCount = 0
        var filteredCount = 0
        val movedFiles = mutableListOf<MovedFile>()

        for ((itemDoc, parentDoc) in itemsToScan) {
            val itemName = itemDoc.name ?: "unknown"
            val category = if (folderMode) {
                filterEngine.getFolderCategory(itemName)
            } else {
                filterEngine.getCategory(itemDoc)
            }

            val (isValid, reason) = if (folderMode) {
                filterEngine.isValidFolder(itemDoc, category)
            } else {
                filterEngine.isValid(itemDoc, category)
            }

            if (!isValid) {
                emit(OrganizationEvent.Log("Filtered: $itemName ($reason)", LogType.INFO, sourceName = itemName))
                filteredCount++
            } else {
                val categoryName = category!!
                val ext = if (folderMode) "" else itemName.substringAfterLast(".", "").lowercase()
                
                // 1. Calculate category folder name
                val catFolderName = if (settings.enableOutputDate && settings.outputDate.isNotBlank()) {
                    "${categoryName}_${settings.outputDate}"
                } else {
                    categoryName
                }

                // 2. Calculate subfolder name (if subfolder nesting is enabled)
                val catObj = categories.find { it.name == categoryName }
                val subfolderName = if (settings.enableMoveSubfolder) {
                    calculateSubfolderName(itemDoc, ext, catObj, folderMode)
                } else {
                    ""
                }

                // 3. Resolve destination directory in filesystem (if not simulate)
                var destCategoryDir: DocumentFile? = null
                var finalDestDir: DocumentFile? = null

                if (!isSimulate) {
                    destCategoryDir = currentRoot.findFile(catFolderName)
                        ?: currentRoot.createDirectory(catFolderName)

                    finalDestDir = if (destCategoryDir != null && subfolderName.isNotEmpty()) {
                        destCategoryDir.findFile(subfolderName)
                            ?: destCategoryDir.createDirectory(subfolderName)
                    } else {
                        destCategoryDir
                    }
                }

                // 4. Prevent moving item if it's already in the target destination
                val isAlreadyOrganized = if (finalDestDir != null) {
                    parentDoc.uri == finalDestDir.uri
                } else {
                    if (subfolderName.isNotEmpty()) {
                        parentDoc.name == subfolderName
                    } else {
                        parentDoc.name == catFolderName
                    }
                }

                if (isAlreadyOrganized) {
                    emit(OrganizationEvent.Log("Already organized: $itemName", LogType.INFO, sourceName = itemName))
                    processed++
                    emit(OrganizationEvent.Progress(processed.toFloat() / total, "Processing $itemName..."))
                    continue
                }

                // 5. Check duplicate & conflict resolution
                val finalDestName = handleConflict(finalDestDir, itemDoc, itemName)

                if (finalDestName == null) {
                    emit(OrganizationEvent.Log("[Duplicate] Skipped: $itemName (already exists in destination)", LogType.INFO, sourceName = itemName))
                } else {
                    val relPath = buildRelativePath(catFolderName, subfolderName, finalDestName)

                    if (isSimulate) {
                        emit(OrganizationEvent.Log("[Simulate] Would move $itemName -> $relPath", LogType.WARNING, sourceName = itemName, targetPath = relPath, category = categoryName))
                        movedFiles.add(
                            MovedFile(
                                sourceUri = itemDoc.uri.toString(),
                                sourceParentUri = parentDoc.uri.toString(),
                                destinationUri = null,
                                destinationParentUri = finalDestDir?.uri?.toString(),
                                destinationPath = relPath,
                                category = categoryName,
                                size = if (folderMode) 0L else itemDoc.length(),
                                originalFileName = itemName,
                                isDirectory = folderMode
                            )
                        )
                        movedCount++
                    } else {
                        try {
                            if (finalDestDir == null) {
                                emit(OrganizationEvent.Log("Failed to create destination folder for $relPath", LogType.ERROR, sourceName = itemName))
                            } else {
                                val movedDoc = if (folderMode) {
                                    performMoveFolder(itemDoc, parentDoc, finalDestDir, itemName, finalDestName)
                                } else {
                                    performMoveFile(itemDoc, parentDoc, finalDestDir, itemName, finalDestName)
                                }

                                if (movedDoc != null) {
                                    emit(OrganizationEvent.Log("Moved: $itemName -> $relPath", LogType.SUCCESS, sourceName = itemName, targetPath = relPath, category = categoryName))
                                    movedFiles.add(
                                        MovedFile(
                                            sourceUri = itemDoc.uri.toString(),
                                            sourceParentUri = parentDoc.uri.toString(),
                                            destinationUri = movedDoc.uri.toString(),
                                            destinationParentUri = finalDestDir.uri.toString(),
                                            destinationPath = relPath,
                                            category = categoryName,
                                            size = if (folderMode) 0L else itemDoc.length(),
                                            originalFileName = itemName,
                                            isDirectory = folderMode
                                        )
                                    )
                                    movedCount++
                                } else {
                                    emit(OrganizationEvent.Log("Failed to move $itemName to $relPath", LogType.ERROR, sourceName = itemName))
                                }
                            }
                        } catch (e: Exception) {
                            emit(OrganizationEvent.Log("Error moving $itemName: ${e.message}", LogType.ERROR, sourceName = itemName))
                        }
                    }
                }
            }

            processed++
            emit(OrganizationEvent.Progress(processed.toFloat() / total, "Processing $itemName..."))
        }

        emit(OrganizationEvent.Log("--- Summary ---", LogType.NORMAL))
        if (isSimulate) {
            emit(OrganizationEvent.Log("Simulated: $movedCount $itemTypeLabel, Filtered: $filteredCount $itemTypeLabel.", LogType.NORMAL))
        } else {
            emit(OrganizationEvent.Log("Moved: $movedCount $itemTypeLabel, Filtered: $filteredCount $itemTypeLabel.", LogType.NORMAL))
        }

        val batch = if (movedFiles.isNotEmpty()) {
            FileHistoryBatch(timestamp = LocalDateTime.now(), movedFiles = movedFiles, groupFolder = groupName.ifBlank { null })
        } else null

        emit(OrganizationEvent.Complete(true, batch))
    }.flowOn(Dispatchers.IO)

    /**
     * Scan items in Folder Mode: detects subdirectories matching category keywords.
     */
    private suspend fun scanFoldersMode(
        folder: DocumentFile,
        result: MutableList<Pair<DocumentFile, DocumentFile>>,
        onProgress: suspend (String) -> Unit
    ) {
        onProgress("Scanning folders in: ${folder.name ?: ""}")
        yield()
        val files = folder.listFiles()

        for (file in files) {
            yield()
            if (!file.isDirectory) continue

            val name = file.name ?: ""

            // 1. Skip group folder
            if (groupName.isNotBlank() && name.equals(groupName, ignoreCase = true)) {
                continue
            }

            // 2. Skip category folders to prevent recursion
            val isCategoryDir = categories.any { cat ->
                name.equals(cat.name, ignoreCase = true) || name.startsWith("${cat.name}_", ignoreCase = true)
            }
            if (isCategoryDir) {
                continue
            }

            // 3. Skip except folders
            val isExceptFolder = settings.exceptFolders.any { excl ->
                excl.isNotBlank() && (name.equals(excl, ignoreCase = true) || file.uri.toString().contains(excl))
            }
            if (isExceptFolder) {
                continue
            }

            // Check if folder name matches a category keyword
            val category = filterEngine.getFolderCategory(name)
            if (category != null) {
                result.add(file to folder)
                // Don't scan inside matched folder because the whole folder moves
            } else if (settings.scanSubfolders) {
                scanFoldersMode(file, result, onProgress)
            }
        }
    }

    /**
     * Scan items in File Mode.
     */
    private suspend fun scanFilesMode(
        folder: DocumentFile,
        result: MutableList<Pair<DocumentFile, DocumentFile>>,
        onProgress: suspend (String) -> Unit
    ) {
        onProgress("Scanning files in: ${folder.name ?: ""}")
        yield()
        val files = folder.listFiles()
        
        for (file in files) {
            yield()
            val name = file.name ?: ""
            
            if (file.isFile) {
                result.add(file to folder)
            } else if (file.isDirectory) {
                // 1. Group folder
                if (groupName.isNotBlank() && name.equals(groupName, ignoreCase = true)) {
                    continue
                }
                
                // 2. Category folders
                val isCategoryDir = categories.any { cat ->
                    name.equals(cat.name, ignoreCase = true) || name.startsWith("${cat.name}_", ignoreCase = true)
                }
                if (isCategoryDir) {
                    continue
                }
                
                // 3. Except folders
                val isExceptFolder = settings.exceptFolders.any { excl ->
                    excl.isNotBlank() && (name.equals(excl, ignoreCase = true) || file.uri.toString().contains(excl))
                }
                if (isExceptFolder) {
                    continue
                }
                
                if (settings.scanSubfolders) {
                    scanFilesMode(file, result, onProgress)
                }
            }
        }
    }

    private fun calculateSubfolderName(docFile: DocumentFile, ext: String, catObj: FileCategory?, folderMode: Boolean): String {
        val catName = catObj?.name ?: ""
        val pattern = settings.subfolders[catName] ?: catObj?.subfolderPattern ?: ""
        
        val baseName = if (pattern.isEmpty()) {
            if (folderMode) "FOLDERS" else (if (ext.isNotEmpty()) ext.uppercase() else "NO_EXT")
        } else {
            pattern
        }

        if (settings.disableSuffixOnSubfolder) return baseName

        return try {
            val mtime = Instant.ofEpochMilli(docFile.lastModified()).atZone(ZoneId.systemDefault()).toLocalDateTime()
            val dateStr = mtime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"))
            "${baseName}_$dateStr"
        } catch (_: Exception) {
            baseName
        }
    }

    private fun buildRelativePath(catFolder: String, subFolder: String, itemName: String): String {
        val parts = mutableListOf<String>()
        if (groupName.isNotBlank()) parts.add(groupName)
        parts.add(catFolder)
        if (subFolder.isNotBlank()) parts.add(subFolder)
        parts.add(itemName)
        return parts.joinToString("/")
    }

    private fun handleConflict(destDir: DocumentFile?, srcItem: DocumentFile, itemName: String): String? {
        if (destDir == null) return itemName
        val destFile = destDir.findFile(itemName) ?: return itemName
        
        // Smart duplicate check (for files)
        if (!srcItem.isDirectory && settings.skipExactDuplicates) {
            if (srcItem.length() == destFile.length()) {
                val srcHash = calculateHash(srcItem)
                val destHash = calculateHash(destFile)
                if (srcHash != null && srcHash == destHash) {
                    return null // Exact duplicate: skip
                }
            }
        }
        
        var counter = 1
        val isDir = srcItem.isDirectory
        val namePart = if (isDir || !itemName.contains(".")) itemName else itemName.substringBeforeLast(".")
        val extPart = if (!isDir && itemName.contains(".")) itemName.substringAfterLast(".") else ""
        var newName = if (extPart.isNotEmpty()) "$namePart ($counter).$extPart" else "$namePart ($counter)"
        
        while (destDir.findFile(newName) != null) {
            counter++
            newName = if (extPart.isNotEmpty()) "$namePart ($counter).$extPart" else "$namePart ($counter)"
        }
        return newName
    }

    /**
     * Executes file move using native SAF moveDocument with safe stream fallback.
     */
    private fun performMoveFile(
        srcFile: DocumentFile,
        srcParent: DocumentFile,
        destDir: DocumentFile,
        originalName: String,
        targetName: String
    ): DocumentFile? {
        // Step 1: Native move
        try {
            val movedUri = DocumentsContract.moveDocument(
                context.contentResolver,
                srcFile.uri,
                srcParent.uri,
                destDir.uri
            )
            if (movedUri != null) {
                if (targetName != originalName) {
                    val renamedUri = try {
                        DocumentsContract.renameDocument(context.contentResolver, movedUri, targetName)
                    } catch (_: Exception) {
                        null
                    }
                    return DocumentFile.fromSingleUri(context, renamedUri ?: movedUri)
                }
                return DocumentFile.fromSingleUri(context, movedUri)
            }
        } catch (_: Exception) {}

        // Step 2: Stream copy fallback
        val mimeType = srcFile.type ?: "application/octet-stream"
        val targetDoc = destDir.createFile(mimeType, targetName)
            ?: throw IllegalStateException("Could not create target file: $targetName")

        var bytesCopied = 0L
        try {
            context.contentResolver.openInputStream(srcFile.uri)?.use { input ->
                context.contentResolver.openOutputStream(targetDoc.uri)?.use { output ->
                    val buffer = ByteArray(65536)
                    var read: Int
                    while (input.read(buffer).also { read = it } != -1) {
                        output.write(buffer, 0, read)
                        bytesCopied += read
                    }
                    output.flush()
                }
            } ?: throw IllegalStateException("Cannot open stream for ${srcFile.name}")

            val srcLength = srcFile.length()
            if (srcLength > 0 && bytesCopied != srcLength) {
                targetDoc.delete()
                throw IllegalStateException("Size mismatch: copied $bytesCopied bytes, expected $srcLength")
            }

            val deleted = try {
                srcFile.delete() || DocumentsContract.deleteDocument(context.contentResolver, srcFile.uri)
            } catch (_: Exception) {
                false
            }

            if (!deleted) {
                targetDoc.delete()
                throw IllegalStateException("Source file could not be deleted (read-only), move aborted")
            }

            return targetDoc
        } catch (e: Exception) {
            try { targetDoc.delete() } catch (_: Exception) {}
            throw e
        }
    }

    /**
     * Executes folder move using native SAF moveDocument with recursive copy fallback.
     */
    private fun performMoveFolder(
        srcDir: DocumentFile,
        srcParent: DocumentFile,
        destDir: DocumentFile,
        originalName: String,
        targetName: String
    ): DocumentFile? {
        // Step 1: Try native moveDocument
        try {
            val movedUri = DocumentsContract.moveDocument(
                context.contentResolver,
                srcDir.uri,
                srcParent.uri,
                destDir.uri
            )
            if (movedUri != null) {
                if (targetName != originalName) {
                    val renamedUri = try {
                        DocumentsContract.renameDocument(context.contentResolver, movedUri, targetName)
                    } catch (_: Exception) {
                        null
                    }
                    return DocumentFile.fromTreeUri(context, renamedUri ?: movedUri)
                }
                return DocumentFile.fromTreeUri(context, movedUri)
            }
        } catch (_: Exception) {}

        // Step 2: Recursive copy directory fallback
        val newTargetDir = destDir.createDirectory(targetName)
            ?: throw IllegalStateException("Could not create target directory: $targetName")

        try {
            copyDirectoryRecursive(srcDir, newTargetDir)

            val deleted = try {
                srcDir.delete() || DocumentsContract.deleteDocument(context.contentResolver, srcDir.uri)
            } catch (_: Exception) {
                false
            }

            if (!deleted) {
                // Rollback target directory
                try { newTargetDir.delete() } catch (_: Exception) {}
                throw IllegalStateException("Source folder could not be deleted (read-only), move aborted")
            }

            return newTargetDir
        } catch (e: Exception) {
            try { newTargetDir.delete() } catch (_: Exception) {}
            throw e
        }
    }

    private fun copyDirectoryRecursive(src: DocumentFile, dst: DocumentFile) {
        val children = src.listFiles()
        for (child in children) {
            val name = child.name ?: continue
            if (child.isDirectory) {
                val newSub = dst.createDirectory(name)
                    ?: throw IllegalStateException("Could not create directory $name in ${dst.name}")
                copyDirectoryRecursive(child, newSub)
            } else if (child.isFile) {
                val mime = child.type ?: "application/octet-stream"
                val newFile = dst.createFile(mime, name)
                    ?: throw IllegalStateException("Could not create file $name in ${dst.name}")
                
                context.contentResolver.openInputStream(child.uri)?.use { inStream ->
                    context.contentResolver.openOutputStream(newFile.uri)?.use { outStream ->
                        val buf = ByteArray(65536)
                        var len: Int
                        while (inStream.read(buf).also { len = it } != -1) {
                            outStream.write(buf, 0, len)
                        }
                        outStream.flush()
                    }
                }
            }
        }
    }

    private fun calculateHash(docFile: DocumentFile): String? {
        return try {
            val digest = MessageDigest.getInstance("MD5")
            context.contentResolver.openInputStream(docFile.uri)?.use { input ->
                val buffer = ByteArray(65536)
                var bytesRead: Int
                while (input.read(buffer).also { bytesRead = it } != -1) {
                    digest.update(buffer, 0, bytesRead)
                }
            }
            digest.digest().joinToString("") { "%02x".format(it) }
        } catch (_: Exception) {
            null
        }
    }
}
