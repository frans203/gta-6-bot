"""Atalho: python baixar.py --qtd N (código em backend/app/servicos/pack.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.servicos.pack import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
