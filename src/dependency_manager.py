import os
import sys
import subprocess
import winreg
import platform

def is_python_version_ok():
    """Verify if running Python is 3.11+."""
    return sys.version_info.major == 3 and sys.version_info.minor >= 11

def is_mt5_installed():
    """Check for MetaTrader 5 via Registry and common paths."""
    # 1. Check Registry
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\MetaQuotes\MetaTrader\5")
        winreg.CloseKey(key)
        return True
    except WindowsError:
        pass
    
    # 2. Check Common Paths
    common_paths = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        rf"{os.environ.get('APPDATA')}\MetaQuotes\Terminal\MT5\terminal64.exe"
    ]
    for path in common_paths:
        if os.path.exists(path):
            return True
            
    return False

def is_tradingview_installed():
    """Check for TradingView Desktop via Protocol registration."""
    try:
        # Check if the protocol handler 'tradingview:' exists in registry
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"tradingview")
        winreg.CloseKey(key)
        return True
    except WindowsError:
        pass
    
    # Fallback to common install path (UWP or Standard)
    tv_path = rf"{os.environ.get('LOCALAPPDATA')}\Programs\TradingView Desktop\TradingView.exe"
    if os.path.exists(tv_path):
        return True
        
    return False

def get_missing_dependencies():
    """Returns a list of missing dependency objects."""
    missing = []
    
    if not is_python_version_ok():
        missing.append({
            "id": "python",
            "name": "Python 3.11+",
            "description": "Required for application engine and AI logic.",
            "winget_id": "Python.Python.3.11"
        })
        
    if not is_mt5_installed():
        missing.append({
            "id": "mt5",
            "name": "MetaTrader 5",
            "description": "Required for trade execution and data fetching.",
            "url": "https://www.metatrader5.com/en/download"
        })
        
    if not is_tradingview_installed():
        missing.append({
            "id": "tradingview",
            "name": "TradingView Desktop",
            "description": "Required for official TradingView chart integration.",
            "winget_id": "TradingView.TradingView"
        })
        
    return missing

def install_via_winget(winget_id):
    """Attempt to install a package via Windows winget using PowerShell."""
    try:
        # Construct the PowerShell command string
        # --accept-source-agreements --accept-package-agreements for silent/unattended
        ps_command = f"winget install --id {winget_id} --silent --accept-source-agreements --accept-package-agreements"
        
        # Explicitly call powershell.exe
        cmd = ["powershell", "-Command", ps_command]
        
        # Start detached so it doesn't block the UI
        subprocess.Popen(cmd, shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE)
        return True
    except Exception as e:
        return False
