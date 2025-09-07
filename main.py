#!/usr/bin/env python3
"""ComBadge - Natural Language to API Converter

Entry point for the ComBadge application.
"""

import sys
from pathlib import Path

# Adding src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    """Main entry point for ComBadge application."""
    try:
        from combadge import ComBadgeApp, GUI_AVAILABLE, GUI_ERROR
        
        if not GUI_AVAILABLE:
            print("❌ ComBadge GUI is not available:")
            print(f"   Error: {GUI_ERROR}")
            print()
            
            if "libtk8.6.so" in GUI_ERROR:
                print("🔧 To fix this issue:")
                print("   - Ubuntu/Debian: sudo apt-get install python3-tk")
                print("   - Fedora: sudo dnf install python3-tkinter")
                print("   - Arch/Manjaro: sudo pacman -S tk")
                print("   - macOS: Reinstall Python with Tkinter support")
                print("   - Windows: Tkinter should be included")
            else:
                print("🔧 Please check your Python installation and dependencies")
            
            print()
            print("💡 For guided setup, run: python launch_combadge.py")
            sys.exit(1)
        
        app = ComBadgeApp()
        app.run()
        
    except ImportError as e:
        print(f"❌ Failed to import ComBadge: {e}")
        print("💡 Try running: python launch_combadge.py for detailed checks")
        sys.exit(1)


if __name__ == "__main__":
    main()