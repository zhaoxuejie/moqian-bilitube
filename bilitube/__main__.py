"""包入口：支持 python -m bilitube。"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
