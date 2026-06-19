"""PyInstaller entry shim (absolute import so the frozen build resolves cleanly)."""
import sys

from ecoworthy_bms.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
