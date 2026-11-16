"""Conexão com o SQLite. Vários processos usam o banco ao mesmo tempo (API, worker, tarefas do Windows),
por isso WAL + busy_timeout."""
import contextlib
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .config import config

BACKEND = Path(__file__).resolve().parents[1]

_engine = None
_Sessao = None


def engine():
    global _engine, _Sessao
    if _engine is None:
        config.dados.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{config.banco}", connect_args={"timeout": 30, "check_same_thread": False})

        @event.listens_for(_engine, "connect")
        def _pragmas(conn, _):
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        _Sessao = sessionmaker(_engine, expire_on_commit=False)
    return _engine


@contextlib.contextmanager
def sessao() -> Iterator[Session]:
    engine()
    s = _Sessao()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def migrar():
    """Aplica as migrações do Alembic (cria o banco na 1ª vez)."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    cfg = AlembicConfig(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{config.banco}")
    cfg.attributes["configure_logger"] = False
    config.dados.mkdir(parents=True, exist_ok=True)
    command.upgrade(cfg, "head")


_pronto = False


def preparar():
    """Migra + cria a conta padrão + importa o postados.json antigo (só uma vez por processo)."""
    global _pronto
    if _pronto:
        return
    migrar()
    from .servicos import importar
    importar.inicial()
    _pronto = True
