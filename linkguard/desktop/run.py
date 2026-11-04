import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ('shared', 'desktop'):
    sys.path.insert(0, str(ROOT / sub))

from linkguard.cli import main

if __name__ == '__main__':
    sys.exit(main())
