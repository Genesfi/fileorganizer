import os
import customtkinter as ctk
import locales
import organizer

class CategoriesDialog(ctk.CTkToplevel):
    def __init__(self, parent, all_categories, current_selected, on_save):
        super().__init__(parent)
        self.title(locales.get("select_categories_title"))
        self.geometry("380x600")
        self.transient(parent)
        self.grab_set()
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "organize_files.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        self.all_categories = all_categories
        self.on_save = on_save
        
        # Heading
        self.label = ctk.CTkLabel(self, text=locales.get("include_categories"), font=("Arial", 14, "bold"))
        self.label.pack(pady=15, anchor="w", padx=20)
        
        # Scrollable Frame
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.checkboxes = {}
        for cat in self.all_categories:
            var = ctk.BooleanVar(value=(cat in current_selected))
            cb = ctk.CTkCheckBox(self.scroll_frame, text=cat, variable=var)
            cb.pack(fill="x", pady=6, anchor="w")
            self.checkboxes[cat] = var
            
        # Button container
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=15, padx=20)
        
        self.btn_unselect = ctk.CTkButton(self.btn_frame, text=locales.get("unselect_all"), command=self.unselect_all, width=110)
        self.btn_unselect.pack(side="left", padx=5)
        
        self.btn_select = ctk.CTkButton(self.btn_frame, text=locales.get("select_all"), command=self.select_all, width=100)
        self.btn_select.pack(side="left", padx=5)
        
        self.btn_done = ctk.CTkButton(self.btn_frame, text=locales.get("done"), command=self.done, width=100)
        self.btn_done.pack(side="right", padx=5)
        
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def select_all(self):
        for var in self.checkboxes.values():
            var.set(True)
            
    def unselect_all(self):
        for var in self.checkboxes.values():
            var.set(False)
            
    def done(self):
        selected = [cat for cat, var in self.checkboxes.items() if var.get()]
        self.on_save(selected)
        self.destroy()


class SubfoldersDialog(ctk.CTkToplevel):
    def __init__(self, parent, categories, current_subfolders, current_enabled, current_disable_suffix, on_save):
        super().__init__(parent)
        self.title("Subfolders")
        self.geometry("450x600")
        self.transient(parent)
        self.grab_set()
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "organize_files.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        self.categories = categories
        self.on_save = on_save
        
        # Suffix Checkbox
        self.disable_suffix_var = ctk.BooleanVar(value=current_disable_suffix)
        self.cb_suffix = ctk.CTkCheckBox(self, text="Disable add date/size to the last folder", variable=self.disable_suffix_var)
        self.cb_suffix.pack(anchor="w", padx=20, pady=15)
        
        # Scrollable Frame
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.rows = {}
        for cat in self.categories:
            if cat == "Others":
                continue
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=6)
            
            # Checkbox
            is_enabled = current_enabled and (cat in current_subfolders)
            var_cb = ctk.BooleanVar(value=is_enabled)
            cb = ctk.CTkCheckBox(row_frame, text=f"{cat}:", variable=var_cb, width=180)
            cb.pack(side="left", anchor="w")
            
            # Subfolder input
            curr_val = current_subfolders.get(cat, "")
            entry = ctk.CTkEntry(row_frame, placeholder_text="e.g. extension, or custom folder")
            entry.insert(0, curr_val)
            entry.pack(side="right", fill="x", expand=True, padx=(10, 0))
            
            # Link toggle state
            def make_toggle(ent, v_cb):
                def toggle():
                    if v_cb.get():
                        ent.configure(state="normal")
                    else:
                        ent.configure(state="disabled")
                return toggle
            
            cb.configure(command=make_toggle(entry, var_cb))
            if not is_enabled:
                entry.configure(state="disabled")
                
            self.rows[cat] = (var_cb, entry)
            
        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=15, padx=20)
        
        self.btn_cancel = ctk.CTkButton(self.btn_frame, text="Cancel", fg_color="gray", hover_color="darkgray", command=self.destroy, width=100)
        self.btn_cancel.pack(side="right", padx=5)
        
        self.btn_ok = ctk.CTkButton(self.btn_frame, text="OK", command=self.done, width=100)
        self.btn_ok.pack(side="right", padx=5)
        
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def done(self):
        subfolders_data = {}
        any_enabled = False
        for cat, (var_cb, entry) in self.rows.items():
            if var_cb.get():
                any_enabled = True
                subfolders_data[cat] = entry.get().strip()
                
        self.on_save(subfolders_data, any_enabled, self.disable_suffix_var.get())
        self.destroy()


class ConflictDialog(ctk.CTkToplevel):
    def __init__(self, parent, src_file, dest_file, callback):
        super().__init__(parent)
        self.title("File exists")
        self.geometry("420x310")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: self.resolve("skip"))
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "organize_files.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
                
        self.callback = callback
        self.filename = os.path.basename(src_file)
        
        # Get file sizes
        try:
            self.src_size = os.path.getsize(src_file)
        except Exception:
            self.src_size = 0
            
        try:
            self.dest_size = os.path.getsize(dest_file)
        except Exception:
            self.dest_size = 0
            
        # Filename Label
        self.lbl_filename = ctk.CTkLabel(self, text=self.filename, font=("Arial", 14, "bold"), wraplength=380)
        self.lbl_filename.pack(pady=(15, 10))
        
        # Unit OptionMenu Selector
        self.unit_var = ctk.StringVar(value="KB")
        self.menu_unit = ctk.CTkOptionMenu(
            self,
            values=["B", "KB", "MB", "GB"],
            variable=self.unit_var,
            command=self.update_sizes,
            width=80,
            fg_color="#4A4A4A",
            button_color="#5A5A5A",
            button_hover_color="#6A6A6A"
        )
        self.menu_unit.pack(pady=5)
        
        # File Size Labels
        self.lbl_size1 = ctk.CTkLabel(self, text="", font=("Arial", 12))
        self.lbl_size1.pack(pady=2)
        
        self.lbl_size2 = ctk.CTkLabel(self, text="", font=("Arial", 12))
        self.lbl_size2.pack(pady=2)
        
        self.update_sizes("KB")
        
        # Checkbox Apply to All
        self.apply_to_all_var = ctk.BooleanVar(value=False)
        self.cb_apply = ctk.CTkCheckBox(self, text="Apply to all", variable=self.apply_to_all_var)
        self.cb_apply.pack(pady=15)
        
        # Buttons frame
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=30, pady=10)
        
        # Buttons: Skip, Overwrite, Duplicate
        self.btn_skip = ctk.CTkButton(
            self.btn_frame,
            text="Skip",
            width=100,
            fg_color="#4A4A4A",
            hover_color="#5A5A5A",
            command=lambda: self.resolve("skip")
        )
        self.btn_skip.pack(side="left", padx=5, fill="x", expand=True)
        
        self.btn_overwrite = ctk.CTkButton(
            self.btn_frame,
            text="Overwrite",
            width=100,
            fg_color="#4A4A4A",
            hover_color="#5A5A5A",
            command=lambda: self.resolve("overwrite")
        )
        self.btn_overwrite.pack(side="left", padx=5, fill="x", expand=True)
        
        self.btn_duplicate = ctk.CTkButton(
            self.btn_frame,
            text="Duplicate",
            width=100,
            fg_color="#4A4A4A",
            hover_color="#5A5A5A",
            command=lambda: self.resolve("duplicate")
        )
        self.btn_duplicate.pack(side="left", padx=5, fill="x", expand=True)
        
        self.center_window()

    def update_sizes(self, unit):
        # Format sizes based on selected unit
        def format_size(bytes_val):
            if unit == "KB":
                val = bytes_val / 1024
            elif unit == "MB":
                val = bytes_val / (1024 * 1024)
            elif unit == "GB":
                val = bytes_val / (1024 * 1024 * 1024)
            else:
                return f"{bytes_val} B"
            return "{:.2f} {}".format(val, unit)
            
        self.lbl_size1.configure(text="File size 1: " + format_size(self.src_size))
        self.lbl_size2.configure(text="File size 2: " + format_size(self.dest_size))

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def resolve(self, choice):
        apply_all = self.apply_to_all_var.get()
        self.destroy()
        self.callback(choice, apply_all)
        



class UndoDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_select):
        super().__init__(parent)
        self.title(locales.get("undo_options_title"))
        self.geometry("400x280")
        self.transient(parent)
        self.grab_set()
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "organize_files.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        self.on_select = on_select
        
        # Read history to get counts
        history = organizer.load_history()
        
        last_batch_count = 0
        last_batch_group = False
        all_action_count = 0
        
        if history:
            last_batch = history[-1]
            last_batch_count = len(last_batch.get("files", []))
            last_batch_group = "group_folder" in last_batch
            
            for batch in history:
                all_action_count += len(batch.get("files", []))
                
        # Main label
        self.label = ctk.CTkLabel(self, text=locales.get("what_to_undo"), font=("Arial", 14, "bold"))
        self.label.pack(pady=20)
        
        # Undo Last Button
        last_text = locales.get("undo_last", count=last_batch_count)
        self.btn_last = ctk.CTkButton(self, text=last_text, command=lambda: self.choose("last"), state="normal" if last_batch_count > 0 else "disabled")
        self.btn_last.pack(fill="x", padx=30, pady=6)
        
        # Undo Group Button
        group_text = locales.get("undo_group", count=1 if last_batch_group else 0)
        self.btn_group = ctk.CTkButton(self, text=group_text, command=lambda: self.choose("group"), state="normal" if last_batch_group else "disabled")
        self.btn_group.pack(fill="x", padx=30, pady=6)
        
        # Undo All Button
        all_text = locales.get("undo_all", count=all_action_count)
        self.btn_all = ctk.CTkButton(self, text=all_text, command=lambda: self.choose("all"), state="normal" if all_action_count > 0 else "disabled")
        self.btn_all.pack(fill="x", padx=30, pady=6)
        
        # Cancel Button
        self.btn_cancel = ctk.CTkButton(self, text="Cancel", fg_color="gray", hover_color="darkgray", command=self.destroy)
        self.btn_cancel.pack(fill="x", padx=30, pady=(15, 0))
        
        self.center_window()
        
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def choose(self, option):
        self.destroy()
        self.on_select(option)
