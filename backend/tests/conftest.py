"""Cada teste roda com banco e mídia temporários (nunca toca no banco real)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    from app import db
    from app.config import config
    monkeypatch.setattr(config, "dados", tmp_path / "dados")
    monkeypatch.setattr(config, "midia", tmp_path / "midia")
    monkeypatch.setattr(config, "logs", tmp_path / "logs")
    config.__dict__.pop("banco", None)
    config.__dict__.pop("modelos", None)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_Sessao", None)
    monkeypatch.setattr(db, "_pronto", False)
    from app.servicos import importar
    monkeypatch.setattr(importar, "POSTADOS", tmp_path / "nao_existe.json")
    db.preparar()
    yield tmp_path
    config.__dict__.pop("banco", None)
    config.__dict__.pop("modelos", None)
