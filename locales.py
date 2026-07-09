import os
import json

CONFIG_DIR = os.path.expanduser(r"~\.file_organizer")

DEFAULT_EN = {
    "app_title": "File Organizer",
    "watermark": "Developed by Migi Gustian",
    "target_folder": "Target Folder:",
    "browse": "Select Folder",
    "simulate": "Simulate (dry-run)",
    "run": "Run",
    "stop": "Stop",
    "undo": "Undo",
    "group": "Group",
    "filter": "Filter",
    "settings": "Settings",
    "name_group_folder": "Enter name for grouped folder:",
    "message_select_valid_folder_title": "Warning",
    "message_select_valid_folder": "Please select a valid target folder.",
    "output_folder_naming": "Output Folder Naming",
    "append_date": "Append date to folder name",
    "templates": "Templates",
    "save_as": "Save As\u2026",
    "delete": "Delete",
    "open_folder": "Open Folder\u2026",
    "folder_types_title": "Folder Types (double-click to toggle [regex])",
    "filename_regex_filter": "Filename Regex Filter",
    "apply_regex": "Apply Regex",
    "load_from_file": "Load from File\u2026",
    "generate_regex_title": "Generate regex from file name",
    "loaded_message_title": "Loaded",
    "loaded_message_body": "Regex set to:\n{pattern}",
    "language": "Language",
    "info": "Info",
    "restart_to_apply": "Please restart to apply new language.",
    "filter_window_title": "Filter",
    "categories_button": "Categories\u2026",
    "advanced_filters": "Advanced Filters",
    "min_size": "Min size:",
    "max_size": "Max size:",
    "date_from": "Date From:",
    "time_from": "Time From:",
    "date_to": "Date To:",
    "time_to": "Time To:",
    "blacklist": "Blacklist:",
    "scan_subfolders": "Scan Sub\u2011folders",
    "enable_datetime_filter": "Enable Date/Time Filter",
    "enable_size_filter": "Enable Size Filter",
    "apply_and_close": "Apply & Close",
    "select_categories_title": "Select Categories",
    "include_categories": "Include categories:",
    "select_all": "Select All",
    "unselect_all": "Unselect All",
    "done": "Done",
    "message_folder_name_empty_title": "Warning",
    "message_folder_name_empty": "Folder name cannot be empty.",
    "prompt_open_folder_context": "Open Folder",
    "message_box_file_in_use_title": "File In Use",
    "file_in_use": "File '{filename}' is in use.",
    "apply_to_all": "Apply to all",
    "retry": "Retry",
    "skip": "Skip",
    "duplicate": "Duplicate",
    "undo_options_title": "Undo Options",
    "what_to_undo": "What do you want to undo?",
    "undo_last": "Undo Last ({count} files)",
    "undo_group": "Undo Group ({count} folders)",
    "undo_all": "Undo All ({count} actions)",
    "info_nothing_to_undo": "There is nothing to undo.",
    "done_group_move_undone": "Group move undone.",
    "done_last_batch_undone": "Last batch undone.",
    "done_all_batches_undone": "All batches have been successfully undone.",
    "confirm_exit_title": "Confirm Exit",
    "confirm_exit_message": "You have interrupted the file organization and there is undo history available.\n\nIf you exit now, all undo information will be lost,\nand you\u2019ll have to manually move any affected files back if you decide not to continue sorting.\n\nWhat would you like to do?",
    "yes_exit": "Yes(Exit)",
    "return_to_app": "Return to App",
    "undo_all_safe_exit": "Undo All(Safe Exit)",
    "confirm_sure_title": "ARE YOU SURE?",
    "confirm_sure_message": "ARE YOU SURE YOU WANT TO EXIT?\nALL UNDO HISTORY WILL BE LOST!",
    "yes": "YES",
    "no": "NO"
}

DEFAULT_ID = {
    "app_title": "Pengelola Berkas",
    "watermark": "Dikembangkan oleh Migi Gustian",
    "target_folder": "Folder Tujuan:",
    "browse": "Telusuri",
    "simulate": "Uji Coba (dry\u2011run)",
    "run": "Jalankan",
    "stop": "Hentikan",
    "undo": "Undo",
    "group": "Grup",
    "filter": "Filter",
    "settings": "Pengaturan",
    "message_select_valid_folder_title": "Peringatan",
    "message_select_valid_folder": "Silakan pilih folder yang valid.",
    "output_folder_naming": "Penamaan Folder",
    "append_date": "Tambahkan tanggal ke nama folder",
    "templates": "Template",
    "save_as": "Simpan Sebagai\u2026",
    "delete": "Hapus",
    "open_folder": "Buka Folder\u2026",
    "folder_types_title": "Jenis Folder (klik dua kali untuk [regex])",
    "filename_regex_filter": "Filter Regex Nama File",
    "apply_regex": "Terapkan Regex",
    "load_from_file": "Muat dari File\u2026",
    "generate_regex_title": "Buat regex dari nama file",
    "loaded_message_title": "Berhasil Dimuat",
    "loaded_message_body": "Regex diatur menjadi:\n{pattern}",
    "language": "Bahasa",
    "info": "Info",
    "restart_to_apply": "Silakan mulai ulang aplikasi untuk menerapkan bahasa baru.",
    "filter_window_title": "Saring",
    "categories_button": "Kategori\u2026",
    "advanced_filters": "Filter Lanjutan",
    "min_size": "Ukuran Minimal:",
    "max_size": "Ukuran Maksimal:",
    "date_from": "Dari Tanggal:",
    "time_from": "Dari Jam:",
    "date_to": "Hingga Tanggal:",
    "time_to": "Hingga Jam:",
    "blacklist": "Daftar Hitam:",
    "scan_subfolders": "Pindai Subfolder",
    "enable_datetime_filter": "Aktifkan Filter Tanggal/Waktu",
    "enable_size_filter": "Aktifkan Filter Ukuran",
    "apply_and_close": "Terapkan & Tutup",
    "select_categories_title": "Pilih Kategori",
    "include_categories": "Sertakan kategori:",
    "select_all": "Pilih Semua",
    "unselect_all": "Batalkan Semua Pilihan",
    "done": "Selesai",
    "message_folder_name_empty_title": "Peringatan",
    "message_folder_name_empty": "Nama folder tidak boleh kosong.",
    "prompt_open_folder_context": "Buka Folder",
    "message_box_file_in_use_title": "Berkas Sedang Digunakan",
    "file_in_use": "Berkas '{filename}' sedang dipakai.",
    "apply_to_all": "Terapkan ke semua",
    "retry": "Coba Lagi",
    "skip": "Lewati",
    "duplicate": "Duplikat",
    "undo_options_title": "Opsi Batalkan",
    "what_to_undo": "Apa yang ingin Anda batalkan?",
    "undo_last": "Batalkan Terakhir ({count} berkas)",
    "undo_group": "Batalkan Grup ({count} folder)",
    "undo_all": "Batalkan Semua ({count} tindakan)",
    "info_nothing_to_undo": "Tidak ada yang perlu dibatalkan.",
    "done_group_move_undone": "Pengelompokan dibatalkan.",
    "done_last_batch_undone": "Batch terakhir dibatalkan.",
    "done_all_batches_undone": "Semua batch berhasil dibatalkan.",
    "confirm_exit_title": "Konfirmasi Keluar",
    "confirm_exit_message": "Anda menghentikan proses pengaturan berkas dan masih ada riwayat undo. Jika keluar sekarang, riwayat tersebut akan hilang, dan Anda harus memindahkan berkas secara manual jika tidak melanjutkan. Apa yang ingin Anda lakukan?",
    "yes_exit": "Ya, Keluar",
    "return_to_app": "Kembali ke Aplikasi",
    "undo_all_safe_exit": "Batalkan Semua (Keluar Aman)",
    "confirm_sure_title": "Yakin?",
    "confirm_sure_message": "Apakah Anda yakin ingin keluar?\nSemua riwayat undo akan hilang!",
    "yes": "Ya",
    "no": "Tidak"
}

_translations = {}
_current_language = "English"
_callbacks = set()

def load_translations(lang):
    global _translations, _current_language
    _current_language = lang
    
    # Select default first
    default_dict = DEFAULT_EN if lang == "English" else DEFAULT_ID
    
    # Try loading from file
    file_name = "en.json" if lang == "English" else "id.json"
    file_path = os.path.join(CONFIG_DIR, file_name)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_dict = json.load(f)
                _translations = {**default_dict, **file_dict}
                return
        except Exception as e:
            print(f"Error loading translation file {file_path}: {e}")
            
    _translations = default_dict.copy()

def get(key, **kwargs):
    text = _translations.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            pass
    return text

def set_language(lang):
    load_translations(lang)
    for cb in _callbacks:
        try:
            cb()
        except Exception as e:
            print(f"Error in locale callback: {e}")

def register_callback(cb):
    _callbacks.add(cb)

def unregister_callback(cb):
    _callbacks.discard(cb)

# Initialize English by default
load_translations("English")
