import os
import sys
import subprocess
import threading
import time
import webbrowser
import streamlit.web.cli as stcli

# CRITICAL FIX: Force Playwright to use the global Windows AppData folder 
# instead of the read-only packaged _internal directory.
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

def install_playwright_if_needed():
    """Silently installs the Chromium browser to the user's AppData folder on the first run."""
    print("[SYSTEM] Verifying Wolfgang browser engine...")
    try:
        from playwright._impl._driver import compute_driver_executable, get_driver_env
        driver_info = compute_driver_executable()
        
        # Grab the environment and enforce the AppData path for the installation subprocess
        env = get_driver_env()
        env["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        
        # Safely construct the command
        if isinstance(driver_info, tuple):
            cmd = [driver_info[0], driver_info[1], 'install', 'chromium']
        else:
            cmd = [driver_info, 'install', 'chromium']
            
        # Run the installation
        subprocess.check_call(cmd, env=env)
    except Exception as e:
        print(f"[WARNING] Playwright setup check: {e}")

def open_browser():
    """Waits for Streamlit to boot, then opens the dashboard."""
    time.sleep(4)
    webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    # 1. Install browser if missing
    install_playwright_if_needed()
    
    # 2. Identify where the .exe is currently running
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    app_path = os.path.join(base_path, "app2.py")
    
    # 3. Trick Windows into running Streamlit internally
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.port=8501",
        "--server.headless=true", 
        "--global.developmentMode=false",
        "--theme.base=dark"  # NEW: Force Dark Mode
    ]
    
    # 4. Launch the browser in a background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # 5. Boot Streamlit
    sys.exit(stcli.main())