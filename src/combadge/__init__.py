"""ComBadge - Natural Language to API Converter

A local desktop application that converts natural language emails and commands 
into structured API calls.
"""

__version__ = "0.1.0"
__author__ = "ComBadge Team"
__description__ = "Natural Language to API Converter"

# Conditional import to handle missing GUI libraries
try:
    from .core.application import ComBadgeApp
    GUI_AVAILABLE = True
    GUI_ERROR = None
except ImportError as e:
    GUI_AVAILABLE = False
    GUI_ERROR = str(e)
    ComBadgeApp = None

__all__ = ["ComBadgeApp", "GUI_AVAILABLE", "GUI_ERROR"]