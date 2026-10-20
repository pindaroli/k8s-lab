import os
import sys

# Add parent directory of src so src can be imported as a package (e.g. from src import main)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
