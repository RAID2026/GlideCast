import os
import subprocess
import sys

def build():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(app_dir, "glidecast.py")
    icon_path = os.path.join(app_dir, "glidecast.ico")
    
    print("=== GlideCast Installer Build Automation ===")
    
    # Verify icon exists
    if not os.path.exists(icon_path):
        print(f"Error: Icon not found at {icon_path}")
        sys.exit(1)
        
    print(f"Found icon at: {icon_path}")
    print("Running PyInstaller to compile GlideCast...")
    
    # Construct PyInstaller command
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        f"--icon={icon_path}",
        f"--add-data={icon_path};.",
        f"--add-data={os.path.join(app_dir, 'bin')};bin",
        "--name=GlideCast",
        "--collect-all=customtkinter",
        "--clean",
        script_path
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    # Run the build process
    result = subprocess.run(cmd, cwd=app_dir)
    
    if result.returncode == 0:
        print("\n=== BUILD SUCCESSFUL ===")
        print(f"Your compiled app is available at: {os.path.join(app_dir, 'dist', 'GlideCast.exe')}")
    else:
        print("\n=== BUILD FAILED ===")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()
