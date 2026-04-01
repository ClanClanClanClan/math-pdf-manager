"""
Audit test configuration.

The project has mixed import styles:
  - Some modules use: from core.xxx import yyy (requires src/ on path)
  - Some modules use: from core.xxx import yyy (requires src/../ on path)

We add BOTH to sys.path so all imports resolve.
This is itself an AUDIT FINDING: mixed import styles are a maintenance hazard.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"

# Add both src/ AND its parent so both import styles work
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
