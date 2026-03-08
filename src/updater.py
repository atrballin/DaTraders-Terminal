import os
import requests
import zipfile
import shutil
import threading
import time
from datetime import datetime

VERSION_FILE = "version.txt"
GITHUB_REPO = "atrballin/DaTraders-Terminal"
UPDATE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def get_current_version():
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r") as f:
                return f.read().strip().replace('v', '')
        except: pass
    return "2.3.2"

def check_and_apply_updates():
    """Background task to check for updates via GitHub Releases."""
    try:
        current_version = get_current_version()
        print(f"[Updater] Checking GitHub for updates. Current version: {current_version}")
        
        headers = {'Accept': 'application/vnd.github.v3+json'}
        response = requests.get(UPDATE_URL, headers=headers, timeout=15)
        
        if response.status_code == 200:
            update_data = response.json()
            new_version_tag = update_data.get("tag_name", "0.0.0")
            new_version = new_version_tag.replace('v', '')
            
            print(f"[Updater] Latest version on GitHub: {new_version_tag}")
            
            # Simple version comparison
            if new_version > current_version:
                print(f"[Updater] New version detected! Preparing to patch...")
                # Look for 'patch.zip' in assets
                assets = update_data.get("assets", [])
                patch_asset = next((a for a in assets if "patch" in a.get("name", "").lower()), None)
                
                if patch_asset:
                    download_url = patch_asset.get("browser_download_url")
                    download_and_patch(download_url)
                    # Update local version file after successful patch staging
                    with open(VERSION_FILE, "w") as f:
                        f.write(new_version_tag)
                else:
                    print("[Updater] No 'patch.zip' found in latest release assets.")
            else:
                print("[Updater] App is up to date.")
        else:
            print(f"[Updater] GitHub API returned status: {response.status_code}")
        
    except Exception as e:
        print(f"[Updater] Update check failed: {e}")

def download_and_patch(url):
    """Downloads a zip patch and extracts it into the app directory."""
    temp_zip = "update_temp.zip"
    try:
        print(f"[Updater] Downloading update from {url}...")
        r = requests.get(url, stream=True)
        with open(temp_zip, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("[Updater] Applying patch...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            # We must be careful not to overwrite files currently in use
            # DLLs (.pyd) might be locked. We might need to stage them.
            for file_info in zip_ref.infolist():
                filename = file_info.filename
                if filename.endswith(".pyd"):
                    # Stage DLL update
                    staged_name = filename + ".new"
                    with zip_ref.open(filename) as source, open(staged_name, "wb") as target:
                        shutil.copyfileobj(source, target)
                    print(f"[Updater] Staged DLL update: {staged_name}")
                else:
                    zip_ref.extract(file_info, ".")
        
        print("[Updater] Update applied successfully. Changes will take effect on restart.")
        os.remove(temp_zip)
    except Exception as e:
        print(f"[Updater] Failed to apply update: {e}")
        if os.path.exists(temp_zip):
            os.remove(temp_zip)

def start_updater_bg():
    thread = threading.Thread(target=check_and_apply_updates, daemon=True)
    thread.start()
