"""Contas (conjuntos de perfis nas redes). Cada conta tem a própria pasta de vídeos e o próprio perfil do Chrome."""
import re
from pathlib import Path

from sqlalchemy import select

from ..config import config
from ..db import sessao
from ..models import Conta

PADRAO = "gta6"
TAGS_PT = "#gameplay #gamer #viral #fyp #shorts #gaming #cortes #twitch"
TAGS_EN = "#gaming #gamer #twitch #clips #funny #viral #fyp #shorts #streamer"


def listar() -> list[Conta]:
    with sessao() as s:
        return list(s.scalars(select(Conta).order_by(Conta.padrao.desc(), Conta.id)))


def obter(conta_id: str | None = None) -> Conta:
    with sessao() as s:
        c = s.get(Conta, conta_id) if conta_id else s.scalar(select(Conta).where(Conta.padrao))
        if c is None:
            raise KeyError(f"conta desconhecida: {conta_id}")
        return c


def criar(id: str, nome: str, idioma: str = "pt", plataformas: list[str] | None = None,
          tags: str | None = None, pasta: str | None = None, perfil: str | None = None) -> Conta:
    if not re.fullmatch(r"[a-z0-9_]{2,40}", id):
        raise ValueError("id da conta: só letras minúsculas, números e _ (2 a 40)")
    c = Conta(
        id=id, nome=nome, idioma=idioma,
        plataformas=plataformas or ["tiktok", "youtube", "instagram"],
        tags=tags if tags is not None else (TAGS_EN if idioma == "en" else TAGS_PT),
        pasta=pasta or str(config.midia / "contas" / id / "videos"),
        perfil=perfil or str(config.midia / "contas" / id / "perfil-chrome"),
    )
    with sessao() as s:
        if s.get(Conta, id):
            raise ValueError(f"já existe a conta {id}")
        s.add(c)
    pasta_videos(c).mkdir(parents=True, exist_ok=True)
    return c


def atualizar(conta_id: str, **campos) -> Conta:
    with sessao() as s:
        c = s.get(Conta, conta_id)
        if c is None:
            raise KeyError(conta_id)
        for k, v in campos.items():
            if v is not None and k in ("nome", "idioma", "plataformas", "tags"):
                setattr(c, k, v)
        return c


def pasta_videos(c: Conta) -> Path:
    return config.caminho(c.pasta)


def perfil(c: Conta) -> Path:
    return config.caminho(c.perfil)


def arquivo_trava(c: Conta) -> Path:
    # a conta original mantém o nome antigo da trava (as tarefas do Windows já criadas dependem dele)
    return config.logs / ("perfil-chrome.lock" if c.padrao else f"perfil-{c.id}.lock")


def videos(c: Conta) -> list[Path]:
    p = pasta_videos(c)
    return sorted(p.glob("*.mp4")) if p.exists() else []
