"""Coisas compartilhadas entre as plataformas: caminhos, log, historico, legendas."""
import json
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LIMPOS = RAIZ / "limpos"
PERFIL = RAIZ / "perfil-chrome"
LOGS = RAIZ / "logs"
HIST = RAIZ / "postados.json"

TAGS = "#gta6 #gtavi #gta #rockstargames #vicecity #gta6trailer #gameplay #gamer #viral #fyp #shorts #gaming"
TITULO_PADRAO = "GTA 6 tá chegando e ninguém tá pronto 😱"

JSON_MODE = False  # quando True, log() nao imprime (a CLI devolve JSON no fim)


class NaoLogado(Exception):
    pass


class LimiteDiario(Exception):
    """A plataforma recusou novos envios hoje (ex.: YouTube sem verificacao do canal)."""


def passo(progresso, msg):
    """Avisa a UI (CLI/React) sobre a etapa atual, se alguem estiver ouvindo."""
    if progresso:
        progresso(msg)


def log(msg, plataforma="geral"):
    linha = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [{plataforma}] {msg}"
    if not JSON_MODE:
        print(linha, flush=True)
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / "postar.log", "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def carregar_hist() -> dict:
    """{ "gta6_002.mp4": { "tiktok": {...}, "youtube": {...} } }"""
    return json.loads(HIST.read_text("utf-8-sig")) if HIST.exists() else {}


def salvar_hist(h: dict):
    HIST.write_text(json.dumps(h, indent=1, ensure_ascii=False), "utf-8")


def registrar(video: Path, plataforma: str, resultado: dict):
    h = carregar_hist()
    h.setdefault(video.name, {})[plataforma] = {"em": datetime.now().isoformat(timespec="seconds"), **resultado}
    salvar_hist(h)


def textos(video: Path) -> tuple[str, str]:
    """(titulo, tags) a partir do .txt do video."""
    txt = video.with_suffix(".txt")
    titulo, tags = TITULO_PADRAO, TAGS
    if txt.exists():
        linhas = [l.strip() for l in txt.read_text("utf-8").splitlines() if l.strip()]
        sem_tag = [l for l in linhas if not l.startswith("#")]
        com_tag = [l for l in linhas if l.startswith("#")]
        if sem_tag:
            titulo = sem_tag[0]
        if com_tag:
            tags = " ".join(com_tag)
    return titulo, tags
