import subprocess
import sys
import os

def build():
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print("Building executable...")
    # --onefile: Create a single executable
    # --noconsole: Hide the terminal window (useful for GUI apps, but we might want it for logging)
    # --add-data: Include essential files (frontend, backend, config, .env.example)
    
    separator = ";" if sys.platform == "win32" else ":"
    
    cmd = [
        "pyinstaller",
        "--onefile",
        # "--noconsole", # Uncomment if you want to hide the terminal
        f"--add-data=frontend{separator}frontend",
        f"--add-data=backend{separator}backend",
        f"--add-data=config{separator}config",
        f"--add-data=.env.example{separator}.",
        "launcher.py"
    ]
    
    subprocess.check_call(cmd)
    print("\nBuild complete! The executable is in the 'dist' folder.")

if __name__ == "__main__":
    build()
