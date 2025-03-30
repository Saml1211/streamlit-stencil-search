#!/usr/bin/env python3
"""
Build script for creating distributable packages of Visio Stencil Explorer
"""
import os
import shutil
import subprocess
import sys
import platform
import argparse
from pathlib import Path

def build_executable():
    """Build a standalone executable using PyInstaller"""
    try:
        # Ensure PyInstaller is installed
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
        # Define icon path
        icon_path = "app/assets/icon.ico" if platform.system() == "Windows" else "app/assets/icon.icns"
        
        # Create PyInstaller command
        pyinstaller_args = [
            "pyinstaller",
            "--name=VisioStencilExplorer",
            "--onefile",
            "--windowed",
            f"--icon={icon_path}",
            "--add-data=config.yaml:.",
            "--add-data=pages:pages",  # Updated path
            "--hidden-import=yaml",
            "--hidden-import=pandas",
            "--hidden-import=xlsxwriter",
            "app.py"  # Updated entry point
        ]

        # Run PyInstaller
        subprocess.check_call(pyinstaller_args)
        
        print("✅ Executable created successfully in dist/ directory")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error building executable: {e}")
        return False

def build_docker():
    """Build a Docker image"""
    try:
        # Build Docker image
        subprocess.check_call(["docker", "build", "-t", "visio-stencil-explorer:latest", "."])
        
        print("✅ Docker image built successfully")
        print("   Run with: docker run -p 8501:8501 visio-stencil-explorer:latest")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error building Docker image: {e}")
        return False

def create_dockerfile():
    """Create a Dockerfile if it doesn't exist"""
    dockerfile_content = """FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"] # Updated entry point
"""

    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)
    
    print("✅ Created Dockerfile")

def ensure_assets():
    """Ensure assets directory exists with icon"""
    os.makedirs("app/assets", exist_ok=True)
    
    # Create a placeholder icon if none exists
    icon_path = Path("app/assets/icon.ico") if platform.system() == "Windows" else Path("app/assets/icon.icns")
    
    if not icon_path.exists():
        print("⚠️ No icon found. Using a placeholder. Replace with your own icon for production.")
        # Here we would generate or copy a placeholder icon
        # For this example, we'll just create an empty file
        icon_path.touch()

def main():
    """Main build function"""
    parser = argparse.ArgumentParser(description="Build Visio Stencil Explorer")
    parser.add_argument("--exe", action="store_true", help="Build standalone executable")
    parser.add_argument("--docker", action="store_true", help="Build Docker image")
    parser.add_argument("--all", action="store_true", help="Build all package types")
    
    args = parser.parse_args()
    
    # If no options specified, show help
    if not (args.exe or args.docker or args.all):
        parser.print_help()
        return
    
    # Ensure assets directory exists
    ensure_assets()
    
    # Build executable if requested
    if args.exe or args.all:
        print("\n📦 Building executable...")
        build_executable()
    
    # Build Docker image if requested
    if args.docker or args.all:
        print("\n🐳 Building Docker image...")
        create_dockerfile()
        build_docker()
    
    print("\n✨ Build process complete!")

if __name__ == "__main__":
    main() 