import os
import requests
import time
import threading
import hashlib

GITHUB_REPO = "atrballin/DaTraders-Terminal"
# Use contents API to read specific directories
CONTENTS_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"

def compute_git_blob_sha(file_path):
    """
    Computes the SHA-1 hash of a local file EXACTLY how git does it internally.
    Git prepends 'blob <size>\0' to the file content before hashing.
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Git blob header
        header = f"blob {len(data)}\0".encode('utf-8')
        
        hasher = hashlib.sha1()
        hasher.update(header)
        hasher.update(data)
        return hasher.hexdigest()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[Updater] Error computing hash for {file_path}: {e}")
        return None

def sync_github_folder(folder_path):
    """
    Queries GitHub for the contents of a specific folder.
    Compares the remote 'sha' with the local file's git blob sha.
    If different, downloads and overwrites the file.
    """
    print(f"[Updater] Scanning GitHub folder: {folder_path}...")
    headers = {'Accept': 'application/vnd.github.v3+json'}
    
    url = CONTENTS_API + folder_path.replace("\\", "/")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[Updater] Failed to fetch {folder_path} from GitHub. HTTP {response.status_code}")
            return
            
        items = response.json()
        
        # Handle case where path is a file, not a directory
        if not isinstance(items, list):
            items = [items]
            
        for item in items:
            if item.get("type") == "dir":
                # Recursively sync subdirectories
                sync_github_folder(item.get("path"))
            elif item.get("type") == "file":
                remote_sha = item.get("sha")
                download_url = item.get("download_url")
                file_path = item.get("path") # Relative path in the repo (e.g., "src/algo_engine.py")
                
                # Check Local File
                local_sha = compute_git_blob_sha(file_path)
                
                if local_sha != remote_sha:
                    print(f"[Updater] Update found for: {file_path} (Local: {local_sha}, Remote: {remote_sha})")
                    download_and_safe_replace(download_url, file_path)
                else:
                    pass # File is strictly up to date
                    
    except Exception as e:
        print(f"[Updater] Error syncing folder {folder_path}: {e}")

def download_and_safe_replace(url, target_path):
    """
    Downloads a raw file from GitHub.
    Safely handles overlapping writes by renaming locked files (like active .pyd extensions)
    to .old before laying down the new file.
    """
    try:
        # Ensure target directory exists
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        
        print(f"[Updater] Downloading {target_path}...")
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.content
            
            try:
                # Try a direct write first
                with open(target_path, "wb") as f:
                    f.write(data)
                print(f"[Updater] Replaced: {target_path}")
            except PermissionError:
                # File is locked by Windows (likely a loaded .pyd or .exe)
                print(f"[Updater] {target_path} is currently locked. Staging update via rename.")
                old_path = target_path + ".old"
                
                # Clean up previous .old if it exists from a past update
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception as e:
                        print(f"[Updater] Warning: Could not remove old file {old_path}: {e}")
                
                # Rename current locked file
                os.rename(target_path, old_path)
                
                # Write new file in place of the old name
                with open(target_path, "wb") as f:
                    f.write(data)
                print(f"[Updater] Successfully staged {target_path}. Restart required to take effect.")
        else:
            print(f"[Updater] Failed to download {target_path}. HTTP {r.status_code}")
            
    except Exception as e:
        print(f"[Updater] Download/Replace error for {target_path}: {e}")

def check_and_apply_updates():
    """Background task to scan the src and gui folders continuously."""
    folders_to_sync = ["src", "gui"]
    
    while True:
        print(f"[Updater] Starting background sync check at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        for folder in folders_to_sync:
            sync_github_folder(folder)
            
        print("[Updater] Sync cycle complete. Sleeping for 1.5 hours...")
        time.sleep(5400) # Check every 1.5 hours

def start_updater_bg():
    thread = threading.Thread(target=check_and_apply_updates, daemon=True)
    thread.start()
