"""Plugins de plataforma. Para adicionar uma rede nova, crie um módulo com a mesma interface
(veja `Plataforma`) e registre em PLATAFORMAS."""
from datetime import datetime
from pathlib import Path
from typing import Protocol

from . import instagram, tiktok, youtube


class Plataforma(Protocol):
    NOME: str
    LOGIN_URL: str
    AGENDA_NATIVA: bool   # True = a própria rede agenda; False = Agendador do Windows

    def postar(self, page, video: Path, revisar: bool = False, quando: datetime | None = None,
               progresso=None) -> dict: ...


PLATAFORMAS: dict[str, Plataforma] = {m.NOME: m for m in (tiktok, youtube, instagram)}
