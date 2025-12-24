import sys
import os
import threading
import socket
import webview
from fastapi.staticfiles import StaticFiles
from uvicorn import Config, Server

# Add current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from main import app

class Api:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def select_folder(self):
        if not self._window:
            return None
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return result[0]
        return None

def get_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def start_server(port):
    # Determine the base directory
    if getattr(sys, 'frozen', False):
        # Running as compiled PyInstaller executable
        # The frontend build is extracted to a temporary folder indicated by _MEIPASS
        base_dir = sys._MEIPASS
        frontend_build_dir = os.path.join(base_dir, 'frontend', 'build')
    else:
        # Running as a script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_build_dir = os.path.abspath(os.path.join(base_dir, '..', 'frontend', 'build'))
    
    if not os.path.exists(frontend_build_dir):
        print(f"Error: Frontend build directory not found at {frontend_build_dir}")
        sys.exit(1)

    # Remove existing root route if present (to allow frontend index.html to be served at /)
    # Filter out the route with path "/"
    app.router.routes = [route for route in app.router.routes if getattr(route, "path", "") != "/"]

    # Mount static files
    # 'html=True' allows serving index.html when requesting /
    app.mount("/", StaticFiles(directory=frontend_build_dir, html=True), name="static")

    # Configure and run server
    # We use uvicorn directly instead of uvicorn.run to have better control (though run is fine too)
    config = Config(app=app, host="127.0.0.1", port=port, log_level="error")
    server = Server(config)
    server.run()

if __name__ == '__main__':
    port = get_free_port()
    
    # Start server in a separate thread
    t = threading.Thread(target=start_server, args=(port,))
    t.daemon = True
    t.start()

    # Define storage path for persistence (Local Storage, Cookies, etc.)
    storage_path = os.path.join(os.path.expanduser('~'), '.kitsu_publisher_data')
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)

    api = Api()
    # Create and start the webview window
    window = webview.create_window('Kitsu Publisher', f'http://127.0.0.1:{port}', width=1280, height=800, resizable=True, js_api=api)
    api.set_window(window)
    
    # Enable persistence by specifying storage_path and disabling private_mode
    webview.start(private_mode=False, storage_path=storage_path)
