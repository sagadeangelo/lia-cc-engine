import sys
from pathlib import Path

# Add root to sys.path so env_config can be found
root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.append(str(root))

try:
    from env_config import *
except ImportError:
    # Fallback if things are messy
    pass
