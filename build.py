import os
import subprocess
import shutil
import sys

def main():
    print("Starting build process...")
    
    # 1. Clean previous builds
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Failed to clean {folder}: {e}")
            
    # 2. Build Unpacked Version (onedir)
    print("\n--- Building Unpacked Version (onedir) ---")
    onedir_cmd = [
        "python", "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=Files Organizer",
        "--add-data=assets;assets",
        "--icon=assets/organize_files.ico",
        "--collect-all", "tkinterdnd2",
        "main.py"
    ]
    subprocess.run(onedir_cmd, check=True)
    print("Unpacked version built successfully at dist/Files Organizer")
    
    # 3. Compile Inno Setup Installer
    iscc_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if os.path.exists(iscc_path):
        print("\n--- Compiling Inno Setup Installer ---")
        iss_cmd = [iscc_path, "setup.iss"]
        subprocess.run(iss_cmd, check=True)
        print("Installer Setup built successfully at dist/FilesOrganizer_Setup.exe")
    else:
        print("\n[WARNING] Inno Setup compiler not found at expected location. Skipping installer compilation.")
        
    # 4. Build Single-File Exe (onefile)
    print("\n--- Building Single-File Exe (onefile) ---")
    onefile_cmd = [
        "python", "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name=Files Organizer_Single",
        "--add-data=assets;assets",
        "--icon=assets/organize_files.ico",
        "--collect-all", "tkinterdnd2",
        "main.py"
    ]
    subprocess.run(onefile_cmd, check=True)
    print("Single-file exe built successfully at dist/Files Organizer_Single.exe")
    
    print("\nBuild process completed!")

if __name__ == "__main__":
    main()
