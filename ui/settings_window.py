import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
import locales
import config
import re

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_save_callback):
        super().__init__(parent)
        self.title(locales.get("settings"))
        self.geometry("520x760")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.save_settings)
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "organize_files.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        self.on_save_callback = on_save_callback
        self.config_data = config.load_config()
        self.active_category = None
        
        self.create_widgets()
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def create_widgets(self):
        # 1. Output Folder Naming
        output_frame = ctk.CTkFrame(self)
        output_frame.pack(fill="x", padx=20, pady=10)
        
        lbl_output = ctk.CTkLabel(output_frame, text=locales.get("output_folder_naming"), font=("Arial", 12, "bold"))
        lbl_output.pack(anchor="w", padx=10, pady=(5, 0))
        
        naming_row = ctk.CTkFrame(output_frame, fg_color="transparent")
        naming_row.pack(fill="x", padx=10, pady=5)
        
        self.append_date_var = ctk.BooleanVar(value=self.config_data.get("enable_output_date", False))
        self.cb_append_date = ctk.CTkCheckBox(naming_row, text=locales.get("append_date"), variable=self.append_date_var)
        self.cb_append_date.pack(side="left", padx=5)
        
        import datetime
        curr_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.date_entry = ctk.CTkEntry(naming_row, width=120)
        self.date_entry.insert(0, self.config_data.get("output_date") or curr_date)
        self.date_entry.pack(side="right", padx=5)
        
        # 2. Language selection
        lang_frame = ctk.CTkFrame(self)
        lang_frame.pack(fill="x", padx=20, pady=5)
        
        lbl_lang = ctk.CTkLabel(lang_frame, text=locales.get("language"), font=("Arial", 12, "bold"))
        lbl_lang.pack(anchor="w", padx=10, pady=(5, 0))
        
        lang_row = ctk.CTkFrame(lang_frame, fg_color="transparent")
        lang_row.pack(fill="x", padx=10, pady=5)
        
        self.lang_var = ctk.StringVar(value=self.config_data.get("language", "English"))
        self.lang_menu = ctk.CTkOptionMenu(lang_row, values=["English", "Indonesia"], variable=self.lang_var, command=self.change_language)
        self.lang_menu.pack(side="left", padx=5)
        
        # 3. Templates Section
        template_frame = ctk.CTkFrame(self)
        template_frame.pack(fill="x", padx=20, pady=5)
        
        lbl_tpl = ctk.CTkLabel(template_frame, text=locales.get("templates"), font=("Arial", 12, "bold"))
        lbl_tpl.pack(anchor="w", padx=10, pady=(5, 0))
        
        tpl_row = ctk.CTkFrame(template_frame, fg_color="transparent")
        tpl_row.pack(fill="x", padx=10, pady=5)
        
        self.tpl_list = config.get_templates()
        current_tpl = self.config_data.get("template", "")
        if current_tpl not in self.tpl_list and current_tpl:
            self.tpl_list.append(current_tpl)
            
        self.tpl_var = ctk.StringVar(value=current_tpl or (self.tpl_list[0] if self.tpl_list else ""))
        self.tpl_menu = ctk.CTkOptionMenu(tpl_row, values=self.tpl_list or ["None"], variable=self.tpl_var, command=self.load_template_clicked, width=150)
        self.tpl_menu.pack(side="left", padx=5)
        
        self.btn_save_as = ctk.CTkButton(tpl_row, text=locales.get("save_as"), width=80, command=self.save_template_as)
        self.btn_save_as.pack(side="left", padx=3)
        
        self.btn_delete_tpl = ctk.CTkButton(tpl_row, text=locales.get("delete"), fg_color="#C0392B", hover_color="#962D22", width=70, command=self.delete_template_clicked)
        self.btn_delete_tpl.pack(side="left", padx=3)
        
        self.btn_open_folder = ctk.CTkButton(tpl_row, text=locales.get("open_folder"), width=100, command=self.open_templates_folder)
        self.btn_open_folder.pack(side="left", padx=3)
        
        # 4. Tab Control for Regex vs Keyword classification settings
        self.tab_control = ctk.CTkTabview(self, height=460)
        self.tab_control.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tab_regex = self.tab_control.add("Regex")
        self.tab_keyword = self.tab_control.add("Keyword")
        
        self.setup_regex_tab()
        self.setup_keyword_tab()
        
        # Select first category by default if available
        if self.regex_listbox.size() > 0:
            self.regex_listbox.selection_set(0)
            self.on_regex_listbox_select(None)


    def change_language(self, val):
        messagebox.showinfo(locales.get("info"), locales.get("restart_to_apply"), parent=self)

    def setup_regex_tab(self):
        # Folder Types Listbox frame
        lbl = ctk.CTkLabel(self.tab_regex, text=locales.get("folder_types_title"), font=("Arial", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=2)
        
        list_frame = ctk.CTkFrame(self.tab_regex)
        list_frame.pack(fill="both", expand=True, padx=10, pady=2)
        
        import tkinter as tk
        self.regex_scrollbar = tk.Scrollbar(list_frame)
        self.regex_scrollbar.pack(side="right", fill="y")
        
        self.regex_listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=self.regex_scrollbar.set, 
            bg="#2B2B2B", 
            fg="#FFFFFF", 
            selectbackground="#565656", 
            selectforeground="#FFFFFF",
            font=("Arial", 10),
            bd=0,
            highlightthickness=0,
            exportselection=False
        )
        self.regex_listbox.pack(side="left", fill="both", expand=True)
        self.regex_scrollbar.config(command=self.regex_listbox.yview)
        
        self.regex_listbox.bind("<<ListboxSelect>>", self.on_regex_listbox_select)
        self.regex_listbox.bind("<Double-Button-1>", self.on_regex_listbox_double_click)
        
        self.refresh_regex_listbox()
        
        # Regex Filename Filter section
        regex_filter_frame = ctk.CTkFrame(self.tab_regex, fg_color="transparent")
        regex_filter_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(regex_filter_frame, text="Filename Regex:").pack(side="left", padx=5)
        self.regex_entry = ctk.CTkEntry(regex_filter_frame)
        self.regex_entry.insert(0, self.config_data.get("filename_regex", ".*"))
        self.regex_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        regex_actions_row = ctk.CTkFrame(self.tab_regex, fg_color="transparent")
        regex_actions_row.pack(fill="x", padx=10, pady=2)
        
        self.btn_apply_regex = ctk.CTkButton(regex_actions_row, text=locales.get("apply_regex"), width=90, command=self.apply_regex_clicked)
        self.btn_apply_regex.pack(side="left", padx=3)
        
        self.btn_load_regex = ctk.CTkButton(regex_actions_row, text=locales.get("load_from_file"), width=120, command=self.load_regex_file)
        self.btn_load_regex.pack(side="left", padx=3)
        
        self.btn_reset_regex = ctk.CTkButton(regex_actions_row, text="Reset Regex", width=90, command=self.reset_regex_clicked)
        self.btn_reset_regex.pack(side="left", padx=3)
        
        # Bottom CRUD editor for categories
        crud_frame = ctk.CTkFrame(self.tab_regex, fg_color="transparent")
        crud_frame.pack(fill="x", padx=10, pady=5)
        
        # Folder Name
        row1 = ctk.CTkFrame(crud_frame, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        ctk.CTkLabel(row1, text="Folder Name:", width=100, anchor="w").pack(side="left")
        self.folder_name_entry = ctk.CTkEntry(row1)
        self.folder_name_entry.pack(side="right", fill="x", expand=True)
        
        # Extensions
        row2 = ctk.CTkFrame(crud_frame, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        ctk.CTkLabel(row2, text="Extensions:", width=100, anchor="w").pack(side="left")
        self.extensions_entry = ctk.CTkEntry(row2)
        self.extensions_entry.pack(side="right", fill="x", expand=True)
        
        # CRUD buttons
        row3 = ctk.CTkFrame(crud_frame, fg_color="transparent")
        row3.pack(fill="x", pady=4)
        
        self.btn_add_cat = ctk.CTkButton(row3, text="Add New", command=self.add_category, width=90)
        self.btn_add_cat.pack(side="right", padx=3)
        
        self.btn_update_cat = ctk.CTkButton(row3, text="Update", command=self.update_category, width=90)
        self.btn_update_cat.pack(side="right", padx=3)
        
        self.btn_delete_cat = ctk.CTkButton(row3, text="Delete", fg_color="#C0392B", hover_color="#962D22", command=self.delete_category, width=90)
        self.btn_delete_cat.pack(side="right", padx=3)

    def refresh_regex_listbox(self):
        self.regex_listbox.delete(0, "end")
        types = self.config_data.get("types", {})
        regex_apply = self.config_data.get("regex_apply_types", {})
        for cat, exts in types.items():
            flag = "[x]" if regex_apply.get(cat, False) else "[ ]"
            ext_str = ", ".join(exts)
            self.regex_listbox.insert("end", f"{flag} {cat}: {ext_str}")

    def on_regex_listbox_select(self, event):
        idx = self.regex_listbox.curselection()
        if not idx:
            return
        # Parse the selected line to extract category name and extensions
        line = self.regex_listbox.get(idx[0])
        # Format: "[ ] Category: .mp4, .mov"
        match = re.match(r"^\[.\]\s*([^:]+):\s*(.*)$", line)
        if match:
            cat_name = match.group(1).strip()
            self.active_category = cat_name
            ext_str = match.group(2).strip()
            self.folder_name_entry.delete(0, "end")
            self.folder_name_entry.insert(0, cat_name)
            self.extensions_entry.delete(0, "end")
            self.extensions_entry.insert(0, ext_str)
            
            # Select in keyword listbox
            self.sync_listbox_selections(cat_name, source="regex")
            
            # Update keywords
            if hasattr(self, "keywords_entry"):
                kws = self.config_data.get("keywords", {}).get(cat_name, [])
                self.keywords_entry.delete(0, "end")
                self.keywords_entry.insert(0, ", ".join(kws))

    def on_regex_listbox_double_click(self, event):
        idx = self.regex_listbox.curselection()
        if not idx:
            return
        line = self.regex_listbox.get(idx[0])
        match = re.match(r"^\[.\]\s*([^:]+):", line)
        if match:
            cat_name = match.group(1).strip()
            apply_types = self.config_data.setdefault("regex_apply_types", {})
            apply_types[cat_name] = not apply_types.get(cat_name, False)
            self.refresh_regex_listbox()
            self.regex_listbox.selection_set(idx[0])

    def setup_keyword_tab(self):
        lbl = ctk.CTkLabel(self.tab_keyword, text="Folder Types (double-click to toggle [keyword])", font=("Arial", 11, "bold"))
        lbl.pack(anchor="w", padx=10, pady=2)
        
        list_frame = ctk.CTkFrame(self.tab_keyword)
        list_frame.pack(fill="both", expand=True, padx=10, pady=2)
        
        import tkinter as tk
        self.kw_scrollbar = tk.Scrollbar(list_frame)
        self.kw_scrollbar.pack(side="right", fill="y")
        
        self.kw_listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=self.kw_scrollbar.set, 
            bg="#2B2B2B", 
            fg="#FFFFFF", 
            selectbackground="#565656", 
            selectforeground="#FFFFFF",
            font=("Arial", 10),
            bd=0,
            highlightthickness=0,
            exportselection=False
        )
        self.kw_listbox.pack(side="left", fill="both", expand=True)
        self.kw_scrollbar.config(command=self.kw_listbox.yview)
        
        self.kw_listbox.bind("<<ListboxSelect>>", self.on_kw_listbox_select)
        self.kw_listbox.bind("<Double-Button-1>", self.on_kw_listbox_double_click)
        self.refresh_kw_listbox()
        
        # Keywords Filter section
        kw_filter_frame = ctk.CTkFrame(self.tab_keyword, fg_color="transparent")
        kw_filter_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(kw_filter_frame, text="Keywords (comma-separated):").pack(side="left", padx=5)
        self.keywords_entry = ctk.CTkEntry(kw_filter_frame)
        self.keywords_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.keywords_entry.bind("<KeyRelease>", self.on_keywords_key_release)

    def refresh_kw_listbox(self):
        self.kw_listbox.delete(0, "end")
        types = self.config_data.get("types", {})
        kw_apply = self.config_data.get("keyword_apply_types", {})
        for cat, exts in types.items():
            flag = "[x]" if kw_apply.get(cat, False) else "[ ]"
            ext_str = ", ".join(exts)
            self.kw_listbox.insert("end", f"{flag} {cat}: {ext_str}")

    def sync_listbox_selections(self, cat_name, source):
        if source == "regex":
            self.kw_listbox.selection_clear(0, "end")
            for i in range(self.kw_listbox.size()):
                line = self.kw_listbox.get(i)
                match = re.match(r"^\[.\]\s*([^:]+):", line)
                if match and match.group(1).strip() == cat_name:
                    self.kw_listbox.selection_set(i)
                    self.kw_listbox.see(i)
                    break
        else:
            self.regex_listbox.selection_clear(0, "end")
            for i in range(self.regex_listbox.size()):
                line = self.regex_listbox.get(i)
                match = re.match(r"^\[.\]\s*([^:]+):", line)
                if match and match.group(1).strip() == cat_name:
                    self.regex_listbox.selection_set(i)
                    self.regex_listbox.see(i)
                    break

    def on_kw_listbox_select(self, event):
        idx = self.kw_listbox.curselection()
        if not idx:
            return
        line = self.kw_listbox.get(idx[0])
        match = re.match(r"^\[.\]\s*([^:]+):\s*(.*)$", line)
        if match:
            cat_name = match.group(1).strip()
            self.active_category = cat_name
            ext_str = match.group(2).strip()
            self.folder_name_entry.delete(0, "end")
            self.folder_name_entry.insert(0, cat_name)
            self.extensions_entry.delete(0, "end")
            self.extensions_entry.insert(0, ext_str)
            
            self.sync_listbox_selections(cat_name, source="kw")
            
            kws = self.config_data.get("keywords", {}).get(cat_name, [])
            self.keywords_entry.delete(0, "end")
            self.keywords_entry.insert(0, ", ".join(kws))

    def on_keywords_key_release(self, event):
        if self.active_category:
            kw_str = self.keywords_entry.get().strip()
            kws = [k.strip() for k in kw_str.split(",") if k.strip()]
            self.config_data.setdefault("keywords", {})[self.active_category] = kws

    def get_selected_category(self):
        idx = self.regex_listbox.curselection()
        if not idx:
            idx = self.kw_listbox.curselection()
            if not idx:
                return None
            line = self.kw_listbox.get(idx[0])
        else:
            line = self.regex_listbox.get(idx[0])
            
        match = re.match(r"^\[.\]\s*([^:]+):", line)
        if match:
            return match.group(1).strip()
        return None

    def on_kw_listbox_double_click(self, event):
        idx = self.kw_listbox.curselection()
        if not idx:
            return
        line = self.kw_listbox.get(idx[0])
        match = re.match(r"^\[.\]\s*([^:]+):", line)
        if match:
            cat_name = match.group(1).strip()
            apply_types = self.config_data.setdefault("keyword_apply_types", {})
            apply_types[cat_name] = not apply_types.get(cat_name, False)
            self.refresh_kw_listbox()
            self.kw_listbox.selection_set(idx[0])

    def add_category(self):
        cat_name = self.folder_name_entry.get().strip()
        ext_str = self.extensions_entry.get().strip()
        if not cat_name:
            messagebox.showwarning(locales.get("message_folder_name_empty_title"), locales.get("message_folder_name_empty"), parent=self)
            return
            
        exts = [e.strip() for e in ext_str.split(",") if e.strip()]
        exts = [e if e.startswith(".") else f".{e}" for e in exts]
        
        self.config_data.setdefault("types", {})[cat_name] = exts
        self.config_data.setdefault("regex_apply_types", {})[cat_name] = False
        self.config_data.setdefault("keyword_apply_types", {})[cat_name] = False
        
        if hasattr(self, "keywords_entry"):
            kw_str = self.keywords_entry.get().strip()
            kws = [k.strip() for k in kw_str.split(",") if k.strip()]
            self.config_data.setdefault("keywords", {})[cat_name] = kws
            
        self.active_category = cat_name
        self.refresh_regex_listbox()
        self.refresh_kw_listbox()

    def update_category(self):
        idx = self.regex_listbox.curselection()
        if not idx:
            idx = self.kw_listbox.curselection()
            if not idx:
                return
            old_line = self.kw_listbox.get(idx[0])
        else:
            old_line = self.regex_listbox.get(idx[0])
            
        old_match = re.match(r"^\[.\]\s*([^:]+):", old_line)
        if not old_match:
            return
        old_cat_name = old_match.group(1).strip()
        
        cat_name = self.folder_name_entry.get().strip()
        ext_str = self.extensions_entry.get().strip()
        if not cat_name:
            messagebox.showwarning(locales.get("message_folder_name_empty_title"), locales.get("message_folder_name_empty"), parent=self)
            return
            
        exts = [e.strip() for e in ext_str.split(",") if e.strip()]
        exts = [e if e.startswith(".") else f".{e}" for e in exts]
        
        types = self.config_data.setdefault("types", {})
        if old_cat_name in types:
            del types[old_cat_name]
        types[cat_name] = exts
        self.active_category = cat_name
        
        regex_flags = self.config_data.setdefault("regex_apply_types", {})
        old_regex_flag = regex_flags.pop(old_cat_name, False)
        regex_flags[cat_name] = old_regex_flag
        
        kw_flags = self.config_data.setdefault("keyword_apply_types", {})
        old_kw_flag = kw_flags.pop(old_cat_name, False)
        kw_flags[cat_name] = old_kw_flag
        
        subfolders = self.config_data.setdefault("subfolders", {})
        if old_cat_name in subfolders:
            subfolders[cat_name] = subfolders.pop(old_cat_name)
            
        if hasattr(self, "keywords_entry"):
            kw_str = self.keywords_entry.get().strip()
            kws = [k.strip() for k in kw_str.split(",") if k.strip()]
            keywords_dict = self.config_data.setdefault("keywords", {})
            if old_cat_name in keywords_dict:
                del keywords_dict[old_cat_name]
            keywords_dict[cat_name] = kws
            
        self.refresh_regex_listbox()
        self.refresh_kw_listbox()

    def delete_category(self):
        idx = self.regex_listbox.curselection()
        if not idx:
            idx = self.kw_listbox.curselection()
            if not idx:
                return
            line = self.kw_listbox.get(idx[0])
        else:
            line = self.regex_listbox.get(idx[0])
            
        match = re.match(r"^\[.\]\s*([^:]+):", line)
        if match:
            cat_name = match.group(1).strip()
            
            types = self.config_data.setdefault("types", {})
            if cat_name in types: del types[cat_name]
            
            regex_flags = self.config_data.setdefault("regex_apply_types", {})
            if cat_name in regex_flags: del regex_flags[cat_name]
            
            kw_flags = self.config_data.setdefault("keyword_apply_types", {})
            if cat_name in kw_flags: del kw_flags[cat_name]
            
            subfolders = self.config_data.setdefault("subfolders", {})
            if cat_name in subfolders: del subfolders[cat_name]
            
            keywords_dict = self.config_data.setdefault("keywords", {})
            if cat_name in keywords_dict: del keywords_dict[cat_name]
            
            self.active_category = None
            self.refresh_regex_listbox()
            self.refresh_kw_listbox()
            self.folder_name_entry.delete(0, "end")
            self.extensions_entry.delete(0, "end")
            if hasattr(self, "keywords_entry"):
                self.keywords_entry.delete(0, "end")

    def apply_regex_clicked(self):
        pat = self.regex_entry.get().strip()
        if pat:
            self.config_data["filename_regex"] = pat
            messagebox.showinfo("Regex Applied", f"Regex filter set to: {pat}", parent=self)

    def load_regex_file(self):
        path = filedialog.askopenfilename(
            parent=self,
            title=locales.get("generate_regex_title")
        )
        if path:
            basename = os.path.basename(path)
            # Get filename stem (without extension)
            stem = os.path.splitext(basename)[0]
            # Escape stem characters for safe regex matching
            escaped = re.escape(stem)
            # Replace any sequence of digits with \d+ (covers both copy numbers and timestamp numbers)
            escaped = re.sub(r'\d+', r'\\d+', escaped)
            # Create a wildcard pattern starting with the filename prefix
            pattern = f"^{escaped}.*$"
            self.regex_entry.delete(0, "end")
            self.regex_entry.insert(0, pattern)
            
            msg = locales.get("loaded_message_body", pattern=pattern)
            messagebox.showinfo(locales.get("loaded_message_title"), msg, parent=self)

    def reset_regex_clicked(self):
        self.regex_entry.delete(0, "end")
        self.regex_entry.insert(0, ".*")

    def load_template_clicked(self, name):
        try:
            print(f"[DEBUG] load_template_clicked called with template: '{name}'")
            if name == "None":
                return
            mapping = config.load_template(name)
            print(f"[DEBUG] config.load_template('{name}') returned mapping of type {type(mapping)}")
            if mapping is not None:
                # Support new template structure containing keywords and apply flags
                if isinstance(mapping, dict) and "types" in mapping:
                    types_dict = mapping.get("types", {})
                    keywords_dict = mapping.get("keywords", {})
                    kw_apply_dict = mapping.get("keyword_apply_types", {})
                else:
                    types_dict = mapping
                    keywords_dict = {}
                    kw_apply_dict = {}

                self.config_data["types"] = types_dict
                self.config_data["template"] = name
                
                # Reset and initialize settings for new template categories
                new_cats = list(types_dict.keys())
                self.config_data["included_categories"] = new_cats
                self.config_data["regex_apply_types"] = {cat: False for cat in new_cats}
                self.config_data["keyword_apply_types"] = {cat: kw_apply_dict.get(cat, False) for cat in new_cats}
                self.config_data["keywords"] = {cat: keywords_dict.get(cat, []) for cat in new_cats}
                self.config_data["subfolders"] = {cat: "" for cat in new_cats}
                
                # Refresh listboxes
                self.refresh_regex_listbox()
                self.refresh_kw_listbox()
                
                # Clear input entries
                self.folder_name_entry.delete(0, "end")
                self.extensions_entry.delete(0, "end")
                if hasattr(self, "keywords_entry"):
                    self.keywords_entry.delete(0, "end")
                    
                # Select first category by default on template load
                self.active_category = None
                if self.regex_listbox.size() > 0:
                    self.regex_listbox.selection_set(0)
                    self.on_regex_listbox_select(None)
                print("[DEBUG] load_template_clicked completed successfully.")
        except Exception as e:
            print(f"[DEBUG] Error in load_template_clicked: {e}")
            import traceback
            traceback.print_exc()

    def save_template_as(self):
        dialog = ctk.CTkInputDialog(text="Enter template name:", title="Save Template As")
        # Center dialog roughly on parent
        name = dialog.get_input()
        if name:
            name = name.strip()
            if name:
                template_data = {
                    "types": self.config_data.get("types", {}),
                    "keywords": self.config_data.get("keywords", {}),
                    "keyword_apply_types": self.config_data.get("keyword_apply_types", {})
                }
                if config.save_template(name, template_data):
                    # Refresh template list
                    self.tpl_list = config.get_templates()
                    self.tpl_menu.configure(values=self.tpl_list)
                    self.tpl_var.set(name)
                    self.config_data["template"] = name
                    messagebox.showinfo("Success", f"Template '{name}' saved successfully.", parent=self)

    def delete_template_clicked(self):
        name = self.tpl_var.get()
        if name and name != "None":
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete template '{name}'?", parent=self):
                if config.delete_template(name):
                    self.tpl_list = config.get_templates()
                    self.tpl_menu.configure(values=self.tpl_list or ["None"])
                    new_val = self.tpl_list[0] if self.tpl_list else "None"
                    self.tpl_var.set(new_val)
                    self.config_data["template"] = new_val if new_val != "None" else ""
                    messagebox.showinfo("Deleted", f"Template '{name}' has been deleted.", parent=self)

    def open_templates_folder(self):
        try:
            os.startfile(config.TEMPLATES_DIR)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open templates folder: {e}", parent=self)

    def save_settings(self):
        # Save active keywords one last time
        cat = self.get_selected_category()
        if cat and hasattr(self, "keywords_entry"):
            kw_str = self.keywords_entry.get().strip()
            kws = [k.strip() for k in kw_str.split(",") if k.strip()]
            self.config_data.setdefault("keywords", {})[cat] = kws
            
        self.config_data["enable_output_date"] = self.append_date_var.get()
        self.config_data["output_date"] = self.date_entry.get().strip()
        self.config_data["language"] = self.lang_var.get()
        self.config_data["filename_regex"] = self.regex_entry.get().strip()
        
        self.on_save_callback(self.config_data)
        self.destroy()
