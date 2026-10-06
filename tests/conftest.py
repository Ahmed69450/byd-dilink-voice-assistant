import sys
from pathlib import Path

# Add android/app/src/main/python to sys.path so tests can import modules
python_dir = Path(__file__).resolve().parent.parent / "android" / "app" / "src" / "main" / "python"
if str(python_dir) not in sys.path:
    sys.path.insert(0, str(python_dir))
