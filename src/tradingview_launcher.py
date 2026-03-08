import subprocess
import os
import platform

def launch_tradingview():
    """
    Launches the TradingView Desktop application using the protocol handler or common paths.
    """
    try:
        if platform.system() == "Windows":
            # 1. Try protocol handler (most reliable for UWP/Store apps)
            # This is non-blocking and uses the default system registration
            os.startfile("tradingview:")
            return True, "TradingView launched successfully via protocol."
        else:
            return False, "Unsupported operating system."
    except Exception as e:
        return False, f"Failed to launch TradingView: {str(e)}"
