package com.example.fileorganizer.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.fileorganizer.domain.FileCategory
import com.example.fileorganizer.ui.theme.ErrorRed
import com.example.fileorganizer.ui.theme.SuccessGreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel = hiltViewModel(),
    onBack: () -> Unit
) {
    val categories by viewModel.categories.collectAsState()
    val settings by viewModel.settings.collectAsState()

    var searchQuery by remember { mutableStateOf("") }
    var selectedTab by remember { mutableIntStateOf(0) } // 0: Categories, 1: Global Options
    var showEditSheet by remember { mutableStateOf(false) }
    var isCreatingNew by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings & Categories") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        },
        floatingActionButton = {
            if (selectedTab == 0) {
                ExtendedFloatingActionButton(
                    onClick = {
                        isCreatingNew = true
                        viewModel.prepareNewCategory()
                        showEditSheet = true
                    },
                    icon = { Icon(Icons.Default.Add, contentDescription = null) },
                    text = { Text("Add Category") }
                )
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
        ) {
            // Navigation Tabs (Categories vs General Options)
            TabRow(selectedTabIndex = selectedTab) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = { Text("Categories (${categories.size})") }
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = { Text("Templates & Options") }
                )
            }

            if (selectedTab == 0) {
                // CATEGORIES TAB (Mobile Friendly List with Search)
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                ) {
                    // Search Bar
                    OutlinedTextField(
                        value = searchQuery,
                        onValueChange = { searchQuery = it },
                        placeholder = { Text("Search cosplayer or category...") },
                        leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                        trailingIcon = {
                            if (searchQuery.isNotEmpty()) {
                                IconButton(onClick = { searchQuery = "" }) {
                                    Icon(Icons.Default.Clear, contentDescription = "Clear")
                                }
                            }
                        },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    val filteredCategories = remember(categories, searchQuery) {
                        if (searchQuery.isBlank()) categories
                        else categories.filter { cat ->
                            cat.name.contains(searchQuery, ignoreCase = true) ||
                            cat.keywords.any { it.contains(searchQuery, ignoreCase = true) }
                        }
                    }

                    if (filteredCategories.isEmpty()) {
                        Box(
                            modifier = Modifier.weight(1f).fillMaxWidth(),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                if (searchQuery.isBlank()) "No categories configured. Tap + Add Category." else "No categories match '$searchQuery'",
                                color = MaterialTheme.colorScheme.outline,
                                fontSize = 14.sp
                            )
                        }
                    } else {
                        LazyColumn(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            contentPadding = PaddingValues(bottom = 80.dp, top = 4.dp)
                        ) {
                            items(filteredCategories, key = { it.name }) { cat ->
                                CategoryCardItem(
                                    category = cat,
                                    onEdit = {
                                        isCreatingNew = false
                                        viewModel.onCategorySelected(cat)
                                        showEditSheet = true
                                    },
                                    onDelete = {
                                        viewModel.activeCategory = cat
                                        viewModel.deleteCategory()
                                    },
                                    onToggleKeyword = {
                                        viewModel.toggleCategoryKeywords(cat.name)
                                    },
                                    onToggleRegex = {
                                        viewModel.toggleCategoryRegex(cat.name)
                                    }
                                )
                            }
                        }
                    }
                }
            } else {
                // GENERAL OPTIONS & TEMPLATES TAB
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // 1. Template Management Card
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Active Template", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text("Switch presets or save custom category rules", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
                            Spacer(modifier = Modifier.height(12.dp))

                            var expanded by remember { mutableStateOf(false) }
                            var showSaveDialog by remember { mutableStateOf(false) }
                            var newTemplateName by remember { mutableStateOf("") }

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Box(modifier = Modifier.weight(1f)) {
                                    OutlinedButton(
                                        onClick = { expanded = true },
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text(viewModel.selectedTemplate)
                                        Spacer(modifier = Modifier.weight(1f))
                                        Icon(Icons.Default.ArrowDropDown, null)
                                    }
                                    DropdownMenu(
                                        expanded = expanded,
                                        onDismissRequest = { expanded = false }
                                    ) {
                                        viewModel.templates.forEach { tpl ->
                                            DropdownMenuItem(
                                                text = { Text(tpl) },
                                                onClick = {
                                                    viewModel.loadTemplate(tpl)
                                                    expanded = false
                                                }
                                            )
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.width(8.dp))
                                IconButton(onClick = { showSaveDialog = true }) {
                                    Icon(Icons.Default.Save, contentDescription = "Save Template", tint = MaterialTheme.colorScheme.primary)
                                }
                                IconButton(
                                    onClick = { viewModel.deleteTemplate(viewModel.selectedTemplate) },
                                    enabled = viewModel.selectedTemplate != "None"
                                ) {
                                    Icon(Icons.Default.Delete, contentDescription = "Delete Template", tint = ErrorRed)
                                }
                            }

                            if (showSaveDialog) {
                                AlertDialog(
                                    onDismissRequest = { showSaveDialog = false },
                                    title = { Text("Save Template As") },
                                    text = {
                                        OutlinedTextField(
                                            value = newTemplateName,
                                            onValueChange = { newTemplateName = it },
                                            label = { Text("Template Name") },
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                    },
                                    confirmButton = {
                                        Button(onClick = {
                                            if (newTemplateName.isNotBlank()) {
                                                viewModel.saveTemplate(newTemplateName.trim())
                                                showSaveDialog = false
                                            }
                                        }) { Text("Save") }
                                    },
                                    dismissButton = {
                                        TextButton(onClick = { showSaveDialog = false }) { Text("Cancel") }
                                    }
                                )
                            }
                        }
                    }

                    // 2. Output Naming Card
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Output Folder Naming", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(8.dp))

                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Checkbox(
                                    checked = settings.enableOutputDate,
                                    onCheckedChange = { viewModel.updateSettings(settings.copy(enableOutputDate = it)) }
                                )
                                Text("Append Date to Category Folder")
                            }

                            if (settings.enableOutputDate) {
                                OutlinedTextField(
                                    value = settings.outputDate,
                                    onValueChange = { viewModel.updateSettings(settings.copy(outputDate = it)) },
                                    label = { Text("Suffix Date (e.g. 2026-09)") },
                                    modifier = Modifier.fillMaxWidth().padding(top = 4.dp)
                                )
                            }

                            Spacer(modifier = Modifier.height(8.dp))
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Checkbox(
                                    checked = settings.skipExactDuplicates,
                                    onCheckedChange = { viewModel.updateSettings(settings.copy(skipExactDuplicates = it)) }
                                )
                                Text("Skip Exact Duplicates (MD5)")
                            }
                        }
                    }

                    // 3. Global Regex Card
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Filename Regex Filter", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text("Applied to categories with Regex toggle enabled", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
                            Spacer(modifier = Modifier.height(8.dp))

                            OutlinedTextField(
                                value = viewModel.editRegex,
                                onValueChange = { viewModel.editRegex = it },
                                label = { Text("Pattern (e.g. .*cos.*)") },
                                modifier = Modifier.fillMaxWidth()
                            )

                            Spacer(modifier = Modifier.height(8.dp))
                            Button(
                                onClick = { viewModel.saveRegex() },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Apply Regex Setting")
                            }
                        }
                    }
                }
            }
        }
    }

    // Full Mobile Category Editor (ModalBottomSheet)
    if (showEditSheet) {
        ModalBottomSheet(
            onDismissRequest = { showEditSheet = false }
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp)
                    .padding(bottom = 32.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text(
                    text = if (isCreatingNew) "Add New Category" else "Edit Category",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )

                Spacer(modifier = Modifier.height(16.dp))

                OutlinedTextField(
                    value = viewModel.editFolderName,
                    onValueChange = { viewModel.editFolderName = it },
                    label = { Text("Category / Folder Name *") },
                    placeholder = { Text("e.g. Natsuko (Natsuko 夏夏子)") },
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = viewModel.editKeywords,
                    onValueChange = { viewModel.editKeywords = it },
                    label = { Text("Keywords (comma separated)") },
                    placeholder = { Text("e.g. Natsuko, 夏夏子") },
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = viewModel.editExtensions,
                    onValueChange = { viewModel.editExtensions = it },
                    label = { Text("Extensions (comma separated)") },
                    placeholder = { Text("e.g. zip, rar, 7z, jpg, mp4") },
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = viewModel.editSubfolder,
                    onValueChange = { viewModel.editSubfolder = it },
                    label = { Text("Subfolder Pattern (optional)") },
                    placeholder = { Text("e.g. Costumes or extension") },
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(20.dp))

                Button(
                    onClick = {
                        if (viewModel.editFolderName.isNotBlank()) {
                            if (isCreatingNew) {
                                viewModel.addCategory()
                            } else {
                                viewModel.updateCategory()
                            }
                            showEditSheet = false
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                    shape = MaterialTheme.shapes.medium
                ) {
                    Icon(if (isCreatingNew) Icons.Default.Add else Icons.Default.Check, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(if (isCreatingNew) "Create Category" else "Save Changes")
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CategoryCardItem(
    category: FileCategory,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    onToggleKeyword: () -> Unit,
    onToggleRegex: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    Icons.Default.Folder,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(22.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = category.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f)
                )

                IconButton(onClick = onEdit) {
                    Icon(Icons.Default.Edit, contentDescription = "Edit", tint = MaterialTheme.colorScheme.primary)
                }
                IconButton(onClick = onDelete) {
                    Icon(Icons.Default.Delete, contentDescription = "Delete", tint = ErrorRed)
                }
            }

            if (category.keywords.isNotEmpty()) {
                Spacer(modifier = Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Keywords: ", fontSize = 12.sp, color = MaterialTheme.colorScheme.outline, fontWeight = FontWeight.SemiBold)
                    Text(
                        text = category.keywords.joinToString(", "),
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2
                    )
                }
            }

            if (category.extensions.isNotEmpty()) {
                Spacer(modifier = Modifier.height(2.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Ext: ", fontSize = 12.sp, color = MaterialTheme.colorScheme.outline, fontWeight = FontWeight.SemiBold)
                    Text(
                        text = category.extensions.take(8).joinToString(", ") + if (category.extensions.size > 8) "..." else "",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            if (!category.subfolderPattern.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(2.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Subfolder: ", fontSize = 12.sp, color = MaterialTheme.colorScheme.outline, fontWeight = FontWeight.SemiBold)
                    Text(category.subfolderPattern, fontSize = 12.sp, color = MaterialTheme.colorScheme.primary)
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Toggles Row (Keyword Active & Regex Active Chips)
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChip(
                    selected = category.isKeywordMatchingEnabled,
                    onClick = onToggleKeyword,
                    label = { Text("Keyword Match: ${if (category.isKeywordMatchingEnabled) "ON" else "OFF"}", fontSize = 11.sp) },
                    leadingIcon = {
                        Icon(
                            if (category.isKeywordMatchingEnabled) Icons.Default.Check else Icons.Default.Close,
                            contentDescription = null,
                            modifier = Modifier.size(14.dp)
                        )
                    }
                )

                FilterChip(
                    selected = category.isRegexEnabled,
                    onClick = onToggleRegex,
                    label = { Text("Regex: ${if (category.isRegexEnabled) "ON" else "OFF"}", fontSize = 11.sp) },
                    leadingIcon = {
                        Icon(
                            if (category.isRegexEnabled) Icons.Default.Check else Icons.Default.Close,
                            contentDescription = null,
                            modifier = Modifier.size(14.dp)
                        )
                    }
                )
            }
        }
    }
}
