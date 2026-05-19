#desktop_agent.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J.A.R.V.I.S. Desktop Agent Launcher
Runs Flask backend + displays in native desktop window using pywebview.
"""

import sys
import os
import time
import threading
import subprocess
from pathlib import Path

# Check dependencies
try:
    import webview
except ImportError:
    print("[ERROR] pywebview not installed.")
    print("Run: pip install pywebview")
    sys.exit(1)

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
FLASK_SCRIPT = BASE_DIR / "app.py"
DATA_FOLDER = BASE_DIR / "data"

# ── Start Flask Server ─────────────────────────────────────────────────────────
def start_flask():
    """Launch Flask app as a subprocess."""
    print("[System] Starting Flask neural core...")

    # On Windows we need to use python executable
    python_exe = sys.executable

    # Environment variables
    env = os.environ.copy()
    env["DATA_FOLDER"] = str(DATA_FOLDER)

    try:
        proc = subprocess.Popen(
            [python_exe, str(FLASK_SCRIPT)],
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )

        # Wait for Flask to be ready (max 30 sec)
        start = time.time()
        ready = False
        while time.time() - start < 30:
            if proc.poll() is not None:
                print(f"[Error] Flask exited with code {proc.returncode}")
                break
            try:
                import urllib.request
                urllib.request.urlopen("http://localhost:5000", timeout=1)
                ready = True
                break
            except:
                time.sleep(1)

        if not ready:
            print("[Error] Flask failed to start")
            return None

        print("[System] Neural core online at http://localhost:5000")
        return proc

    except Exception as e:
        print(f"[Error] Failed to start Flask: {e}")
        return None

# ── PyWebView Window ──────────────────────────────────────────────────────────
class JarvisAPI:
    """Bridge between Python backend and JS frontend."""
    def __init__(self, flask_proc):
        self.flask_proc = flask_proc

    def get_version(self):
        return "1.0.0"

    def quit(self):
        """Close the entire application."""
        if self.flask_proc:
            self.flask_proc.terminate()
        try:
            # Try to destroy the GUI window if available
            if hasattr(webview, 'windows') and getattr(webview, 'windows'):
                try:
                    webview.windows[0].destroy()
                except Exception:
                    pass
        except Exception:
            pass

    def open_data_folder(self):
        """Open data folder in file explorer."""
        os.startfile(str(DATA_FOLDER)) if os.name == 'nt' else os.system(f'xdg-open "{DATA_FOLDER}"')

def main():
    print("=" * 50)
    print("   J.A.R.V.I.S. Desktop Agent")
    print("=" * 50)

    # Start Flask in background
    flask_proc = start_flask()
    if not flask_proc:
        input("\nPress Enter to exit...")
        return

    # Create window
    window_args = {
        'title': 'J.A.R.V.I.S. Excel Agent',
        'url': 'http://localhost:5000',
        'width': 1400,
        'height': 900,
        'resizable': True,
        'fullscreen': False,
        'frameless': False,       # Set True for borderless HUD look
        'transparent': False,     # Set True for transparent background
        'always_on_top': False,   # Set True for desktop widget mode
        'min_size': (1200, 700),
        'on_top': False,          # Deprecated, use always_on_top
        'easy_drag': False,
        'shadow': True,
        'dark_theme': True,
    }

    api = JarvisAPI(flask_proc)

    try:
        window = webview.create_window(**window_args, js_api=api)
        print("[System] Interface window created")
        print("[System] Use Ctrl+C to quit\n")

        # Start the GUI event loop
        webview.start(debug=False, http_server=False)

    except KeyboardInterrupt:
        print("\n[System] Shutting down...")
    finally:
        if flask_proc:
            flask_proc.terminate()
            flask_proc.wait(timeout=5)

if __name__ == '__main__':
    main()
