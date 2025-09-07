# Development Patches and Workarounds

This document tracks temporary patches and workarounds implemented during development to resolve compatibility and stability issues.

## Active Patches

### 1. CustomTkinter Scaling Tracker Fix (Python 3.13 Compatibility)

**Issue**: CustomTkinter 5.2.2 has a bug with Python 3.13 where `window.state()` returns a dict instead of being callable, causing `TypeError: 'dict' object is not callable`.

**Location**: `src/combadge/core/application.py` lines 11-28

**Patch**:
```python
# Monkey patch to fix 'dict' object not callable error
from customtkinter.windows.widgets.scaling import scaling_tracker
original_check_dpi_scaling = scaling_tracker.ScalingTracker.check_dpi_scaling

def patched_check_dpi_scaling(self):
    try:
        return original_check_dpi_scaling(self)
    except (TypeError, AttributeError) as e:
        # Silently ignore scaling tracker errors
        pass

scaling_tracker.ScalingTracker.check_dpi_scaling = patched_check_dpi_scaling
```

**Status**: Active workaround
**Resolution**: Update CustomTkinter when Python 3.13 compatibility is officially supported

### 2. Setup Wizard Threading Bypass

**Issue**: Setup wizard causes "RuntimeError: main thread is not in main loop" due to GUI updates from background threads.

**Location**: `src/combadge/core/application.py` lines 76-82

**Patch**:
```python
# Temporarily bypass setup wizard due to threading issues
self.logger.info("Bypassing setup wizard (temporary fix for threading issues)")

# Proceed directly to initialize components  
self.setup_complete = True
self._initialize_ollama()
self.main_window.deiconify()  # Show main window
```

**Status**: Temporary workaround
**Resolution**: Fix threading issues in setup wizard by properly using `self.after()` for all GUI updates

## Fixed Issues (No Longer Active)

### Thread-Safe GUI Updates in Setup Wizard

**Issue**: Setup wizard tried to update GUI elements directly from background threads.

**Files Fixed**:
- `src/combadge/ui/setup_wizard.py`: Added proper `self.after()` scheduling

**Resolution**: Updated `update_section_status()` to use main thread scheduling:
```python
def update_section_status(self, section_tuple, status: str, progress: Optional[float] = None):
    # Schedule GUI update on main thread
    self.after(0, self._update_section_status_impl, section_tuple, status, progress)
```

## Development Guidelines

### Adding New Patches

1. Document the exact issue and error message
2. Include the affected files and line numbers
3. Provide the complete patch code
4. Mark as temporary or permanent
5. Include resolution plans

### Removing Patches

1. Test thoroughly to ensure the underlying issue is resolved
2. Remove the patch code
3. Update this document to move the issue to "Fixed Issues"
4. Verify no other code depends on the patch

## Testing Notes

- All patches should be tested on the target Python version (3.13)
- GUI patches should be tested with window operations (minimize, resize, close)
- Threading patches should be tested with concurrent operations

## Code Refactoring (Fleet Management → Generic NLP to API)

**Issue**: ComBadge was originally designed with fleet management specific terminology and should be a generic NLP to API converter.

**Changes Made**:
- **Main Window**: Changed title from "Fleet Management Assistant" to "NLP to API Converter"
- **Intent Classification**: Renamed `FleetIntent` → `APIIntent`, updated all fleet-specific intents
- **Module Structure**: Renamed `src/combadge/fleet/` → `src/combadge/processors/`
- **File Renames**: `vehicle_validator.py` → `resource_validator.py`
- **Class Renames**: `VehicleValidator` → `ResourceValidator`, `FleetIntent` → `APIIntent`
- **Pattern Updates**: Updated regex patterns from vehicle-specific to generic resource patterns
- **Configuration**: Changed API base URL from fleet-api.company.com to api.company.com

**Status**: Completed - ComBadge is now a generic NLP to API converter
**Files Modified**: 20+ files updated across UI, intelligence, and processing modules

### 3. Model Download Progress UI

**Issue**: Users had no feedback when Ollama models were being downloaded in background, making app appear frozen.

**Changes Made**:
- **Progress Callback**: Connected `OllamaServerManager.on_download_progress` to UI updates
- **Status Messages**: Added real-time download progress with MB counts and percentages
- **User Feedback**: Clear status progression from "Preparing AI model" → "Downloading" → "Processing"

**Status**: Active - Provides real-time feedback for model downloads
**Files Modified**: `src/combadge/core/application.py`

## Future Improvements

1. **CustomTkinter Version**: Monitor for Python 3.13 compatible release
2. **Setup Wizard**: Redesign threading model to eliminate race conditions
3. **Error Handling**: Implement more robust error handling for GUI operations
4. **Testing**: Add automated tests for patched functionality
5. **Complete Fleet Removal**: Continue removing any remaining fleet-specific terminology

---
*Last Updated: 2025-09-07*
*Development Phase: Launch Error Fixes*