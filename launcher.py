import os
import subprocess
import sys
import webbrowser
import threading
import time

# Configuration
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(REPO_ROOT, ".env")
ENV_EXAMPLE = os.path.join(REPO_ROOT, ".env.example")
REQUIREMENTS_FILE = os.path.join(REPO_ROOT, "requirements.txt")
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8080
VENV_DIR = os.path.join(REPO_ROOT, ".venv")

def get_venv_python():
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")

def ensure_venv():
    """Ensure the script is running inside a virtual environment."""
    if sys.prefix != sys.base_prefix:
        print("Running inside virtual environment.")
        return True

    print("Virtual environment not detected. Setting up...")
    if not os.path.exists(VENV_DIR):
        print(f"Creating virtual environment in {VENV_DIR}...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])

    venv_python = get_venv_python()
    print(f"Restarting launcher within virtual environment: {venv_python}")
    
    # Restart the script using the venv python
    try:
        subprocess.run([venv_python, os.path.abspath(__file__)] + sys.argv[1:])
        sys.exit(0)
    except Exception as e:
        print(f"Error restarting in venv: {e}")
        sys.exit(1)

def check_requirements():
    print("Checking and installing Python requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE])
        print("Requirements installed successfully.")
    except Exception as e:
        print(f"Error installing requirements: {e}")

def check_ollama():
    print("Checking Ollama status...")
    try:
        subprocess.check_output(["ollama", "--version"], stderr=subprocess.STDOUT)
        print("Ollama is installed.")
        
        # Pull the model
        print("Checking/Pulling mistral-nemo model... this may take a moment.")
        subprocess.check_call(["ollama", "pull", "mistral-nemo"])
        print("Model mistral-nemo is ready.")
    except FileNotFoundError:
        print("\n" + "!"*40)
        print("Ollama is not installed.")
        print("!"*40 + "\n")
        
        if sys.platform == "win32":
            print("Downloading Ollama installer for Windows...")
            webbrowser.open("https://ollama.com/download/OllamaSetup.exe")
        else:
            print("To install Ollama on Linux/macOS, run:")
            print("curl -fsSL https://ollama.com/install.sh | sh")
            webbrowser.open("https://ollama.com/download")
            
        print("\nPlease install Ollama and run this launcher again.")
        sys.exit(1)
    except Exception as e:
        print(f"Note: Could not verify/pull model automatically ({e}). Ensure Ollama is running.")

def setup_api_key():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            content = f.read()
            if "GOOGLE_API_KEY=" in content and len(content.split("GOOGLE_API_KEY=")[1].strip().split('\n')[0]) > 0:
                print("Gemini API Key found in .env.")
                return

    print("\n" + "="*40)
    print("Gemini API Key missing.")
    print("="*40)
    
    api_key = None
    try:
        import tkinter as tk
        from tkinter import simpledialog, messagebox
        root = tk.Tk()
        root.withdraw()
        api_key = simpledialog.askstring("Gemini API Key", "Please enter your Gemini API Key:", show='*')
    except Exception:
        print("Notice: Tkinter interface not available. Using terminal.")
        api_key = input("Please enter your Gemini API Key: ").strip()

    if api_key:
        if not os.path.exists(ENV_FILE):
            if os.path.exists(ENV_EXAMPLE):
                with open(ENV_EXAMPLE, "r") as f:
                    content = f.read()
            else:
                content = "GOOGLE_API_KEY=\n"
        else:
            with open(ENV_FILE, "r") as f:
                content = f.read()

        if "GOOGLE_API_KEY=" in content:
            new_lines = []
            for line in content.splitlines():
                if line.startswith("GOOGLE_API_KEY="):
                    new_lines.append(f"GOOGLE_API_KEY={api_key}")
                else:
                    new_lines.append(line)
            content = "\n".join(new_lines)
        else:
            content += f"\nGOOGLE_API_KEY={api_key}\n"

        with open(ENV_FILE, "w") as f:
            f.write(content)
        print("API Key saved to .env.")
    else:
        print("Error: Gemini API Key is required.")
        sys.exit(1)

def start_backend():
    print("Starting backend server...")
    os.environ["PYTHONPATH"] = REPO_ROOT
    # Ensure uvicorn is used from the current python (venv)
    cmd = [sys.executable, "-m", "uvicorn", "backend.api:app", "--host", BACKEND_HOST, "--port", str(BACKEND_PORT)]
    subprocess.Popen(cmd, cwd=REPO_ROOT)

def open_frontend():
    print("Opening frontend in browser...")
    time.sleep(3) # Wait for backend
    frontend_path = os.path.join(REPO_ROOT, "frontend", "index.html")
    # Using http://localhost:8080 might be better if the frontend is served, 
    # but here it is a static file that likely connects to 127.0.0.1:8080
    webbrowser.open(f"file://{frontend_path}")

def main():
    if ensure_venv():
        check_requirements()
        check_ollama()
        setup_api_key()
        
        backend_thread = threading.Thread(target=start_backend)
        backend_thread.daemon = True
        backend_thread.start()
        
        open_frontend()
        
        print("\n" + "="*40)
        print("Application is running!")
        print(f"Backend: http://{BACKEND_HOST}:{BACKEND_PORT}")
        print("="*40)
        print("\nKeep this terminal open while using the app.")
        print("Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping application...")

if __name__ == "__main__":
    main()
