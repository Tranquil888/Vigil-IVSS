"""PyInstaller entry point. Kept separate because the spec needs a script path."""

from vigil.app import main

if __name__ == "__main__":
    raise SystemExit(main())
