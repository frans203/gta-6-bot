"""Histórico de posts (o que foi publicado/agendado em cada plataforma). Fonte da verdade: tabela `posts`.
`carregar_hist` devolve o mesmo formato do antigo postados.json para o resto do código não mudar."""
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from ..db import sessao
from ..models import Post

CAMPOS = ("status", "para", "link", "erro", "print", "tarefa", "obs")


def _como_dict(p: Post) -> dict:
    d = {"em": p.em, "status": p.status, **(p.extra or {})}
    for k in CAMPOS[1:]:
        if getattr(p, k) is not None:
            d[k] = getattr(p, k)
    return d


def carregar_hist(conta_id: str) -> dict[str, dict[str, dict]]:
    """{ "gta6_002.mp4": { "tiktok": {"status": ..., "para": ...}, ... } }"""
    h: dict[str, dict[str, dict]] = {}
    with sessao() as s:
        for p in s.scalars(select(Post).where(Post.conta_id == conta_id)):
            h.setdefault(p.video, {})[p.plataforma] = _como_dict(p)
    return h


def _nome(video: Path | str) -> str:
    return video.name if isinstance(video, Path) else Path(video).name


def gravar(s, conta_id: str, video: str, plataforma: str, dados: dict) -> Post:
    p = s.scalar(select(Post).where(Post.conta_id == conta_id, Post.video == video, Post.plataforma == plataforma))
    if p is None:
        p = Post(conta_id=conta_id, video=video, plataforma=plataforma)
        s.add(p)
    p.em = dados.get("em") or datetime.now().isoformat(timespec="seconds")
    for k in CAMPOS:
        v = dados.get(k)
        setattr(p, k, str(v) if v is not None and k != "status" else v)
    p.extra = {k: v for k, v in dados.items() if k not in CAMPOS and k != "em"}
    return p


def registrar(conta_id: str, video: Path | str, plataforma: str, resultado: dict):
    """Substitui o estado do vídeo nessa plataforma (como o antigo postados.json)."""
    with sessao() as s:
        gravar(s, conta_id, _nome(video), plataforma, {"em": datetime.now().isoformat(timespec="seconds"), **resultado})


def status_de(conta_id: str, video: Path | str, plataforma: str) -> str | None:
    with sessao() as s:
        return s.scalar(select(Post.status).where(Post.conta_id == conta_id, Post.video == _nome(video),
                                                  Post.plataforma == plataforma))


def exportar(conta_id: str, destino: Path) -> Path:
    destino.write_text(json.dumps(carregar_hist(conta_id), indent=1, ensure_ascii=False), "utf-8")
    return destino
