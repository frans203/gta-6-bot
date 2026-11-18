"""Coisas compartilhadas entre as plataformas: log, exceções, textos do post.

Textos de um vídeo (ao lado do mp4):
  <video>.txt        título (1ª linha) + hashtags (linhas com #). Formato antigo; o pack e os cortes escrevem só ele.
  <video>.meta.json  {descricao, redes: {youtube: {titulo, descricao}, tiktok: {legenda}, instagram: {legenda}}}
                     escrito pela tela Fila; o que estiver vazio usa o texto geral.
"""
import json
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


# ------------------------------------------------------------------ textos por rede

REDES_TEXTO = ("youtube", "tiktok", "instagram")
LIMITES = {"youtube_titulo": 100, "youtube_descricao": 5000, "tiktok": 2200, "instagram": 2200,
           "instagram_hashtags": 30}


def caminho_meta(video: Path) -> Path:
    return video.with_name(video.stem + ".meta.json")


def ler_meta(video: Path) -> dict:
    """Textos do vídeo: {titulo, descricao, tags, redes} (.txt + .meta.json)."""
    titulo, tags = ler_txt(video)
    extra = {}
    p = caminho_meta(video)
    if p.exists():
        try:
            extra = json.loads(p.read_text("utf-8"))
        except ValueError:
            extra = {}
    redes = {r: {k: v for k, v in (extra.get("redes") or {}).get(r, {}).items() if v} for r in REDES_TEXTO}
    return {"titulo": titulo or "", "descricao": extra.get("descricao") or "", "tags": tags or "",
            "redes": {r: v for r, v in redes.items() if v}}


def escrever_meta(video: Path, meta: dict):
    """Grava título e hashtags no .txt (compatível com o resto) e descrição/personalizações no .meta.json."""
    escrever_txt(video, meta.get("titulo") or TITULO_PADRAO, meta.get("tags") or "")
    redes = {r: {k: v.strip() for k, v in (meta.get("redes") or {}).get(r, {}).items() if v and v.strip()}
             for r in REDES_TEXTO}
    dados = {"descricao": (meta.get("descricao") or "").strip(), "redes": {r: v for r, v in redes.items() if v}}
    p = caminho_meta(video)
    if not dados["descricao"] and not dados["redes"]:
        p.unlink(missing_ok=True)
        return
    novo = p.with_suffix(".novo")
    novo.write_text(json.dumps(dados, ensure_ascii=False, indent=1), "utf-8")
    novo.replace(p)


def _linha(texto: str) -> str:
    """Uma linha só: o robô digita o texto e um Enter fecharia/escolheria sugestões nas redes."""
    return " ".join(texto.split())


def juntar(*partes: str) -> str:
    return _linha(" ".join(p for p in partes if p and p.strip()))


def titulo_youtube_padrao(titulo: str, tags: str) -> str:
    extra = "#gta6 #shorts" if "#gta6" in tags.lower() else "#shorts"
    t = f"{titulo} {extra}"
    return t if len(t) <= 99 else titulo[:99]


def textos_rede(video: Path, rede: str) -> dict:
    """Texto final de uma rede: youtube -> {titulo, descricao}; tiktok/instagram -> {legenda}.
    Personalização da rede (se houver) > texto geral (título + descrição + hashtags)."""
    m = ler_meta(video)
    titulo, tags = m["titulo"] or TITULO_PADRAO, m["tags"] or TAGS
    o = m["redes"].get(rede, {})
    if rede == "youtube":
        return {"titulo": _linha(o.get("titulo") or titulo_youtube_padrao(titulo, tags))[:LIMITES["youtube_titulo"]],
                "descricao": juntar(o.get("descricao") or juntar(m["descricao"] or titulo, tags))[:LIMITES["youtube_descricao"]]}
    return {"legenda": _linha(o.get("legenda") or juntar(titulo, m["descricao"], tags))[:LIMITES.get(rede, 2200)]}
