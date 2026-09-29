"""Point Paddle's library discovery at the frozen bundle, not user Python."""
import site
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # PyInstaller disables user site packages and leaves USER_SITE as None.
    # Paddle 2.x joins this value unconditionally when seeking paddle/libs.
    # This does not enable user site imports; the path is inside this bundle.
    site.USER_SITE = sys._MEIPASS
