import os
import queue
import customtkinter as ctk
from tkinter import filedialog, messagebox, Menu
import locales
import config
import organizer
from ui.settings_window import SettingsWindow
from ui.filter_window import FilterWindow
from ui.dialogs import ConflictDialog, UndoDialog

# Try importing TkinterDnD2
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    dnd_available = True
except ImportError:
    dnd_available = False
    print("tkinterdnd2 not available. Drag & drop will be disabled.")

# Define base class depending on DnD availability
if dnd_available:
    class BaseWindow(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self):
            ctk.CTk.__init__(self)
            TkinterDnD.DnDWrapper.__init__(self)
else:
    class BaseWindow(ctk.CTk):
        def __init__(self):
            super().__init__()

class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        
        # Load configuration
        self.config_data = config.load_config()
        
        # Initialize locale
        locales.load_translations(self.config_data.get("language", "English"))
        locales.register_callback(self.refresh_labels)
        
        # Set app parameters
        self.title(locales.get("app_title"))
        self.geometry("750x660")
        
        # Icon
        self.set_icon()
        
        # Apply theme
        self.current_theme = self.config_data.get("theme", "dark")
        ctk.set_appearance_mode(self.current_theme)
        
        # Organizer State
        self.organize_thread = None
        self.log_queue = queue.Queue()
        self.target_folder = ""
        self.session_files_moved = False
        
        # Build UI
        self.create_widgets()
        
        # Setup Drag and Drop
        if dnd_available:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind('<<Drop>>', self.on_folder_drop)
                # Register components to accept drop as well
                self.entry_path.drop_target_register(DND_FILES)
                self.entry_path.dnd_bind('<<Drop>>', self.on_folder_drop)
            except Exception as e:
                print(f"Failed to register DND: {e}")
                
        # Start checking log queue
        self.check_log_queue()
        
        # Update initial undo/group button states
        self.update_history_buttons()
        
        # Center the window on the screen
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = 750
        height = 660
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def set_icon(self):
        # We copied organize_files.ico into assets folder!
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "organize_files.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"Error loading icon bitmap: {e}")

    def create_widgets(self):
        # Top margin
        ctk.CTkLabel(self, text="", height=5).pack()
        
        # Row 1: Folder Selection
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=5)
        
        self.btn_select = ctk.CTkButton(row1, text=locales.get("browse"), command=self.browse_folder, width=120)
        self.btn_select.pack(side="left", padx=(0, 10))
        
        self.entry_path = ctk.CTkEntry(row1, placeholder_text="Drag & drop a folder here or click Select Folder...")
        self.entry_path.pack(side="left", fill="x", expand=True)
        
        # Row 2: Control Buttons Row
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=5)
        
        self.simulate_var = ctk.BooleanVar(value=self.config_data.get("simulate", False))
        self.cb_simulate = ctk.CTkCheckBox(row2, text=locales.get("simulate"), variable=self.simulate_var, command=self.on_simulate_changed)
        self.cb_simulate.pack(side="left", padx=(0, 15))
        
        # Buttons: Run, Pause, Stop, Undo, Group, Filter, Dark, Settings
        self.btn_run = ctk.CTkButton(row2, text=locales.get("run"), width=65, command=self.run_organization)
        self.btn_run.pack(side="left", padx=3)
        
        self.btn_pause = ctk.CTkButton(row2, text="Pause", width=65, state="disabled", command=self.pause_organization)
        self.btn_pause.pack(side="left", padx=3)
        
        self.btn_stop = ctk.CTkButton(row2, text=locales.get("stop"), width=65, state="disabled", command=self.stop_organization)
        self.btn_stop.pack(side="left", padx=3)
        
        self.btn_undo = ctk.CTkButton(row2, text=locales.get("undo"), width=65, command=self.open_undo_dialog)
        self.btn_undo.pack(side="left", padx=3)
        
        self.btn_group = ctk.CTkButton(row2, text=locales.get("group"), width=65, command=self.group_folders_clicked)
        self.btn_group.pack(side="left", padx=3)
        
        self.btn_filter = ctk.CTkButton(row2, text=locales.get("filter"), width=65, command=self.open_filter_window)
        self.btn_filter.pack(side="left", padx=3)
        
        theme_text = "Light" if self.current_theme == "dark" else "Dark"
        self.btn_dark = ctk.CTkButton(row2, text=theme_text, width=65, command=self.toggle_theme)
        self.btn_dark.pack(side="left", padx=3)
        
        self.btn_settings = ctk.CTkButton(row2, text=locales.get("settings"), width=80, command=self.open_settings_window)
        self.btn_settings.pack(side="left", padx=3)
        
        # Row 3: Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(fill="x", padx=15, pady=8)
        self.progress_bar.set(0)
        
        # Row 4: Status label
        self.lbl_status = ctk.CTkLabel(self, text="Ready", font=("Arial", 12), anchor="w")
        self.lbl_status.pack(fill="x", padx=15, pady=(2, 5))
        
        # Row 5: Log text area (using Tkinter Text inside CTkFrame for advanced tagging)
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        import tkinter as tk
        self.log_scrollbar = tk.Scrollbar(log_frame)
        self.log_scrollbar.pack(side="right", fill="y")
        
        # Custom color codes:
        # Dark theme background: #1E1E1E
        # Light theme background: #FFFFFF
        bg_col = "#1E1E1E" if self.current_theme == "dark" else "#F0F0F0"
        fg_col = "#FFFFFF" if self.current_theme == "dark" else "#000000"
        
        self.log_text = tk.Text(
            log_frame, 
            yscrollcommand=self.log_scrollbar.set, 
            bg=bg_col, 
            fg=fg_col, 
            font=("Consolas", 10),
            bd=0,
            highlightthickness=0
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scrollbar.config(command=self.log_text.yview)
        
        # Setup Text tags for color coding:
        # Green = moved, Orange = simulated, Cyan = filtered, Red = errors
        self.log_text.tag_config("green", foreground="#2ECC71")
        self.log_text.tag_config("orange", foreground="#E67E22")
        self.log_text.tag_config("cyan", foreground="#1ABC9C")
        self.log_text.tag_config("red", foreground="#E74C3C")
        self.log_text.tag_config("normal", foreground=fg_col)
        
        # Bind events for opening folders from logs
        self.log_text.bind("<Double-Button-1>", self.on_log_double_click)
        self.log_text.bind("<Button-3>", self.show_log_context_menu)
        
        # Context menu
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label=locales.get("prompt_open_folder_context"), command=self.open_folder_from_context)
        
        # Footer
        self.lbl_footer = ctk.CTkLabel(self, text=locales.get("watermark"), font=("Arial", 10, "italic"))
        self.lbl_footer.pack(pady=10)
        
        # Intercept exit protocol to protect undo history
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def on_simulate_changed(self):
        self.config_data["simulate"] = self.simulate_var.get()
        config.save_config(self.config_data)

    def refresh_labels(self):
        self.title(locales.get("app_title"))
        self.btn_select.configure(text=locales.get("browse"))
        self.cb_simulate.configure(text=locales.get("simulate"))
        self.btn_run.configure(text=locales.get("run"))
        self.btn_stop.configure(text=locales.get("stop"))
        self.btn_undo.configure(text=locales.get("undo"))
        self.btn_group.configure(text=locales.get("group"))
        self.btn_filter.configure(text=locales.get("filter"))
        self.btn_settings.configure(text=locales.get("settings"))
        self.lbl_footer.configure(text=locales.get("watermark"))
        
        # Re-create context menu to translate it
        self.context_menu.entryconfigure(0, label=locales.get("prompt_open_folder_context"))

    def browse_folder(self):
        folder = filedialog.askdirectory(parent=self, title=locales.get("browse"))
        if folder:
            self.set_target_folder(folder)

    def set_target_folder(self, folder):
        self.target_folder = os.path.normpath(folder)
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, self.target_folder)
        self.lbl_status.configure(text=f"Selected folder: {self.target_folder}")

    def on_folder_drop(self, event):
        data = event.data
        # Handle curly braces wrapping paths with spaces on Windows
        if data.startswith('{') and data.endswith('}'):
            data = data[1:-1]
        data = os.path.normpath(data)
        if os.path.isdir(data):
            self.set_target_folder(data)
        else:
            # Try to grab dirname if file is dropped
            dirname = os.path.dirname(data)
            if os.path.isdir(dirname):
                self.set_target_folder(dirname)

    def append_log(self, text, tag="normal"):
        self.log_text.insert("end", text + "\n", tag)
        self.log_text.see("end")

    def run_organization(self):
        if not self.target_folder or not os.path.exists(self.target_folder):
            messagebox.showwarning(
                locales.get("message_select_valid_folder_title"),
                locales.get("message_select_valid_folder"),
                parent=self
            )
            return
            
        self.config_data = config.load_config()
        self.config_data["simulate"] = self.simulate_var.get()
        
        # Reset progress and log
        self.progress_bar.set(0)
        self.log_text.delete("1.0", "end")
        
        # Enable Stop/Pause, Disable Run
        self.btn_run.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="Pause")
        self.btn_stop.configure(state="normal")
        self.btn_undo.configure(state="disabled")
        self.btn_group.configure(state="disabled")
        self.btn_filter.configure(state="disabled")
        self.btn_settings.configure(state="disabled")
        
        self.lbl_status.configure(text="Organizing files...")
        
        # Start organizing thread
        self.organize_thread = organizer.OrganizeThread(
            target_folder=self.target_folder,
            config=self.config_data,
            log_queue=self.log_queue,
            progress_callback=self.update_progress,
            conflict_resolver=self.resolve_conflict_callback,
            on_complete=self.on_organization_complete
        )
        self.organize_thread.start()

    def update_progress(self, val):
        self.progress_bar.set(val)

    def resolve_conflict_callback(self, src, dest, callback):
        # This is called from the background thread. We schedule the dialog to run on the main UI thread.
        self.after(0, lambda: ConflictDialog(self, src, dest, callback))

    def on_organization_complete(self, success):
        self.after(0, lambda: self._on_org_complete_ui(success))

    def _on_org_complete_ui(self, success):
        self.btn_run.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="Pause")
        self.btn_stop.configure(state="disabled")
        self.btn_filter.configure(state="normal")
        self.btn_settings.configure(state="normal")
        
        self.lbl_status.configure(text="Finished" if success else "Failed")
        self.update_history_buttons()

        # Update session_files_moved if actual moves occurred in the thread
        if self.organize_thread and hasattr(self.organize_thread, "current_batch"):
            has_moves = any(item.get("type") == "move" for item in self.organize_thread.current_batch)
            if has_moves:
                self.session_files_moved = True

    def pause_organization(self):
        if self.organize_thread and self.organize_thread.is_alive():
            if self.organize_thread.is_paused:
                self.organize_thread.resume()
                self.btn_pause.configure(text="Pause")
                self.lbl_status.configure(text="Organizing files...")
            else:
                self.organize_thread.pause()
                self.btn_pause.configure(text="Resume")
                self.lbl_status.configure(text="Paused")

    def stop_organization(self):
        if self.organize_thread and self.organize_thread.is_alive():
            self.organize_thread.stop()
            self.btn_stop.configure(state="disabled")
            self.btn_pause.configure(state="disabled")
            self.lbl_status.configure(text="Stopping...")

    def update_history_buttons(self):
        history = organizer.load_history()
        has_history = len(history) > 0
        self.btn_undo.configure(state="normal" if has_history else "disabled")
        
        # Group is enabled if there is history and the last batch hasn't been grouped yet
        has_groupable = False
        if history:
            last = history[-1]
            if "group_folder" not in last and len(last.get("files", [])) > 0:
                has_groupable = True
        self.btn_group.configure(state="normal" if has_groupable else "disabled")

    def open_undo_dialog(self):
        UndoDialog(self, self.perform_undo)

    def perform_undo(self, option):
        self.lbl_status.configure(text="Undoing action...")
        self.log_text.delete("1.0", "end")
        
        if option == "last":
            count, files = organizer.undo_last_batch()
            for dst, src in files:
                self.append_log(f"Restored: {os.path.basename(src)} <- {os.path.relpath(dst, self.target_folder)}", "cyan")
            self.append_log(locales.get("done_last_batch_undone"), "green")
            self.lbl_status.configure(text="Last batch undone.")
        elif option == "group":
            success, msg = organizer.undo_group_move()
            if success:
                self.append_log(locales.get("done_group_move_undone"), "green")
                self.lbl_status.configure(text="Group folder undone.")
            else:
                self.append_log(f"Group undo failed: {msg}", "red")
                self.lbl_status.configure(text="Group undo failed.")
        elif option == "all":
            count, files = organizer.undo_all()
            for dst, src in files:
                self.append_log(f"Restored: {os.path.basename(src)} <- {os.path.relpath(dst, self.target_folder)}", "cyan")
            self.append_log(locales.get("done_all_batches_undone"), "green")
            self.lbl_status.configure(text="All actions undone.")
            
        self.update_history_buttons()

    def group_folders_clicked(self):
        if not self.target_folder:
            return
        dialog = ctk.CTkInputDialog(text=locales.get("name_group_folder"), title=locales.get("group"))
        group_name = dialog.get_input()
        if group_name:
            group_name = group_name.strip()
            if not group_name:
                messagebox.showwarning("Warning", locales.get("message_folder_name_empty"), parent=self)
                return
                
            success, msg = organizer.group_folders(self.target_folder, group_name)
            if success:
                self.append_log(msg, "green")
                self.lbl_status.configure(text=f"Grouped into {group_name}.")
            else:
                self.append_log(msg, "red")
                self.lbl_status.configure(text="Grouping failed.")
            self.update_history_buttons()

    def toggle_theme(self):
        if self.current_theme == "dark":
            self.current_theme = "light"
            self.btn_dark.configure(text="Dark")
        else:
            self.current_theme = "dark"
            self.btn_dark.configure(text="Light")
            
        ctk.set_appearance_mode(self.current_theme)
        
        # Update text box backgrounds
        bg_col = "#1E1E1E" if self.current_theme == "dark" else "#F0F0F0"
        fg_col = "#FFFFFF" if self.current_theme == "dark" else "#000000"
        self.log_text.configure(bg=bg_col, fg=fg_col)
        self.log_text.tag_config("normal", foreground=fg_col)
        
        # Save theme setting
        self.config_data["theme"] = self.current_theme
        config.save_config(self.config_data)

    def open_filter_window(self):
        self.config_data = config.load_config()
        all_cats = list(self.config_data.get("types", {}).keys())
        FilterWindow(self, self.config_data, all_cats, self.save_filter_config)

    def save_filter_config(self, new_config):
        self.config_data = new_config
        config.save_config(self.config_data)
        self.lbl_status.configure(text="Filters updated.")

    def open_settings_window(self):
        SettingsWindow(self, self.save_settings_config)

    def save_settings_config(self, new_config):
        self.config_data = new_config
        config.save_config(self.config_data)
        # Apply updated language if changed
        locales.set_language(self.config_data.get("language", "English"))
        self.lbl_status.configure(text="Settings saved.")

    def check_log_queue(self):
        while not self.log_queue.empty():
            try:
                text, tag = self.log_queue.get_nowait()
                self.append_log(text, tag)
            except queue.Empty:
                break
        self.after(100, self.check_log_queue)

    def get_destination_folder_from_line(self, line_text):
        """Extracts the destination directory path from a log line."""
        # Logs look like:
        # Moved: file.txt -> CategorySubfolder/file.txt
        # [Simulate] Would move file.txt -> CategorySubfolder/file.txt
        # Restored: file.txt <- CategorySubfolder/file.txt
        if "->" in line_text:
            parts = line_text.split("->")
            if len(parts) > 1:
                rel_dest = parts[1].strip()
                # rel_dest represents relative path of the file
                abs_dest = os.path.join(self.target_folder, rel_dest)
                return os.path.dirname(abs_dest)
        elif "<-" in line_text:
            parts = line_text.split("<-")
            if len(parts) > 1:
                rel_dest = parts[1].strip()
                abs_dest = os.path.join(self.target_folder, rel_dest)
                return os.path.dirname(abs_dest)
        return None

    def on_log_double_click(self, event):
        line_text = self.log_text.get("current linestart", "current lineend")
        dest_dir = self.get_destination_folder_from_line(line_text)
        if dest_dir and os.path.exists(dest_dir):
            try:
                os.startfile(dest_dir)
            except Exception as e:
                print(f"Failed to open folder: {e}")

    def show_log_context_menu(self, event):
        # Move cursor to click position
        self.log_text.mark_set("current", f"@{event.x},{event.y}")
        line_text = self.log_text.get("current linestart", "current lineend")
        dest_dir = self.get_destination_folder_from_line(line_text)
        
        if dest_dir and os.path.exists(dest_dir):
            self.context_menu_dest_dir = dest_dir
            self.context_menu.post(event.x_root, event.y_root)

    def open_folder_from_context(self):
        if hasattr(self, "context_menu_dest_dir") and self.context_menu_dest_dir:
            try:
                os.startfile(self.context_menu_dest_dir)
            except Exception as e:
                print(f"Failed to open folder: {e}")

    def on_exit(self):
        has_undo = False
        undo_count = 0
        if getattr(self, "session_files_moved", False):
            history = organizer.load_history()
            if history:
                for b in history:
                    undo_count += len(b.get("files", []))
                if undo_count > 0:
                    has_undo = True
                
        # If organizer is running or there is undo history, alert the user!
        if self.organize_thread and self.organize_thread.is_alive():
            if messagebox.askyesno("Exit", "File organization is still running. Stop it and exit?", parent=self):
                self.organize_thread.stop()
                self.destroy()
            return
            
        if has_undo:
            # Custom confirmation exit dialog
            # "You have interrupted the file organization and there is undo history available..."
            # Options: Yes(Exit), Return to App, Undo All(Safe Exit)
            from ui.dialogs import ctk
            exit_dialog = ExitConfirmationDialog(self, undo_count)
            # wait for action
            self.wait_window(exit_dialog)
        else:
            self.destroy()


class ExitConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, parent, count):
        super().__init__(parent)
        self.parent = parent
        self.count = count
        
        self.title(locales.get("confirm_exit_title"))
        self.geometry("450x260")
        self.transient(parent)
        self.grab_set()
        
        # Message
        msg = locales.get("confirm_exit_message")
        self.label = ctk.CTkLabel(self, text=msg, font=("Arial", 12), wraplength=410, justify="left")
        self.label.pack(pady=20, padx=20)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        # Return to App
        self.btn_return = ctk.CTkButton(btn_frame, text=locales.get("return_to_app"), command=self.destroy)
        self.btn_return.pack(side="left", padx=5, fill="x", expand=True)
        
        # Undo All (Safe Exit)
        safe_text = locales.get("undo_all_safe_exit")
        self.btn_safe = ctk.CTkButton(btn_frame, text=safe_text, fg_color="#1ABC9C", hover_color="#16A085", command=self.safe_exit)
        self.btn_safe.pack(side="left", padx=5, fill="x", expand=True)
        
        # Yes (Exit)
        yes_text = locales.get("yes_exit")
        self.btn_exit = ctk.CTkButton(btn_frame, text=yes_text, fg_color="#C0392B", hover_color="#962D22", command=self.force_exit)
        self.btn_exit.pack(side="left", padx=5, fill="x", expand=True)
        
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def force_exit(self):
        # Prompt "ARE YOU SURE YOU WANT TO EXIT? ALL UNDO HISTORY WILL BE LOST!"
        if messagebox.askyesno(locales.get("confirm_sure_title"), locales.get("confirm_sure_message"), parent=self):
            organizer.clear_history()
            self.destroy()
            self.parent.destroy()
            
    def safe_exit(self):
        self.destroy()
        # Perform Undo All in parent context
        self.parent.perform_undo("all")
        organizer.clear_history()
        self.parent.destroy()
