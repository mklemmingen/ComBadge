#!/usr/bin/env python3
"""ComBadge - Natural Language to API Converter

Entry point for the ComBadge application.
"""

import sys
from pathlib import Path

# Adding src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from combadge.core.application import ComBadgeApp


def main():
    """Main entry point for ComBadge application."""
    app = ComBadgeApp()
    app.run()


if __name__ == "__main__":
    main()