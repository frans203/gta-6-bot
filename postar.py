"""Atalho: python postar.py ... (usado pelas tarefas do Agendador do Windows; código em backend/app/cli/postar.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.cli.postar import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
