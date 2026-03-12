import os
import sys
import subprocess
import requests
import time
import threading
import hashlib

GITHUB_REPO = "atrballin/DaTraders-Terminal"
# Use contents API to read specific directories
CONTENTS_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"

# Target installation directory for updates
INSTALL_DIR = r"C:\Program Files\DaTradersTerminal\_internal"

# ──────────────────────────────────────────────────────────────────
#  Premium Update Progress UI (Tkinter Overlay)
# ──────────────────────────────────────────────────────────────────

class UpdateProgressUI:
    """
    A small, premium-looking overlay window that displays
    update progress to the user. Matches the DaTraders dark theme.
    """
    # Theme constants (from styles.py)
    BG_MAIN    = "#121212"
    BG_PANE    = "#1A1C23"
    BG_HEADER  = "#1E2129"
    BORDER     = "#2D323E"
    TEXT       = "#FAFAFA"
    TEXT_DIM   = "#8A8F9E"
    ACCENT     = "#4B91F7"
    ACCENT_GLOW = "#3B7AD9"
    SUCCESS    = "#00E676"

    def __init__(self):
        self.root = None
        self.canvas = None
        self.status_label = None
        self.file_label = None
        self.progress_val = 0.0
        self.total_files = 0
        self.completed_files = 0
        self._thread = None
        self._ready = threading.Event()

    def show(self, total_files=1):
        """Launch the progress window on a dedicated UI thread."""
        self.total_files = max(total_files, 1)
        self.completed_files = 0
        self.progress_val = 0.0
        self._ready.clear()
        self._thread = threading.Thread(target=self._run_ui, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3) # Wait for UI to be ready

    def _run_ui(self):
        """Creates and runs the tkinter window."""
        try:
            import tkinter as tk
        except ImportError:
            print("[Updater] tkinter not available - skipping progress UI")
            self._ready.set()
            return

        self.root = tk.Tk()
        self.root.title("DaTraders Terminal — Updating")
        self.root.overrideredirect(True)  # Borderless window
        self.root.attributes("-topmost", True)
        self.root.configure(bg=self.BG_MAIN)

        # Window size and centering
        w, h = 420, 180
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Subtle border effect via a frame
        border_frame = tk.Frame(self.root, bg=self.BORDER, padx=1, pady=1)
        border_frame.pack(fill="both", expand=True)

        inner = tk.Frame(border_frame, bg=self.BG_PANE)
        inner.pack(fill="both", expand=True)

        # ─── Header ───
        header = tk.Frame(inner, bg=self.BG_HEADER, height=44)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Accent bar at the very top (2px gradient feel)
        accent_bar = tk.Frame(header, bg=self.ACCENT, height=2)
        accent_bar.pack(fill="x", side="top")

        title_label = tk.Label(
            header, text="⬇  Updating DaTraders Terminal",
            bg=self.BG_HEADER, fg=self.TEXT,
            font=("Segoe UI Semibold", 11),
            anchor="w", padx=14
        )
        title_label.pack(fill="both", expand=True)

        # ─── Body ───
        body = tk.Frame(inner, bg=self.BG_PANE, padx=20, pady=12)
        body.pack(fill="both", expand=True)

        # Status text
        self.status_label = tk.Label(
            body, text="Checking for updates…",
            bg=self.BG_PANE, fg=self.TEXT,
            font=("Segoe UI", 10), anchor="w"
        )
        self.status_label.pack(fill="x", pady=(0, 4))

        # File name being updated
        self.file_label = tk.Label(
            body, text="",
            bg=self.BG_PANE, fg=self.TEXT_DIM,
            font=("Segoe UI", 8), anchor="w"
        )
        self.file_label.pack(fill="x", pady=(0, 8))

        # ─── Custom Progress Bar (Canvas) ───
        bar_frame = tk.Frame(body, bg=self.BG_MAIN, height=8)
        bar_frame.pack(fill="x", pady=(0, 6))

        self.canvas = tk.Canvas(
            bar_frame, height=8, bg=self.BG_MAIN,
            highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="x")

        # Draw background track (rounded)
        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width() or 376
        self.canvas.create_rectangle(
            0, 0, cw, 8,
            fill=self.BORDER, outline="", width=0
        )
        # Progress fill (will be updated)
        self._bar_id = self.canvas.create_rectangle(
            0, 0, 0, 8,
            fill=self.ACCENT, outline="", width=0
        )

        # Percentage label
        self.pct_label = tk.Label(
            body, text="0%",
            bg=self.BG_PANE, fg=self.TEXT_DIM,
            font=("Segoe UI", 8), anchor="e"
        )
        self.pct_label.pack(fill="x")

        self._ready.set()
        self.root.mainloop()

    def update_progress(self, filename=""):
        """Call from the updater thread to advance progress by one file."""
        self.completed_files += 1
        self.progress_val = min(self.completed_files / self.total_files, 1.0)

        if self.root and self.canvas:
            try:
                self.root.after(0, self._refresh_ui, filename)
            except Exception:
                pass

    def _refresh_ui(self, filename):
        """Runs on the tkinter thread to update all widgets."""
        try:
            pct = int(self.progress_val * 100)

            # Update labels
            self.status_label.config(
                text=f"Installing updates… ({self.completed_files}/{self.total_files})"
            )
            self.file_label.config(text=filename)
            self.pct_label.config(text=f"{pct}%")

            # Update progress bar
            self.canvas.update_idletasks()
            cw = self.canvas.winfo_width() or 376
            fill_w = int(cw * self.progress_val)
            self.canvas.coords(self._bar_id, 0, 0, fill_w, 8)

            # At 100%, change bar to green
            if pct >= 100:
                self.canvas.itemconfig(self._bar_id, fill=self.SUCCESS)
                self.status_label.config(text="Update complete! Restarting…")
                self.file_label.config(text="")
                self.pct_label.config(text="100%", fg=self.SUCCESS)
        except Exception:
            pass

    def close(self):
        """Safely destroy the progress window."""
        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass
            self.root = None


# ──────────────────────────────────────────────────────────────────
#  Core Updater Logic
# ──────────────────────────────────────────────────────────────────

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

def _collect_outdated_files(folder_path):
    """
    Pre-scan: Recursively collects all files that need updating.
    Returns a list of (download_url, local_path, repo_path) tuples.
    """
    headers = {'Accept': 'application/vnd.github.v3+json'}
    url = CONTENTS_API + folder_path.replace("\\", "/")
    outdated = []

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[Updater] Failed to fetch {folder_path} from GitHub. HTTP {response.status_code}")
            return outdated

        items = response.json()
        if not isinstance(items, list):
            items = [items]

        for item in items:
            if item.get("type") == "dir":
                outdated.extend(_collect_outdated_files(item.get("path")))
            elif item.get("type") == "file":
                remote_sha = item.get("sha")
                download_url = item.get("download_url")
                repo_path = item.get("path")
                local_path = os.path.join(INSTALL_DIR, repo_path)
                local_sha = compute_git_blob_sha(local_path)

                if local_sha != remote_sha:
                    outdated.append((download_url, local_path, repo_path))

    except Exception as e:
        print(f"[Updater] Error scanning folder {folder_path}: {e}")

    return outdated

def download_and_safe_replace(url, target_path):
    """
    Downloads a raw file from GitHub.
    Safely handles overlapping writes by renaming locked files (like active .pyd extensions)
    to .old before laying down the new file.
    """
    try:
        # Ensure target directory exists
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        
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

def restart_app():
    """
    Restarts the application after updates have been applied.
    Launches the installed exe and exits the current process.
    """
    exe_path = os.path.join(INSTALL_DIR, "..", "DaTradersTerminal.exe")
    exe_path = os.path.normpath(exe_path)
    
    if os.path.exists(exe_path):
        print(f"[Updater] Restarting application: {exe_path}")
        try:
            # Launch a new process detached from the current one
            subprocess.Popen(
                [exe_path],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
            print("[Updater] New process launched. Exiting current process...")
            time.sleep(1) # Brief delay to ensure new process starts
            os._exit(0)   # Hard exit to release all file locks
        except Exception as e:
            print(f"[Updater] Restart failed: {e}. Manual restart required.")
    else:
        print(f"[Updater] Exe not found at {exe_path}. Manual restart required.")


# ──────────────────────────────────────────────────────────────────
#  Main Sync Loop
# ──────────────────────────────────────────────────────────────────

def check_and_apply_updates():
    """Background task to scan the src and gui folders continuously."""
    folders_to_sync = ["src", "gui"]
    
    while True:
        print(f"[Updater] Starting background sync check at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[Updater] Target install directory: {INSTALL_DIR}")
        
        # Phase 1: Pre-scan to count total outdated files
        all_outdated = []
        for folder in folders_to_sync:
            all_outdated.extend(_collect_outdated_files(folder))

        if all_outdated:
            print(f"[Updater] Found {len(all_outdated)} file(s) to update.")
            
            # Phase 2: Show Progress UI
            ui = UpdateProgressUI()
            ui.show(total_files=len(all_outdated))
            time.sleep(0.5) # Let the window render

            # Phase 3: Download & replace each file with progress
            for download_url, local_path, repo_path in all_outdated:
                print(f"[Updater] Updating: {repo_path}")
                download_and_safe_replace(download_url, local_path)
                ui.update_progress(filename=repo_path)
                time.sleep(0.15) # Brief pause for visual feedback

            # Phase 4: Show completion for a moment, then restart
            time.sleep(2)
            ui.close()
            
            print("[Updater] Updates applied. Restarting application...")
            restart_app()
        else:
            print("[Updater] No updates found. Sleeping for 1.5 hours...")
            
        time.sleep(5400) # Check every 1.5 hours

def start_updater_bg():
    thread = threading.Thread(target=check_and_apply_updates, daemon=True)
    thread.start()
