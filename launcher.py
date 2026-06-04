import os
import subprocess
import sys
import webbrowser
import threading
import time
# import tkinter as tk  # Moved inside functions to avoid startup failure if missing
# from tkinter import messagebox, simpledialog

# Configuration
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(REPO_ROOT, ".env")
ENV_EXAMPLE = os.path.join(REPO_ROOT, ".env.example")
REQUIREMENTS_FILE = os.path.join(REPO_ROOT, "requirements.txt")
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8080

def check_requirements():
    print("Checking and installing Python requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE])
        print("Requirements installed successfully.")
    except Exception as e:
        print(f"Error installing requirements: {e}")

def check_ollama():
    print("Checking Ollama status...")
    try:
        # Check if ollama is installed
        subprocess.check_output(["ollama", "--version"], stderr=subprocess.STDOUT)
        print("Ollama is installed.")
        
        # Pull the model
        print("Pulling mistral-nemo model... this may take a while depending on your internet connection.")
        subprocess.check_call(["ollama", "pull", "mistral-nemo"])
        print("Model mistral-nemo is ready.")
    except FileNotFoundError:
        print("\n" + "!"*40)
        print("Ollama is not installed.")
        print("Please download it from https://ollama.com and install it.")
        print("!"*40 + "\n")
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("Ollama Missing", "Ollama is not installed. Please download it from https://ollama.com and install it before running this application.")
        except Exception:
            pass
            
        webbrowser.open("https://ollama.com")
        sys.exit(1)
    except Exception as e:
        print(f"Error checking/pulling Ollama: {e}")

def setup_api_key():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            content = f.read()
            if "GOOGLE_API_KEY=" in content and len(content.split("GOOGLE_API_KEY=")[1].strip().split('\n')[0]) > 0:
                print("Gemini API Key found in .env.")
                return

    # If not found or empty, ask user
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
        print("Tkinter not available. Falling back to terminal input.")
        api_key = input("Please enter your Gemini API Key: ").strip()

    if api_key:
        # Create .env from example if it doesn't exist
        if not os.path.exists(ENV_FILE):
            if os.path.exists(ENV_EXAMPLE):
                with open(ENV_EXAMPLE, "r") as f:
                    content = f.read()
            else:
                content = "GOOGLE_API_KEY=\n"
        else:
            with open(ENV_FILE, "r") as f:
                content = f.read()

        # Update API Key
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
        messagebox.showerror("Error", "Gemini API Key is required to run the application.")
        sys.exit(1)

def start_backend():
    print("Starting backend server...")
    os.environ["PYTHONPATH"] = REPO_ROOT
    cmd = [sys.executable, "-m", "uvicorn", "backend.api:app", "--host", BACKEND_HOST, "--port", str(BACKEND_PORT)]
    subprocess.Popen(cmd, cwd=REPO_ROOT)

def open_frontend():
    print("Opening frontend in browser...")
    time.sleep(2) # Give the backend a moment to start
    frontend_path = os.path.join(REPO_ROOT, "frontend", "index.html")
    webbrowser.open(f"file://{frontend_path}")

def main():
    check_requirements()
    # check_ollama() # Optional: Uncomment if Ollama is mandatory for the user
    setup_api_key()
    
    backend_thread = threading.Thread(target=start_backend)
    backend_thread.daemon = True
    backend_thread.start()
    
    open_frontend()
    
    print("\nApplication is running!")
    print(f"Backend: http://{BACKEND_HOST}:{BACKEND_PORT}")
    print("Press Ctrl+C in this terminal to stop the application.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping application...")

if __name__ == "__main__":
    main()
