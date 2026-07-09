import os
import json
import locales
import config
from ui.main_window import MainWindow

def setup_lang_files():
    # Write en.json and id.json into user's config dir if they do not exist
    os.makedirs(config.CONFIG_DIR, exist_ok=True)
    
    en_path = os.path.join(config.CONFIG_DIR, "en.json")
    if not os.path.exists(en_path):
        try:
            with open(en_path, "w", encoding="utf-8") as f:
                json.dump(locales.DEFAULT_EN, f, indent=4)
        except Exception as e:
            print(f"Failed to create default en.json: {e}")
            
    id_path = os.path.join(config.CONFIG_DIR, "id.json")
    if not os.path.exists(id_path):
        try:
            with open(id_path, "w", encoding="utf-8") as f:
                json.dump(locales.DEFAULT_ID, f, indent=4)
        except Exception as e:
            print(f"Failed to create default id.json: {e}")

def main():
    # Setup configuration directories and template folder
    config.ensure_config_dir()
    
    # Pre-populate translation files if missing
    setup_lang_files()
    
    # Initialize and run MainWindow
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
