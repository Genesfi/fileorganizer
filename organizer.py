import os
import re
import json
import shutil
import datetime
import threading
import queue
import traceback

CONFIG_DIR = os.path.expanduser(r"~\.file_organizer")
HISTORY_FILE = os.path.join(CONFIG_DIR, "undo_history.json")

class OrganizeThread(threading.Thread):
    def __init__(self, target_folder, config, log_queue, progress_callback, conflict_resolver, on_complete):
        super().__init__()
        self.target_folder = target_folder
        self.config = config
        self.log_queue = log_queue
        self.progress_callback = progress_callback
        self.conflict_resolver = conflict_resolver
        self.on_complete = on_complete
        
        self.is_paused = False
        self.is_stopped = False
        self._pause_cond = threading.Condition(threading.Lock())
        
        self.current_batch = []
        self.conflict_action = None  # Store choice from resolver
        self.apply_to_all_choice = None  # None, 'overwrite', 'skip', 'duplicate'
        
    def log(self, text, tag="normal"):
        self.log_queue.put((text, tag))
        
    def pause(self):
        with self._pause_cond:
            self.is_paused = True
            
    def resume(self):
        with self._pause_cond:
            self.is_paused = False
            self._pause_cond.notify_all()
            
    def stop(self):
        self.is_stopped = True
        self.resume() # Wake up from pause if stopped
        
    def check_paused(self):
        with self._pause_cond:
            while self.is_paused and not self.is_stopped:
                self._pause_cond.wait()
                
    def get_file_category(self, filename, ext):
        ext_lower = ext.lower()
        types = self.config.get("types", {})
        
        # Check matching categories
        matched_categories = []
        for cat, exts in types.items():
            if ext_lower in [e.lower() for e in exts]:
                matched_categories.append(cat)
                
        if not matched_categories:
            # Check if "Others" is in included_categories
            included = self.config.get("included_categories", [])
            if "Others" in included:
                return "Others"
            return None
            
        # If there are multiple categories matching, we check which are included.
        included = self.config.get("included_categories", [])
        active_matches = [cat for cat in matched_categories if cat in included]
        
        if not active_matches:
            return None
            
        # 1. Look for a category that has keyword matching enabled and matches the filename
        filename_lower = filename.lower()
        keyword_apply_types = self.config.get("keyword_apply_types", {})
        keywords_config = self.config.get("keywords", {})
        
        for cat in active_matches:
            if keyword_apply_types.get(cat, False):
                cat_keywords = keywords_config.get(cat, [])
                if cat_keywords:
                    # Check if any keyword matches
                    for kw in cat_keywords:
                        if kw.strip().lower() in filename_lower:
                            return cat
                            
        # 2. If no keyword-specific category matched, fall back to first category that does NOT have keyword matching enabled
        for cat in active_matches:
            if not keyword_apply_types.get(cat, False):
                return cat
                
        # 3. If all active matches require keywords but none matched, we return None (not organized)
        return None

    def apply_filters(self, filepath, category):
        if category is None:
            return False, "category_excluded"
            
        # 1. Categories filter
        included = self.config.get("included_categories", [])
        if category not in included:
            return False, "category_excluded"
            
        # 2. Check except folders
        except_folders = self.config.get("except_folders", [])
        rel_path = os.path.relpath(filepath, self.target_folder)
        for excl in except_folders:
            # Check if filepath is inside any excluded folder
            excl_abs = os.path.abspath(excl)
            file_abs = os.path.abspath(filepath)
            if file_abs.startswith(excl_abs + os.sep) or file_abs == excl_abs:
                return False, "excluded_folder"
                
        # 3. Filename regex filter (if active for this category)
        regex_apply = self.config.get("regex_apply_types", {}).get(category, False)
        if regex_apply:
            regex_str = self.config.get("filename_regex", ".*")
            try:
                if not re.search(regex_str, os.path.basename(filepath)):
                    return False, "regex_mismatch"
            except Exception as e:
                self.log(f"Regex error: {e}", "red")
                return False, "regex_error"
                
        # 4. Global Blacklist filter
        blacklist_str = self.config.get("blacklist", "")
        if blacklist_str:
            keywords = [k.strip() for k in blacklist_str.split("\n") if k.strip()]
            filename_lower = os.path.basename(filepath).lower()
            for kw in keywords:
                if kw.lower() in filename_lower:
                    return False, "blacklisted_keyword"
                    
        # 4b. Category Keywords filter (if active for this category)
        keyword_apply = self.config.get("keyword_apply_types", {}).get(category, False)
        if keyword_apply:
            cat_keywords = self.config.get("keywords", {}).get(category, [])
            if cat_keywords:
                filename_lower = os.path.basename(filepath).lower()
                matched = False
                for kw in cat_keywords:
                    if kw.strip().lower() in filename_lower:
                        matched = True
                        break
                if not matched:
                    return False, "keyword_mismatch"
                        
        # 5. Size filter
        if self.config.get("enable_size_filter", False):
            try:
                size_bytes = os.path.getsize(filepath)
                min_size = self.config.get("min_size", 0)
                min_unit = self.config.get("min_size_unit", "MB")
                max_size = self.config.get("max_size", 0)
                max_unit = self.config.get("max_size_unit", "MB")
                
                # Helper to convert units
                def to_bytes(val, unit):
                    u = unit.upper()
                    if u == "KB": return val * 1024
                    if u == "MB": return val * 1024 * 1024
                    if u == "GB": return val * 1024 * 1024 * 1024
                    return val # Bytes
                    
                min_bytes = to_bytes(min_size, min_unit)
                max_bytes = to_bytes(max_size, max_unit)
                
                if size_bytes < min_bytes:
                    return False, "too_small"
                if max_bytes > 0 and size_bytes > max_bytes:
                    return False, "too_large"
            except Exception as e:
                return False, f"size_error: {e}"
                
        # 6. Date/Time filter
        if self.config.get("enable_datetime_filter", False):
            try:
                mtime = os.path.getmtime(filepath)
                dt_file = datetime.datetime.fromtimestamp(mtime)
                
                date_from_str = self.config.get("date_from", "")
                time_from_str = self.config.get("time_from", "00:00")
                date_to_str = self.config.get("date_to", "")
                time_to_str = self.config.get("time_to", "23:59")
                
                # Default parse formats
                def parse_dt(date_s, time_s, default_dt):
                    if not date_s:
                        return default_dt
                    try:
                        return datetime.datetime.strptime(f"{date_s} {time_s}", "%Y-%m-%d %H:%M")
                    except ValueError:
                        return datetime.datetime.strptime(f"{date_s} {time_s}", "%Y-%m-%d %H:%M:%S")
                        
                dt_from = parse_dt(date_from_str, time_from_str, datetime.datetime.min)
                dt_to = parse_dt(date_to_str, time_to_str, datetime.datetime.max)
                
                if dt_file < dt_from or dt_file > dt_to:
                    return False, "date_range_mismatch"
            except Exception as e:
                return False, f"date_error: {e}"
                
        return True, "ok"

    def handle_conflict(self, src_file, dest_file):
        """Returns the target destination file path (possibly renamed) or None to skip."""
        if not os.path.exists(dest_file):
            return dest_file
            
        if self.apply_to_all_choice == "overwrite":
            try:
                os.remove(dest_file)
            except Exception as e:
                self.log(f"Overwrite failed for {os.path.basename(dest_file)}: {e}", "red")
            return dest_file
        elif self.apply_to_all_choice == "skip":
            return None
        elif self.apply_to_all_choice == "duplicate":
            # Generate a duplicate name
            base, ext = os.path.splitext(dest_file)
            counter = 1
            while os.path.exists(f"{base} ({counter}){ext}"):
                counter += 1
            return f"{base} ({counter}){ext}"
            
        # Ask user via resolver callback
        # Define a threading event to wait for response
        resolved_evt = threading.Event()
        result = {}
        
        def ui_resolve(choice, apply_to_all):
            result["choice"] = choice
            result["apply_to_all"] = apply_to_all
            resolved_evt.set()
            
        self.conflict_resolver(src_file, dest_file, ui_resolve)
        
        # Block thread until UI dialog responds
        resolved_evt.wait()
        
        choice = result.get("choice", "skip")
        apply_to_all = result.get("apply_to_all", False)
        
        if apply_to_all:
            self.apply_to_all_choice = choice
            
        if choice == "retry":
            return self.handle_conflict(src_file, dest_file)
        elif choice == "overwrite":
            try:
                os.remove(dest_file)
            except Exception as e:
                self.log(f"Overwrite failed: {e}", "red")
            return dest_file
        elif choice == "duplicate":
            base, ext = os.path.splitext(dest_file)
            counter = 1
            while os.path.exists(f"{base} ({counter}){ext}"):
                counter += 1
            return f"{base} ({counter}){ext}"
        else: # skip
            return None

    def run(self):
        try:
            self.log("Scanning target directory...", "normal")
            
            # Find files to organize
            files_to_scan = []
            scan_sub = self.config.get("scan_subfolders", False)
            
            # Categories checklist
            included = self.config.get("included_categories", [])
            
            if not os.path.exists(self.target_folder):
                self.log(f"Target folder does not exist: {self.target_folder}", "red")
                self.on_complete(False)
                return
                
            for root, dirs, files in os.walk(self.target_folder):
                # Exclude directories that are in the except folders list to prevent descending
                except_folders = self.config.get("except_folders", [])
                dirs_copy = list(dirs)
                for d in dirs_copy:
                    d_abs = os.path.join(root, d)
                    for excl in except_folders:
                        excl_abs = os.path.abspath(excl)
                        if os.path.abspath(d_abs).startswith(excl_abs + os.sep) or os.path.abspath(d_abs) == excl_abs:
                            dirs.remove(d)
                            break
                            
                for f in files:
                    filepath = os.path.join(root, f)
                    files_to_scan.append(filepath)
                    
                if not scan_sub:
                    break # Only scan top-level
                    
            total_files = len(files_to_scan)
            if total_files == 0:
                self.log("No files found to organize.", "cyan")
                self.progress_callback(1.0)
                self.on_complete(True)
                return
                
            processed = 0
            moved_count = 0
            simulated_count = 0
            filtered_count = 0
            
            # Dry-run simulate text
            mode_prefix = "[Simulate] " if self.config.get("simulate", False) else ""
            
            for filepath in files_to_scan:
                self.check_paused()
                if self.is_stopped:
                    self.log("Operation stopped by user.", "red")
                    break
                    
                # Calculate category
                base_name = os.path.basename(filepath)
                ext = os.path.splitext(base_name)[1]
                category = self.get_file_category(base_name, ext)
                
                # Check filters
                is_valid, reason = self.apply_filters(filepath, category)
                
                if not is_valid:
                    self.log(f"Filtered: {base_name} ({reason})", "cyan")
                    filtered_count += 1
                else:
                    # Category folder name
                    cat_folder_name = category
                    if self.config.get("enable_output_date", False):
                        date_val = self.config.get("output_date", "")
                        if date_val:
                            cat_folder_name = f"{category}_{date_val}"
                            
                    # Calculate subfolder nesting
                    subfolder_name = ""
                    enable_move_subfolder = self.config.get("enable_move_subfolder", False)
                    subfolder_configs = self.config.get("subfolders", {})
                    
                    if enable_move_subfolder and category in subfolder_configs:
                        # Find custom name or fallback to extension (without dot)
                        sub_pattern = subfolder_configs[category]
                        if not sub_pattern:
                            subfolder_name = ext[1:].upper() if ext else "NO_EXT"
                        else:
                            subfolder_name = sub_pattern
                            
                        # Suffix check
                        disable_suffix = self.config.get("disable_suffix_on_subfolder", False)
                        if not disable_suffix:
                            # Append modification date as suffix
                            try:
                                mtime = os.path.getmtime(filepath)
                                file_date = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                                subfolder_name = f"{subfolder_name}_{file_date}"
                            except Exception:
                                pass
                                
                    # Compute destination path
                    dest_dir = os.path.join(self.target_folder, cat_folder_name)
                    if subfolder_name:
                        dest_dir = os.path.join(dest_dir, subfolder_name)
                        
                    dest_file_path = os.path.join(dest_dir, base_name)
                    
                    # Prevent moving file into itself or its own directory
                    if os.path.abspath(filepath) == os.path.abspath(dest_file_path):
                        # Already organized
                        processed += 1
                        self.progress_callback(processed / total_files)
                        continue
                        
                    if self.config.get("simulate", False):
                        # Simulation
                        self.log(f"{mode_prefix}Would move {base_name} -> {os.path.relpath(dest_file_path, self.target_folder)}", "orange")
                        self.current_batch.append({
                            "src": filepath,
                            "dst": dest_file_path,
                            "type": "simulate"
                        })
                        simulated_count += 1
                    else:
                        # Actually move file
                        # Resolve name conflict
                        final_dest = self.handle_conflict(filepath, dest_file_path)
                        if final_dest:
                            try:
                                os.makedirs(os.path.dirname(final_dest), exist_ok=True)
                                shutil.move(filepath, final_dest)
                                self.log(f"Moved: {os.path.basename(filepath)} -> {os.path.relpath(final_dest, self.target_folder)}", "green")
                                self.current_batch.append({
                                    "src": filepath,
                                    "dst": final_dest,
                                    "type": "move"
                                })
                                moved_count += 1
                            except Exception as e:
                                self.log(f"Error moving {base_name}: {e}", "red")
                        else:
                            self.log(f"Skipped conflict: {base_name}", "cyan")
                            
                processed += 1
                self.progress_callback(processed / total_files)
                
            # Log summary
            self.log(f"--- Summary ---", "normal")
            if self.config.get("simulate", False):
                self.log(f"Simulated: {simulated_count} files, Filtered: {filtered_count} files.", "normal")
            else:
                self.log(f"Moved: {moved_count} files, Filtered: {filtered_count} files.", "normal")
                # Save to batch history for undo
                if self.current_batch:
                    save_to_history(self.current_batch)
                    
            self.on_complete(True)
            
        except Exception as e:
            self.log(f"Thread error: {traceback.format_exc()}", "red")
            self.on_complete(False)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading undo history: {e}")
        return []

def save_history(history):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving undo history: {e}")

def save_to_history(batch):
    history = load_history()
    # Add timestamp or batch ID
    batch_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": batch
    }
    history.append(batch_entry)
    save_history(history)

def clear_history():
    if os.path.exists(HISTORY_FILE):
        try:
            os.remove(HISTORY_FILE)
        except Exception as e:
            print(f"Error clearing history: {e}")

def undo_last_batch():
    history = load_history()
    if not history:
        return 0, []
        
    last_batch = history.pop()
    files_undone = []
    error_count = 0
    
    for item in reversed(last_batch["files"]):
        src = item["src"]
        dst = item["dst"]
        
        # In undo, we move back from dst to src
        if os.path.exists(dst):
            try:
                os.makedirs(os.path.dirname(src), exist_ok=True)
                shutil.move(dst, src)
                files_undone.append((dst, src))
                
                # Clean up empty parent dirs of the dst path recursively
                cleanup_empty_dirs(os.path.dirname(dst))
            except Exception as e:
                print(f"Undo failed for {dst} -> {src}: {e}")
                error_count += 1
                
    save_history(history)
    return len(files_undone), files_undone

def undo_all():
    history = load_history()
    if not history:
        return 0, []
        
    total_undone = 0
    all_undone_files = []
    
    # Process from the newest batch to the oldest
    for batch_entry in reversed(history):
        for item in reversed(batch_entry["files"]):
            src = item["src"]
            dst = item["dst"]
            if os.path.exists(dst):
                try:
                    os.makedirs(os.path.dirname(src), exist_ok=True)
                    shutil.move(dst, src)
                    all_undone_files.append((dst, src))
                    total_undone += 1
                    cleanup_empty_dirs(os.path.dirname(dst))
                except Exception as e:
                    print(f"Undo failed for {dst} -> {src}: {e}")
                    
    clear_history()
    return total_undone, all_undone_files

def cleanup_empty_dirs(path):
    """Recursively delete empty folders up the tree."""
    if not os.path.exists(path):
        return
    try:
        # Check if directory is empty
        if not os.listdir(path):
            os.rmdir(path)
            # Try cleaning up parent directory
            cleanup_empty_dirs(os.path.dirname(path))
    except Exception:
        pass

def group_folders(target_folder, group_name):
    """Moves all category folders created inside target_folder into target_folder/group_name."""
    if not group_name:
        return False, "Group folder name cannot be empty."
        
    history = load_history()
    if not history:
        return False, "No organization history found to group."
        
    # Get the last batch
    last_batch = history[-1]
    
    # Identify unique top-level folders created in this batch inside target_folder
    # We find the paths relative to target_folder and grab the first segment
    folders_to_move = set()
    for item in last_batch["files"]:
        dst = item["dst"]
        rel = os.path.relpath(dst, target_folder)
        parts = rel.split(os.sep)
        if len(parts) > 1:
            first_dir = parts[0]
            if first_dir != group_name: # Don't move the group folder into itself
                folders_to_move.add(first_dir)
                
    if not folders_to_move:
        return False, "No category folders found to group."
        
    group_path = os.path.join(target_folder, group_name)
    os.makedirs(group_path, exist_ok=True)
    
    grouped_paths = []
    
    for folder in folders_to_move:
        src_path = os.path.join(target_folder, folder)
        dest_path = os.path.join(group_path, folder)
        
        if os.path.exists(src_path):
            try:
                # If destination already exists, merge them
                if os.path.exists(dest_path):
                    for root, dirs, files in os.walk(src_path):
                        for file in files:
                            s_file = os.path.join(root, file)
                            r_path = os.path.relpath(s_file, src_path)
                            d_file = os.path.join(dest_path, r_path)
                            os.makedirs(os.path.dirname(d_file), exist_ok=True)
                            shutil.move(s_file, d_file)
                    cleanup_empty_dirs(src_path)
                else:
                    shutil.move(src_path, dest_path)
                grouped_paths.append((src_path, dest_path))
            except Exception as e:
                print(f"Error grouping folder {folder}: {e}")
                
    # Update last batch history entries to reflect new destinations!
    # This allows Undo to still work after grouping!
    updated_files = []
    for item in last_batch["files"]:
        dst = item["dst"]
        rel = os.path.relpath(dst, target_folder)
        parts = rel.split(os.sep)
        if parts[0] in folders_to_move:
            # Recompute destination path with group folder prepended
            new_dst = os.path.join(group_path, rel)
            updated_files.append({
                "src": item["src"],
                "dst": new_dst,
                "type": item["type"]
            })
        else:
            updated_files.append(item)
            
    last_batch["files"] = updated_files
    # Add a special grouping log in the history so we can undo grouping separately!
    last_batch["group_folder"] = group_path
    last_batch["grouped_folders"] = grouped_paths
    save_history(history)
    
    return True, f"Successfully grouped folders into '{group_name}'."

def undo_group_move():
    history = load_history()
    if not history:
        return False, "No history to undo."
        
    last_batch = history[-1]
    if "group_folder" not in last_batch or "grouped_folders" not in last_batch:
        return False, "Last action was not a group folder operation."
        
    group_folder = last_batch["group_folder"]
    grouped_folders = last_batch["grouped_folders"]
    
    undone_count = 0
    for src_path, dest_path in grouped_folders:
        # Move back from dest_path (inside group folder) to src_path (target folder root)
        if os.path.exists(dest_path):
            try:
                # Merge if folder already exists at src_path
                if os.path.exists(src_path):
                    for root, dirs, files in os.walk(dest_path):
                        for file in files:
                            d_file = os.path.join(root, file)
                            r_path = os.path.relpath(d_file, dest_path)
                            s_file = os.path.join(src_path, r_path)
                            os.makedirs(os.path.dirname(s_file), exist_ok=True)
                            shutil.move(d_file, s_file)
                    cleanup_empty_dirs(dest_path)
                else:
                    shutil.move(dest_path, src_path)
                undone_count += 1
            except Exception as e:
                print(f"Error undoing group for {dest_path}: {e}")
                
    # Revert history destination paths to original (non-grouped) paths
    updated_files = []
    target_folder = os.path.dirname(group_folder)
    for item in last_batch["files"]:
        dst = item["dst"]
        rel = os.path.relpath(dst, group_folder)
        # If the file path goes through the group folder, restore it
        if os.path.abspath(dst).startswith(os.path.abspath(group_folder)):
            new_dst = os.path.join(target_folder, rel)
            updated_files.append({
                "src": item["src"],
                "dst": new_dst,
                "type": item["type"]
            })
        else:
            updated_files.append(item)
            
    last_batch["files"] = updated_files
    
    # Remove group indicators from history batch
    del last_batch["group_folder"]
    del last_batch["grouped_folders"]
    save_history(history)
    
    # Clean up empty group folder
    cleanup_empty_dirs(group_folder)
    return True, "Successfully undid folder grouping."
