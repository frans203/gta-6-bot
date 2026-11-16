"""Atalho: python jason.py ... (o código fica em backend/app/cli/jason.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.cli.jason import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
