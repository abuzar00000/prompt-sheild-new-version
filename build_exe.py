import subprocess
import sys
import os

# Configuration
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(REPO_ROOT, ".venv")

def get_venv_python():
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")

def build():
    # Ensure we are in venv
    if sys.prefix == sys.base_prefix:
        print("Please run this script using the venv python or after running launcher.py")
        if os.path.exists(VENV_DIR):
            venv_python = get_venv_python()
            print(f"Switching to venv: {venv_python}")
            subprocess.run([venv_python, os.path.abspath(__file__)] + sys.argv[1:])
            sys.exit(0)
        else:
            print("Virtual environment not found. Please run launcher.py first.")
            sys.exit(1)

    print("Installing PyInstaller within venv...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print("Building executable...")
    separator = ";" if sys.platform == "win32" else ":"
    
    cmd = [
        "pyinstaller",
        "--onefile",
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
