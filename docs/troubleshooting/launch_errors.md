# ComBadge Launch Error Fixes

This document describes common errors encountered when launching ComBadge and their solutions.

## Error #1: Tkinter Library Missing

### Error Message
```
ImportError: libtk8.6.so: cannot open shared object file: No such file or directory
```

### Cause
The system is missing the Tk GUI library that Python's Tkinter module requires.

### Solution by Platform

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install python3-tk
```

#### Fedora/CentOS/RHEL
```bash
sudo dnf install python3-tkinter
# Or on older versions:
sudo yum install tkinter
```

#### Arch Linux/Manjaro
```bash
sudo pacman -S tk
```

#### macOS
```bash
# Using Homebrew
brew install python-tk

# Or reinstall Python with tkinter support
brew reinstall python@3.11
```

#### Windows
Tkinter should be included with standard Python installations. If missing:
1. Reinstall Python from python.org
2. Ensure "tcl/tk and IDLE" is checked during installation

### Verification
After installation, test with:
```bash
python -c "import tkinter; print('Tkinter is available')"
```

## Error #2: Python Version Too Old

### Error Message
```
Python 3.9+ required, found 3.8.x
```

### Solution
1. **Install newer Python version**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install python3.11
   
   # Fedora
   sudo dnf install python3.11
   
   # Arch/Manjaro
   sudo pacman -S python311
   
   # macOS
   brew install python@3.11
   ```

2. **Update virtual environment**:
   ```bash
   # Remove old venv
   rm -rf venv
   
   # Create new venv with newer Python
   python3.11 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   
   # Reinstall dependencies
   pip install -r requirements/base.txt
   ```

## Error #3: Missing Python Dependencies

### Error Message
```
Missing Python packages: customtkinter, requests, yaml
```

### Solution
```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install missing packages
pip install -r requirements/base.txt

# Or install individually
pip install customtkinter requests pyyaml psutil aiohttp pydantic
```

## Error #4: Virtual Environment Not Activated

### Error Message
```
Virtual environment not activated!
```

### Solution
```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

# Verify activation (should show (venv) in prompt)
which python  # Should point to venv/bin/python
```

## Error #5: Permission Denied

### Error Message
```
PermissionError: [Errno 13] Permission denied
```

### Common Causes and Solutions

1. **Log directory permissions**:
   ```bash
   mkdir -p logs
   chmod 755 logs
   ```

2. **Config file permissions**:
   ```bash
   chmod 644 config/*.yaml
   ```

3. **Running as wrong user**:
   ```bash
   # Don't run as root unless necessary
   # Use your regular user account
   ```

## Error #6: Port Already in Use (Ollama)

### Error Message
```
OSError: [Errno 98] Address already in use: localhost:11434
```

### Solution
```bash
# Check what's using port 11434
lsof -i :11434

# If it's another Ollama instance, stop it
pkill -f ollama

# Or use different port in config
# Edit config/default_config.yaml:
# llm:
#   base_url: "http://localhost:11435"
```

## Error #7: Display Not Available (Headless System)

### Error Message
```
_tkinter.TclError: no display name and no $DISPLAY environment variable
```

### Solution
This error occurs when running on a server without a graphical interface.

1. **Use X11 forwarding** (SSH):
   ```bash
   ssh -X username@hostname
   ```

2. **Use virtual display**:
   ```bash
   # Install Xvfb
   sudo apt-get install xvfb
   
   # Run with virtual display
   xvfb-run -a python main.py
   ```

3. **Use headless mode** (future feature):
   ```bash
   # This will be supported in future versions
   python main.py --headless
   ```

## Error #8: Missing Cryptography Module

### Error Message
```
No module named 'cryptography'
```

### Cause
The cryptography package is required for secure credential storage but is not installed.

### Solution
```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install cryptography
pip install cryptography>=41.0.0

# Or install all requirements
pip install -r requirements/base.txt
```

### Verification
After installation, test with:
```bash
python -c "import cryptography; print('Cryptography is available')"
```

## Error #9: Pydantic Regex Parameter Deprecated

### Error Message
```
pydantic.errors.PydanticUserError: `regex` is removed. use `pattern` instead
```

### Cause
Pydantic v2 deprecated the `regex` parameter in Field definitions, replaced with `pattern`.

### Solution
Update all Field definitions in configuration files:
```python
# Old (deprecated)
method: str = Field(default="cookie", regex="^(cookie|token|oauth|api_key)$")

# New (correct)
method: str = Field(default="cookie", pattern="^(cookie|token|oauth|api_key)$")
```

### Files Fixed
- `src/combadge/core/config_manager.py`: Updated all Field regex parameters to pattern

## Error #10: Class Import Name Mismatches

### Error Messages
```
cannot import name 'FleetPromptBuilder' from 'combadge.intelligence.chain_of_thought.prompt_builder'
cannot import name 'ReasoningDisplay' from 'combadge.ui.components.reasoning_display'
cannot import name 'ThemeManager' from 'combadge.ui.styles.themes'
```

### Cause
Import statements reference class names that don't exist in the target files.

### Solution
Update import statements to match actual class names:
- `FleetPromptBuilder` → `APIPromptBuilder`
- `ReasoningDisplay` → `RealtimeReasoningDisplay`  
- `ThemeManager` → `Theme`

### Files Fixed
- `src/combadge/intelligence/chain_of_thought/__init__.py`
- `src/combadge/ui/components/__init__.py`
- `src/combadge/ui/main_window.py`
- `src/combadge/ui/setup_wizard.py`

## Error #11: CustomTkinter Parameter Conflicts

### Error Messages
```
CTkFrame() got multiple values for keyword argument 'corner_radius'
CTkTextbox() got multiple values for keyword argument 'font'
```

### Cause
Widget creation code explicitly sets parameters that are also included in theme style dictionaries.

### Solution
Remove explicit parameters when using theme styles, or override theme values properly:
```python
# Problem
ctk.CTkFrame(self, corner_radius=0, **self.theme.create_frame_style())

# Solution
frame_style = self.theme.create_frame_style()
frame_style["corner_radius"] = 0  # Override theme default
ctk.CTkFrame(self, **frame_style)
```

### Files Fixed
- `src/combadge/ui/main_window.py`: Fixed corner_radius conflicts
- `src/combadge/ui/components/input_panel.py`: Fixed font conflicts

## Error #12: Invalid Color References

### Error Messages
```
'ThemeColors' object has no attribute 'mercedes_blue'
transparency is not allowed for this attribute
```

### Cause
Code references non-existent theme colors and CustomTkinter doesn't allow transparency for certain attributes.

### Solution
- Replace invalid color names with valid theme colors: `mercedes_blue` → `accent_blue`
- Remove transparency values for incompatible attributes like border_color

### Files Fixed
- `src/combadge/ui/main_window.py`: Updated color references
- `src/combadge/ui/components/input_panel.py`: Updated color references  
- `src/combadge/ui/styles/themes.py`: Fixed transparency issues

## Error #13: Missing GUI_ERROR Variable

### Error Message
```
cannot import name 'GUI_ERROR' from 'combadge'
```

### Cause
GUI_ERROR variable only defined when ImportError occurs, but main.py always tries to import it.

### Solution
Define GUI_ERROR in both success and error cases:
```python
try:
    from .core.application import ComBadgeApp
    GUI_AVAILABLE = True
    GUI_ERROR = None  # Always define
except ImportError as e:
    GUI_AVAILABLE = False
    GUI_ERROR = str(e)
    ComBadgeApp = None
```

### Files Fixed
- `src/combadge/__init__.py`: Added GUI_ERROR = None for success case

## Error #14: Ollama Model Not Found

### Error Message
```
Model qwen2.5:14b not found
```

### Solution
```bash
# Manually download model
ollama pull qwen2.5:14b

# Or use smaller model for testing
ollama pull llama2:7b

# Update config to use different model
# Edit config/default_config.yaml:
# llm:
#   model: "llama2:7b"
```

## Diagnostic Tools

### Pre-Launch Checker
```bash
python launch_combadge.py
```
This script checks all requirements and provides specific error messages.

### Core Component Test
```bash
python test_core_only.py
```
Tests non-GUI components without requiring Tkinter.

### Log Analysis
```bash
# Check recent errors
tail -f logs/combadge.log

# Search for specific errors
grep -i error logs/combadge.log
```

## Getting Help

If these solutions don't resolve your issue:

1. **Check logs**: `logs/combadge.log` for detailed error information
2. **Run diagnostics**: `python launch_combadge.py` for guided troubleshooting
3. **Create issue**: Report the problem at https://github.com/mklemmingen/Combadge/issues

Include:
- Your operating system and version
- Python version (`python --version`)
- Full error message
- Contents of `logs/combadge.log`
- Output of `python launch_combadge.py`