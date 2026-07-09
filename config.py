import os
import json
import shutil

CONFIG_DIR = os.path.expanduser(r"~\.file_organizer")
CONFIG_FILE = os.path.join(CONFIG_DIR, "file_organizer_config.json")
TEMPLATES_DIR = os.path.join(CONFIG_DIR, "templates")

DEFAULT_TYPES = {
    "Videos": [".mp4", ".mov", ".avi", ".mkv", ".flv", ".webm"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".md"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "Photoshop Project": [".psd"],
    "After Effect Project": [".aep"],
    "Premiere Pro Project": [".prproj"],
    "DaVinci Resolve Project": [".drp"],
    "Final Cut Pro Project": [".fcpxml"],
    "Vector Template/Project": [".ai", ".eps", ".svg", ".cdr", ".dxf", ".wmf", ".emf", ".odg"],
    "Thumbnails": [".jpg", ".jpeg", ".png", ".psd"],
    "Captions/Subtitles": [".srt", ".vtt", ".ass", ".ssa", ".sub"],
    "Fonts": [".ttf", ".otf", ".woff", ".woff2"],
    "LUTs/Color Presets": [".cube", ".look", ".3dl"],
    "Plugins/Scripts": [".jsx", ".jsxbin", ".aex"],
    "Project Backups": [".bak", ".tmp", ".autosave"],
    "Screen Recording Software": [".camproj", ".trec", ".mxc", ".screenflow"]
}

DEFAULT_CONFIG = {
    "types": DEFAULT_TYPES,
    "template": "Editor & Creator",
    "regex_apply_types": {k: False for k in DEFAULT_TYPES.keys()},
    "keyword_apply_types": {k: False for k in DEFAULT_TYPES.keys()},
    "category_apply_types": {},
    "enable_output_date": False,
    "output_date": "",
    "theme": "dark",
    "language": "English",
    "subfolders": {},
    "enable_move_subfolder": False,
    "disable_suffix_on_subfolder": False,
    "blacklist": "",
    "scan_subfolders": False,
    "enable_datetime_filter": False,
    "enable_size_filter": False,
    "min_size": 0,
    "min_size_unit": "MB",
    "max_size": 0,
    "max_size_unit": "MB",
    "date_from": "",
    "time_from": "00:00",
    "date_to": "",
    "time_to": "23:59",
    "except_folders": [],
    "included_categories": list(DEFAULT_TYPES.keys()) + ["Others"],
    "filename_regex": ".*"
}

def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

def load_config():
    ensure_config_dir()
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Overwrite default config keys with loaded values directly (do not merge dictionaries)
        merged = DEFAULT_CONFIG.copy()
        for k, v in config.items():
            merged[k] = v
            
        # Sanitize included_categories to remove stale categories not present in active types
        active_cats = list(merged.get("types", {}).keys()) + ["Others"]
        merged["included_categories"] = [c for c in merged.get("included_categories", []) if c in active_cats]
        
        return merged
    except Exception as e:
        print(f"Error loading config, returning defaults: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")

def get_templates():
    ensure_config_dir()
    templates = []
    if os.path.exists(TEMPLATES_DIR):
        for f in os.listdir(TEMPLATES_DIR):
            if f.endswith(".json"):
                templates.append(f[:-5])
    return templates

def load_template(name):
    ensure_config_dir()
    template_path = os.path.join(TEMPLATES_DIR, f"{name}.json")
    if not os.path.exists(template_path):
        return None
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading template {name}: {e}")
        return None

def save_template(name, mapping):
    ensure_config_dir()
    template_path = os.path.join(TEMPLATES_DIR, f"{name}.json")
    try:
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving template {name}: {e}")
        return False

def delete_template(name):
    ensure_config_dir()
    template_path = os.path.join(TEMPLATES_DIR, f"{name}.json")
    if os.path.exists(template_path):
        try:
            os.remove(template_path)
            return True
        except Exception as e:
            print(f"Error deleting template {name}: {e}")
    return False
