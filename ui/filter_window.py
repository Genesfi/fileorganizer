import os
import customtkinter as ctk
from tkinter import filedialog
import locales
from ui.dialogs import CategoriesDialog, SubfoldersDialog

class ExceptFoldersDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_except_folders, on_save):
        super().__init__(parent)
        self.title("Except Folders")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "organize_files.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        self.on_save = on_save
        self.folders = list(current_except_folders)
        
        # Label
        self.label = ctk.CTkLabel(self, text="Excluded Folders (will not be scanned):", font=("Arial", 13, "bold"))
        self.label.pack(pady=15, padx=20, anchor="w")
        
        # Frame for List and scrollbar
        self.list_frame = ctk.CTkFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Standard Tkinter Listbox with custom styling to match dark theme
        import tkinter as tk
        self.scrollbar = tk.Scrollbar(self.list_frame)
        self.scrollbar.pack(side="right", fill="y")
        
        # Multiple selection mode allows drag-to-toggle behavior
        self.listbox = tk.Listbox(
            self.list_frame, 
            yscrollcommand=self.scrollbar.set, 
            selectmode="multiple", 
            bg="#2B2B2B", 
            fg="#FFFFFF", 
            selectbackground="#565656", 
            selectforeground="#FFFFFF",
            font=("Arial", 11),
            bd=0,
            highlightthickness=0,
            exportselection=False
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.listbox.yview)
        
        self.refresh_listbox()
        
        # Buttons frame
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=15, padx=20)
        
        self.btn_add = ctk.CTkButton(self.btn_frame, text="Add Folder...", command=self.add_folder, width=110)
        self.btn_add.pack(side="left", padx=5)
        
        self.btn_remove = ctk.CTkButton(self.btn_frame, text="Remove", command=self.remove_folders, width=90, fg_color="#C0392B", hover_color="#962D22")
        self.btn_remove.pack(side="left", padx=5)
        
        self.btn_cancel = ctk.CTkButton(self.btn_frame, text="Cancel", fg_color="gray", hover_color="darkgray", command=self.destroy, width=90)
        self.btn_cancel.pack(side="right", padx=5)
        
        self.btn_ok = ctk.CTkButton(self.btn_frame, text="OK", command=self.done, width=90)
        self.btn_ok.pack(side="right", padx=5)
        
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def refresh_listbox(self):
        self.listbox.delete(0, "end")
        for f in self.folders:
            self.listbox.insert("end", f)
            
    def add_folder(self):
        folder = filedialog.askdirectory(parent=self)
        if folder:
            folder_normalized = os.path.normpath(folder)
            if folder_normalized not in self.folders:
                self.folders.append(folder_normalized)
                self.refresh_listbox()
                
    def remove_folders(self):
        selected_indices = list(self.listbox.curselection())
        for index in sorted(selected_indices, reverse=True):
            self.folders.pop(index)
        self.refresh_listbox()
        
    def done(self):
        self.on_save(self.folders)
        self.destroy()


class FilterWindow(ctk.CTkToplevel):
    def __init__(self, parent, current_config, all_categories, on_save):
        super().__init__(parent)
        self.title(locales.get("filter_window_title"))
        self.geometry("620x520")
        self.transient(parent)
        self.grab_set()
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "organize_files.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        self.config = current_config.copy()
        self.all_categories = all_categories
        self.on_save = on_save
        
        # Top Buttons Row
        self.top_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_btn_frame.pack(fill="x", padx=20, pady=15)
        
        self.btn_categories = ctk.CTkButton(self.top_btn_frame, text=locales.get("categories_button"), command=self.open_categories)
        self.btn_categories.pack(side="left", padx=5, fill="x", expand=True)
        
        self.btn_except = ctk.CTkButton(self.top_btn_frame, text="Except Folders...", command=self.open_except_folders)
        self.btn_except.pack(side="left", padx=5, fill="x", expand=True)
        
        self.btn_subfolders = ctk.CTkButton(self.top_btn_frame, text="Subfolders...", command=self.open_subfolders)
        self.btn_subfolders.pack(side="left", padx=5, fill="x", expand=True)
        
        # Advanced Filters Group
        self.group_frame = ctk.CTkLabel(self, text="") # just a container
        # Let's style a frame with label
        self.adv_frame = ctk.CTkLabel(self, text=locales.get("advanced_filters"), font=("Arial", 12, "bold"))
        self.adv_frame.pack(anchor="w", padx=20)
        
        self.filters_container = ctk.CTkFrame(self)
        self.filters_container.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Size Filters Row
        size_frame = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        size_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(size_frame, text=locales.get("min_size")).pack(side="left", padx=5)
        self.min_size_var = ctk.StringVar(value=str(self.config.get("min_size", 0)))
        self.min_size_entry = ctk.CTkEntry(size_frame, width=80, textvariable=self.min_size_var)
        self.min_size_entry.pack(side="left", padx=5)
        
        self.min_unit_var = ctk.StringVar(value=self.config.get("min_size_unit", "MB"))
        self.min_unit_menu = ctk.CTkOptionMenu(size_frame, values=["B", "KB", "MB", "GB"], variable=self.min_unit_var, width=80)
        self.min_unit_menu.pack(side="left", padx=5)
        
        ctk.CTkLabel(size_frame, text=locales.get("max_size")).pack(side="left", padx=(20, 5))
        self.max_size_var = ctk.StringVar(value=str(self.config.get("max_size", 0)))
        self.max_size_entry = ctk.CTkEntry(size_frame, width=80, textvariable=self.max_size_var)
        self.max_size_entry.pack(side="left", padx=5)
        
        self.max_unit_var = ctk.StringVar(value=self.config.get("max_size_unit", "MB"))
        self.max_unit_menu = ctk.CTkOptionMenu(size_frame, values=["B", "KB", "MB", "GB"], variable=self.max_unit_var, width=80)
        self.max_unit_menu.pack(side="left", padx=5)
        
        # Date Filters Grid (using Frame)
        date_time_frame = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        date_time_frame.pack(fill="x", padx=15, pady=5)
        
        # Row 1
        ctk.CTkLabel(date_time_frame, text=locales.get("date_from"), width=90, anchor="w").grid(row=0, column=0, padx=5, pady=5)
        self.date_from_entry = ctk.CTkEntry(date_time_frame, placeholder_text="YYYY-MM-DD", width=140)
        self.date_from_entry.insert(0, self.config.get("date_from", ""))
        self.date_from_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(date_time_frame, text=locales.get("time_from"), width=90, anchor="w").grid(row=0, column=2, padx=(20, 5), pady=5)
        self.time_from_entry = ctk.CTkEntry(date_time_frame, placeholder_text="HH:MM", width=100)
        self.time_from_entry.insert(0, self.config.get("time_from", "00:00"))
        self.time_from_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Row 2
        ctk.CTkLabel(date_time_frame, text=locales.get("date_to"), width=90, anchor="w").grid(row=1, column=0, padx=5, pady=5)
        self.date_to_entry = ctk.CTkEntry(date_time_frame, placeholder_text="YYYY-MM-DD", width=140)
        self.date_to_entry.insert(0, self.config.get("date_to", ""))
        self.date_to_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(date_time_frame, text=locales.get("time_to"), width=90, anchor="w").grid(row=1, column=2, padx=(20, 5), pady=5)
        self.time_to_entry = ctk.CTkEntry(date_time_frame, placeholder_text="HH:MM", width=100)
        self.time_to_entry.insert(0, self.config.get("time_to", "23:59"))
        self.time_to_entry.grid(row=1, column=3, padx=5, pady=5)
        
        # Blacklist Text Area
        blacklist_label_frame = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        blacklist_label_frame.pack(fill="x", padx=15, pady=(5, 0))
        ctk.CTkLabel(blacklist_label_frame, text=locales.get("blacklist")).pack(side="left")
        
        self.blacklist_text = ctk.CTkTextbox(self.filters_container, height=70)
        self.blacklist_text.pack(fill="x", padx=15, pady=5)
        self.blacklist_text.insert("1.0", self.config.get("blacklist", ""))
        
        # Bottom Checkboxes Grid
        cb_frame = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        cb_frame.pack(fill="x", padx=15, pady=10)
        
        self.scan_subfolders_var = ctk.BooleanVar(value=self.config.get("scan_subfolders", False))
        self.cb_scan = ctk.CTkCheckBox(cb_frame, text=locales.get("scan_subfolders"), variable=self.scan_subfolders_var)
        self.cb_scan.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.enable_datetime_var = ctk.BooleanVar(value=self.config.get("enable_datetime_filter", False))
        self.cb_date = ctk.CTkCheckBox(cb_frame, text=locales.get("enable_datetime_filter"), variable=self.enable_datetime_var)
        self.cb_date.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        self.enable_size_var = ctk.BooleanVar(value=self.config.get("enable_size_filter", False))
        self.cb_size = ctk.CTkCheckBox(cb_frame, text=locales.get("enable_size_filter"), variable=self.enable_size_var)
        self.cb_size.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.enable_move_subfolder_var = ctk.BooleanVar(value=self.config.get("enable_move_subfolder", False))
        self.cb_sub = ctk.CTkCheckBox(cb_frame, text="Move into sub-folder", variable=self.enable_move_subfolder_var)
        self.cb_sub.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # Apply Button
        self.btn_apply = ctk.CTkButton(self, text=locales.get("apply_and_close"), command=self.apply, height=35)
        self.btn_apply.pack(pady=15)
        
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def open_categories(self):
        cats = list(self.all_categories)
        if "Others" not in cats:
            cats.append("Others")
        CategoriesDialog(
            self,
            cats,
            self.config.get("included_categories", []),
            self.save_categories
        )
        
    def save_categories(self, selected):
        self.config["included_categories"] = selected
        
    def open_except_folders(self):
        ExceptFoldersDialog(
            self,
            self.config.get("except_folders", []),
            self.save_except_folders
        )
        
    def save_except_folders(self, folders):
        self.config["except_folders"] = folders
        
    def open_subfolders(self):
        SubfoldersDialog(
            self,
            self.all_categories,
            self.config.get("subfolders", {}),
            self.enable_move_subfolder_var.get(),
            self.config.get("disable_suffix_on_subfolder", False),
            self.save_subfolders
        )
        
    def save_subfolders(self, subfolders_data, any_enabled, disable_suffix):
        self.config["subfolders"] = subfolders_data
        self.config["disable_suffix_on_subfolder"] = disable_suffix
        if any_enabled:
            self.enable_move_subfolder_var.set(True)
            
    def apply(self):
        # Update config fields from widgets
        try:
            self.config["min_size"] = int(self.min_size_var.get())
        except ValueError:
            self.config["min_size"] = 0
            
        try:
            self.config["max_size"] = int(self.max_size_var.get())
        except ValueError:
            self.config["max_size"] = 0
            
        self.config["min_size_unit"] = self.min_unit_var.get()
        self.config["max_size_unit"] = self.max_unit_var.get()
        
        self.config["date_from"] = self.date_from_entry.get().strip()
        self.config["time_from"] = self.time_from_entry.get().strip()
        self.config["date_to"] = self.date_to_entry.get().strip()
        self.config["time_to"] = self.time_to_entry.get().strip()
        
        self.config["blacklist"] = self.blacklist_text.get("1.0", "end-1c").strip()
        
        self.config["scan_subfolders"] = self.scan_subfolders_var.get()
        self.config["enable_datetime_filter"] = self.enable_datetime_var.get()
        self.config["enable_size_filter"] = self.enable_size_var.get()
        self.config["enable_move_subfolder"] = self.enable_move_subfolder_var.get()
        
        self.on_save(self.config)
        self.destroy()
