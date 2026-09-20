package com.example.fileorganizer.ui

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.fileorganizer.R
import com.example.fileorganizer.domain.LogType
import com.example.fileorganizer.domain.OrganizationEvent
import com.example.fileorganizer.ui.theme.*
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    viewModel: MainViewModel = hiltViewModel(),
    onOpenSettings: () -> Unit
) {
    val context = LocalContext.current
    val launcher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree()
    ) { uri ->
        uri?.let { viewModel.onFolderSelected(it) }
    }

    var showFolderBrowserDialog by remember { mutableStateOf(false) }
    var showPermissionDialog by remember { mutableStateOf(false) }
    var currentBrowsePath by remember {
        val downloadDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        mutableStateOf(if (downloadDir.exists()) downloadDir.absolutePath else Environment.getExternalStorageDirectory().absolutePath)
    }

    val checkPermissionAndOpen: (() -> Unit) -> Unit = { onGranted ->
        val hasPermission = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Environment.isExternalStorageManager()
        } else {
            true
        }
        if (!hasPermission) {
            showPermissionDialog = true
        } else {
            onGranted()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.app_name)) },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(16.dp)
        ) {
            // 1. Mobile Friendly Folder Selection Card
            Card(
                onClick = {
                    checkPermissionAndOpen { showFolderBrowserDialog = true }
                },
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = if (viewModel.selectedFolderUri == null) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)
                ),
                shape = MaterialTheme.shapes.medium
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Default.FolderOpen,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(32.dp)
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = if (viewModel.selectedFolderPath.isNotBlank()) "Target Directory" else "Select Target Directory",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.outline
                        )
                        Text(
                            text = if (viewModel.selectedFolderPath.isNotBlank()) viewModel.selectedFolderPath else "Tap here to select folder...",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 2
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    OutlinedButton(
                        onClick = {
                            checkPermissionAndOpen { showFolderBrowserDialog = true }
                        },
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                    ) {
                        Text("Browse", fontSize = 12.sp)
                    }
                }
            }

            // Quick Folder Presets (Directly solves Scoped Storage Download restriction)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Quick:", fontSize = 11.sp, color = MaterialTheme.colorScheme.outline)
                
                AssistChip(
                    onClick = {
                        checkPermissionAndOpen {
                            val downloadDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                            viewModel.onFolderSelected(Uri.fromFile(downloadDir))
                        }
                    },
                    label = { Text("Download", fontSize = 11.sp) },
                    leadingIcon = {
                        Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(14.dp))
                    }
                )

                AssistChip(
                    onClick = {
                        checkPermissionAndOpen {
                            val storageDir = Environment.getExternalStorageDirectory()
                            viewModel.onFolderSelected(Uri.fromFile(storageDir))
                        }
                    },
                    label = { Text("Storage", fontSize = 11.sp) },
                    leadingIcon = {
                        Icon(Icons.Default.Smartphone, contentDescription = null, modifier = Modifier.size(14.dp))
                    }
                )

                AssistChip(
                    onClick = { launcher.launch(null) },
                    label = { Text("SAF Picker", fontSize = 11.sp) },
                    leadingIcon = {
                        Icon(Icons.Default.FolderShared, contentDescription = null, modifier = Modifier.size(14.dp))
                    }
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // 2. Group Folder
            OutlinedTextField(
                value = viewModel.groupName,
                onValueChange = { viewModel.groupName = it },
                label = { Text("Group Sub-Folder (Optional, e.g. Cosplay_Collection)") },
                placeholder = { Text("Leave empty to organize directly in root") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                leadingIcon = { Icon(Icons.Default.CreateNewFolder, contentDescription = null) }
            )

            Spacer(modifier = Modifier.height(12.dp))

            // 3. Controls & Action Bar (Mobile-first layout)
            val settings by viewModel.settings.collectAsState()
            var showFilterDialog by remember { mutableStateOf(false) }
            var showUndoConfirmDialog by remember { mutableStateOf(false) }

            // Mode & Option Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(
                        checked = viewModel.isSimulate,
                        onCheckedChange = { viewModel.isSimulate = it }
                    )
                    Text(stringResource(R.string.simulate), style = MaterialTheme.typography.bodyMedium)
                }

                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    FilterChip(
                        selected = settings.organizeFoldersMode,
                        onClick = {
                            viewModel.updateSettings(settings.copy(organizeFoldersMode = !settings.organizeFoldersMode))
                        },
                        label = {
                            Text(
                                if (settings.organizeFoldersMode) "📁 Folder Mode" else "📄 File Mode",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        },
                        leadingIcon = {
                            Icon(
                                if (settings.organizeFoldersMode) Icons.Default.Folder else Icons.Default.InsertDriveFile,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    )
                    
                    IconButton(onClick = { showUndoConfirmDialog = true }, enabled = !viewModel.isRunning) {
                        Icon(Icons.Default.Undo, contentDescription = "Undo")
                    }
                    IconButton(onClick = { showFilterDialog = true }, enabled = !viewModel.isRunning) {
                        Icon(Icons.Default.Tune, contentDescription = "Settings / Filters")
                    }
                }
            }

            // Big Run / Stop Action Button for Mobile
            Spacer(modifier = Modifier.height(6.dp))
            if (viewModel.isRunning) {
                Button(
                    onClick = { viewModel.stopOrganization() },
                    modifier = Modifier.fillMaxWidth().height(46.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = ErrorRed),
                    shape = MaterialTheme.shapes.medium
                ) {
                    Icon(Icons.Default.Stop, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Stop Operation", fontWeight = FontWeight.Bold)
                }
            } else {
                Button(
                    onClick = { viewModel.runOrganization() },
                    modifier = Modifier.fillMaxWidth().height(46.dp),
                    enabled = viewModel.selectedFolderUri != null,
                    shape = MaterialTheme.shapes.medium
                ) {
                    Icon(Icons.Default.PlayArrow, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        if (viewModel.isSimulate) "Run Simulation (Preview)" else if (settings.organizeFoldersMode) "Organize Folders" else "Organize Files",
                        fontWeight = FontWeight.Bold
                    )
                }
            }

                    if (showFilterDialog) {
                        AlertDialog(
                            onDismissRequest = { showFilterDialog = false },
                            title = { Text("Filters & Modes") },
                            text = {
                                Column {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Checkbox(
                                            checked = settings.organizeFoldersMode,
                                            onCheckedChange = { viewModel.updateSettings(settings.copy(organizeFoldersMode = it)) }
                                        )
                                        Text("Organize Folders Mode", fontWeight = FontWeight.Bold)
                                    }
                                    Text(
                                        "When enabled, entire folders (like cosplay folders) are moved into category folders based on folder keywords.",
                                        fontSize = 11.sp,
                                        color = MaterialTheme.colorScheme.outline,
                                        modifier = Modifier.padding(start = 12.dp, bottom = 8.dp)
                                    )
                                    Divider()
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Checkbox(
                                            checked = settings.scanSubfolders,
                                            onCheckedChange = { viewModel.updateSettings(settings.copy(scanSubfolders = it)) }
                                        )
                                        Text("Scan Subfolders")
                                    }
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Checkbox(
                                            checked = settings.enableMoveSubfolder,
                                            onCheckedChange = { viewModel.updateSettings(settings.copy(enableMoveSubfolder = it)) }
                                        )
                                        Text("Enable Subfolder Nesting")
                                    }
                                    if (settings.enableMoveSubfolder) {
                                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(start = 16.dp)) {
                                            Checkbox(
                                                checked = settings.disableSuffixOnSubfolder,
                                                onCheckedChange = { viewModel.updateSettings(settings.copy(disableSuffixOnSubfolder = it)) }
                                            )
                                            Text("Disable Date Suffix on Subfolder", fontSize = 13.sp)
                                        }
                                    }
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Checkbox(
                                            checked = settings.skipExactDuplicates,
                                            onCheckedChange = { viewModel.updateSettings(settings.copy(skipExactDuplicates = it)) }
                                        )
                                        Text("Skip Exact Duplicates")
                                    }
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Checkbox(
                                            checked = settings.enableSizeFilter,
                                            onCheckedChange = { viewModel.updateSettings(settings.copy(enableSizeFilter = it)) }
                                        )
                                        Text("Size Filter")
                                    }
                                }
                            },
                            confirmButton = {
                                Button(onClick = { showFilterDialog = false }) { Text("Close") }
                            }
                        )
                    }

            if (showUndoConfirmDialog) {
                AlertDialog(
                    onDismissRequest = { showUndoConfirmDialog = false },
                    title = { Text("Confirm Undo") },
                    text = {
                        Text("Are you sure you want to revert the last operation? Moved files and folders will be restored to their original locations.")
                    },
                    confirmButton = {
                        Button(
                            onClick = {
                                showUndoConfirmDialog = false
                                viewModel.undoLast()
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                        ) {
                            Text("Yes, Undo")
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { showUndoConfirmDialog = false }) {
                            Text("Cancel")
                        }
                    }
                )
            }

            if (showPermissionDialog) {
                AlertDialog(
                    onDismissRequest = { showPermissionDialog = false },
                    title = { Text("All Files Access Required") },
                    text = {
                        Text("Android restricts direct access to the Download folder via system picker. To organize the Download folder directly, please grant 'All Files Access' permission.")
                    },
                    confirmButton = {
                        Button(
                            onClick = {
                                showPermissionDialog = false
                                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                                    try {
                                        val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                                            data = Uri.parse("package:${context.packageName}")
                                        }
                                        context.startActivity(intent)
                                    } catch (_: Exception) {
                                        val intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                                        context.startActivity(intent)
                                    }
                                }
                            }
                        ) {
                            Text("Open Settings")
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { showPermissionDialog = false }) {
                            Text("Cancel")
                        }
                    }
                )
            }

            if (showFolderBrowserDialog) {
                val currentDir = File(currentBrowsePath)
                val subDirs = remember(currentBrowsePath) {
                    try {
                        currentDir.listFiles { f -> f.isDirectory }?.sortedBy { it.name.lowercase() } ?: emptyList()
                    } catch (_: Exception) {
                        emptyList()
                    }
                }

                AlertDialog(
                    onDismissRequest = { showFolderBrowserDialog = false },
                    title = {
                        Column {
                            Text("Select Folder", fontWeight = FontWeight.Bold)
                            Text(
                                text = currentBrowsePath,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary,
                                maxLines = 1
                            )
                        }
                    },
                    text = {
                        Column(modifier = Modifier.fillMaxWidth().heightIn(max = 340.dp)) {
                            // Quick jumps
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                SuggestionChip(
                                    onClick = {
                                        currentBrowsePath = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).absolutePath
                                    },
                                    label = { Text("Download", fontSize = 11.sp) }
                                )
                                SuggestionChip(
                                    onClick = {
                                        currentBrowsePath = Environment.getExternalStorageDirectory().absolutePath
                                    },
                                    label = { Text("Root", fontSize = 11.sp) }
                                )
                            }

                            Divider()

                            LazyColumn(modifier = Modifier.weight(1f).fillMaxWidth()) {
                                val parentFile = currentDir.parentFile
                                val rootPath = Environment.getExternalStorageDirectory().parentFile?.absolutePath ?: ""
                                if (parentFile != null && parentFile.canRead() && currentBrowsePath != rootPath && currentBrowsePath != "/storage/emulated") {
                                    item {
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clickable { currentBrowsePath = parentFile.absolutePath }
                                                .padding(vertical = 8.dp, horizontal = 4.dp),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Icon(Icons.Default.ArrowBack, contentDescription = null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.outline)
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Text(".. (Parent Folder)", fontSize = 13.sp, color = MaterialTheme.colorScheme.outline)
                                        }
                                    }
                                }

                                if (subDirs.isEmpty()) {
                                    item {
                                        Text(
                                            "No subfolders found here.",
                                            modifier = Modifier.padding(16.dp),
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.outline
                                        )
                                    }
                                } else {
                                    items(subDirs) { dir ->
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clickable { currentBrowsePath = dir.absolutePath }
                                                .padding(vertical = 8.dp, horizontal = 4.dp),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Icon(Icons.Default.Folder, contentDescription = null, modifier = Modifier.size(20.dp), tint = MaterialTheme.colorScheme.primary)
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Text(dir.name, style = MaterialTheme.typography.bodyMedium, maxLines = 1)
                                        }
                                    }
                                }
                            }
                        }
                    },
                    confirmButton = {
                        Button(
                            onClick = {
                                showFolderBrowserDialog = false
                                val dir = File(currentBrowsePath)
                                viewModel.onFolderSelected(Uri.fromFile(dir))
                            }
                        ) {
                            Text("Select This Folder")
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { showFolderBrowserDialog = false }) {
                            Text("Cancel")
                        }
                    }
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Progress
            LinearProgressIndicator(
                progress = viewModel.progress,
                modifier = Modifier.fillMaxWidth()
            )
            Text(
                text = viewModel.statusText,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 4.dp)
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Stats Cards
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatsCard(stringResource(R.string.stats_files), viewModel.statsFiles.toString(), Modifier.weight(1f))
                StatsCard(stringResource(R.string.stats_size), "${viewModel.statsSize / 1024} KB", Modifier.weight(1f))
                StatsCard(stringResource(R.string.stats_top), viewModel.statsTopCategory, Modifier.weight(1f))
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Logs Section Header & Filter Tabs
            var logFilterTab by remember { mutableIntStateOf(0) } // 0: All, 1: Moved, 2: Skipped
            
            Row(
                modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Activity Log", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    FilterChip(
                        selected = logFilterTab == 0,
                        onClick = { logFilterTab = 0 },
                        label = { Text("All (${viewModel.logs.size})", fontSize = 11.sp) }
                    )
                    val movedCount = viewModel.logs.count { it.type == LogType.SUCCESS || it.type == LogType.WARNING }
                    FilterChip(
                        selected = logFilterTab == 1,
                        onClick = { logFilterTab = 1 },
                        label = { Text("Moved ($movedCount)", fontSize = 11.sp) }
                    )
                    val skippedCount = viewModel.logs.count { it.type == LogType.INFO }
                    FilterChip(
                        selected = logFilterTab == 2,
                        onClick = { logFilterTab = 2 },
                        label = { Text("Skipped ($skippedCount)", fontSize = 11.sp) }
                    )
                }
            }

            // Logs List
            Surface(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                color = MaterialTheme.colorScheme.surfaceVariant,
                shape = MaterialTheme.shapes.medium
            ) {
                val filteredLogs = remember(viewModel.logs.size, logFilterTab) {
                    when (logFilterTab) {
                        1 -> viewModel.logs.filter { it.type == LogType.SUCCESS || it.type == LogType.WARNING }
                        2 -> viewModel.logs.filter { it.type == LogType.INFO }
                        else -> viewModel.logs.toList()
                    }
                }

                if (filteredLogs.isEmpty()) {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(
                            text = if (viewModel.logs.isEmpty()) "No activity yet. Choose a folder and tap Run." else "No items match this filter.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.outline
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize().padding(horizontal = 8.dp, vertical = 6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        items(filteredLogs) { log ->
                            LogItemView(log, settings.organizeFoldersMode)
                        }
                    }
                }
            }

            // Footer
            Text(
                text = stringResource(R.string.watermark),
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.align(Alignment.CenterHorizontally).padding(top = 8.dp),
                color = MaterialTheme.colorScheme.outline
            )
        }
    }
}

@Composable
fun LogItemView(log: OrganizationEvent.Log, isFolderMode: Boolean) {
    if (log.sourceName != null && log.targetPath != null) {
        // Structured Move / Simulate Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface
            ),
            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
        ) {
            Column(modifier = Modifier.padding(10.dp)) {
                // Row 1: Source Item Name & Status Tag
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(
                        modifier = Modifier.weight(1f),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            if (isFolderMode) Icons.Default.Folder else Icons.Default.InsertDriveFile,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = log.sourceName,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 13.sp,
                            maxLines = 2,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                    
                    Spacer(modifier = Modifier.width(8.dp))
                    
                    // Status Badge
                    Surface(
                        color = if (log.type == LogType.SUCCESS) SuccessGreen.copy(alpha = 0.15f) else WarningOrange.copy(alpha = 0.15f),
                        shape = MaterialTheme.shapes.extraSmall
                    ) {
                        Text(
                            text = if (log.type == LogType.SUCCESS) "MOVED" else "SIMULATE",
                            color = if (log.type == LogType.SUCCESS) SuccessGreen else WarningOrange,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))

                // Row 2: Arrow and Clear Target Category Badge
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Default.ArrowForward,
                        contentDescription = "Target",
                        tint = MaterialTheme.colorScheme.outline,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    
                    Surface(
                        color = MaterialTheme.colorScheme.primaryContainer,
                        shape = MaterialTheme.shapes.small
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                        ) {
                            Icon(
                                Icons.Default.FolderSpecial,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onPrimaryContainer,
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = log.targetPath,
                                color = MaterialTheme.colorScheme.onPrimaryContainer,
                                fontWeight = FontWeight.Bold,
                                fontSize = 12.sp
                            )
                        }
                    }
                }
            }
        }
    } else if (log.sourceName != null && log.type == LogType.INFO) {
        // Skipped / Filtered Item Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.6f)
            )
        ) {
            Row(
                modifier = Modifier.padding(8.dp).fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    Icons.Default.FilterListOff,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.outline,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = log.message,
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    } else {
        // Plain System Message
        Text(
            text = log.message,
            color = getLogColor(log.type),
            fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
            fontSize = 12.sp,
            modifier = Modifier.padding(vertical = 2.dp)
        )
    }
}

@Composable
fun StatsCard(label: String, value: String, modifier: Modifier = Modifier) {
    Card(modifier = modifier) {
        Column(modifier = Modifier.padding(8.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium)
            Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
fun getLogColor(type: LogType): Color {
    return when (type) {
        LogType.SUCCESS -> SuccessGreen
        LogType.WARNING -> WarningOrange
        LogType.ERROR -> ErrorRed
        LogType.INFO -> InfoCyan
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
}
