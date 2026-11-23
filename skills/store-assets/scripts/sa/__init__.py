"""store-assets rendering package. Importing it checks the runtime first, so a missing
dependency prints one actionable line instead of a traceback."""

import sys

if sys.version_info < (3, 9):
    sys.exit(f"store-assets needs Python 3.9+, found {sys.version.split()[0]}")
try:
    import PIL
except ImportError:
    sys.exit("store-assets needs Pillow 10.1+. Install it with: python3 -m pip install pillow")
if tuple(int(x) for x in PIL.__version__.split(".")[:2]) < (10, 1):
    sys.exit(f"store-assets needs Pillow 10.1+, found {PIL.__version__}. Upgrade: python3 -m pip install -U pillow")
