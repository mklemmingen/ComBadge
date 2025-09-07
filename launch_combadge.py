#!/usr/bin/env python3
"""
ComBadge Launch Wrapper
Checks system requirements and provides helpful error messages before launching.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_tkinter():
    """Check if Tkinter is available."""
    try:
        import tkinter
        return True, "Tkinter is available"
    except ImportError as e:
        if "libtk8.6.so" in str(e):
            return False, """
Tkinter Error: Missing system library 'libtk8.6.so'

To fix this issue:
- On Ubuntu/Debian: sudo apt-get install python3-tk
- On Fedora: sudo dnf install python3-tkinter
- On Arch/Manjaro: sudo pacman -S tk
- On macOS: Tkinter should be included with Python
- On Windows: Tkinter should be included with Python

After installing, try running ComBadge again.
"""
        else:
            return False, f"Tkinter import error: {e}"

def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        return False, f"Python 3.9+ required, found {version.major}.{version.minor}.{version.micro}"
    return True, f"Python {version.major}.{version.minor}.{version.micro}"

def check_virtual_env():
    """Check if we're in the correct virtual environment."""
    venv = os.environ.get('VIRTUAL_ENV')
    if venv and 'combadge' in venv.lower():
        return True, f"Virtual environment: {Path(venv).name}"
    else:
        # Check if venv exists in current directory
        venv_path = Path(__file__).parent / "venv"
        if venv_path.exists():
            return False, f"""
Virtual environment not activated!

Please activate it first:
- Linux/macOS: source venv/bin/activate
- Windows: venv\\Scripts\\activate

Then run: python launch_combadge.py
"""
        return True, "No virtual environment (using system Python)"

def check_dependencies():
    """Check required Python packages."""
    required = [
        'customtkinter',
        'requests',
        'yaml',
        'psutil',
        'aiohttp',
        'pydantic'
    ]
    
    missing = []
    for package in required:
        try:
            if package == 'yaml':
                __import__('yaml')
            else:
                __import__(package)
        except ImportError:
            missing.append(package if package != 'yaml' else 'pyyaml')
    
    if missing:
        return False, f"""
Missing Python packages: {', '.join(missing)}

To install:
pip install -r requirements/base.txt

Or individually:
pip install {' '.join(missing)}
"""
    return True, "All Python dependencies installed"

def check_ollama():
    """Check if Ollama is available."""
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            
            # Check if service is running
            import requests
            try:
                resp = requests.get("http://localhost:11434/api/version", timeout=2)
                if resp.status_code == 200:
                    return True, f"Ollama {version} (service running)"
                else:
                    return True, f"Ollama {version} (service not running - will start automatically)"
            except:
                return True, f"Ollama {version} (service not running - will start automatically)"
                
    except FileNotFoundError:
        return True, "Ollama not installed (setup wizard will handle this)"
    except Exception as e:
        return True, f"Ollama check skipped: {e}"
        
    return True, "Ollama status unknown"

def main():
    """Main launch sequence."""
    print("ComBadge Pre-Launch Checks")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_env),
        ("Tkinter (GUI Library)", check_tkinter),
        ("Python Dependencies", check_dependencies),
        ("Ollama Installation", check_ollama)
    ]
    
    all_passed = True
    critical_errors = []
    
    for name, check_func in checks:
        passed, message = check_func()
        status = "✓" if passed else "✗"
        print(f"{status} {name}: {message.strip()}")
        
        if not passed:
            all_passed = False
            if name in ["Tkinter (GUI Library)", "Python Version"]:
                critical_errors.append((name, message))
    
    print("=" * 50)
    
    if critical_errors:
        print("\n❌ Critical errors found:\n")
        for name, message in critical_errors:
            print(f"{name}:{message}")
        print("\nPlease fix these issues before launching ComBadge.")
        sys.exit(1)
    
    if not all_passed:
        print("\n⚠️  Some checks failed, but ComBadge may still run.")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)
    else:
        print("\n✅ All checks passed!")
    
    # Launch ComBadge
    print("\n🚀 Launching ComBadge...\n")
    
    # Add src to path if needed
    src_path = Path(__file__).parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    try:
        # Import and run the application
        from combadge.core.application import ComBadgeApp
        app = ComBadgeApp()
        app.run()
    except Exception as e:
        print(f"\n❌ Error launching ComBadge: {e}")
        print("\nFor more details, check logs/combadge.log")
        sys.exit(1)

if __name__ == "__main__":
    main()