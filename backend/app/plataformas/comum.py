"""Coisas compartilhadas entre as plataformas: log, exceções, legendas (.txt ao lado do vídeo)."""
from datetime import datetime
from pathlib import Path

from ..config import config

LOGS = config.logs

TAGS = "#gta6 #gtavi #gta #rockstargames #vicecity #gta6trailer #gameplay #gamer #viral #fyp #shorts #gaming"
TITULO_PADRAO = "GTA 6 tá chegando e ninguém tá pronto 😱"

JSON_MODE = False  # quando True, log() nao imprime (a CLI devolve JSON / usa rich no fim)


class NaoLogado(Exception):
    pass


class LimiteDiario(Exception):
    """A plataforma recusou novos envios hoje (ex.: YouTube sem verificacao do canal)."""


def passo(progresso, msg):
    """Avisa a UI (CLI/web) sobre a etapa atual, se alguem estiver ouvindo."""
    if progresso:
        progresso(msg)


def log(msg, plataforma="geral"):
    linha = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [{plataforma}] {msg}"
    if not JSON_MODE:
        print(linha, flush=True)
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / "postar.log", "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def ler_txt(video: Path) -> tuple[str | None, str | None]:
    """(titulo, tags) do .txt ao lado do vídeo, ou (None, None)."""
    txt = video.with_suffix(".txt")
    if not txt.exists():
        return None, None
    linhas = [linha.strip() for linha in txt.read_text("utf-8").splitlines() if linha.strip()]
    sem_tag = [linha for linha in linhas if not linha.startswith("#")]
    com_tag = [linha for linha in linhas if linha.startswith("#")]
    return (sem_tag[0] if sem_tag else None), (" ".join(com_tag) if com_tag else None)


def escrever_txt(video: Path, titulo: str, tags: str):
    video.with_suffix(".txt").write_text(f"{titulo.strip()}\n\n{tags.strip()}\n", "utf-8")


def textos(video: Path) -> tuple[str, str]:
    """(titulo, tags) a partir do .txt do video."""
    titulo, tags = ler_txt(video)
    return titulo or TITULO_PADRAO, tags or TAGS
