"""Source and PyInstaller entry point; installed packages use atomverse-ai."""
from atomverse.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
