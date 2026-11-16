"""Detectores de destaques (sem IA): cada um devolve uma curva com uma nota por segundo do vídeo (0..1).
A análise soma as curvas com pesos e escolhe os picos. Para criar um detector novo, registre uma função
`f(ctx: Analise) -> np.ndarray | None` com @DETECTORES.registrar."""
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import fontes, midia
from .plugins import DETECTORES


@dataclass
class Analise:
    url: str
    duracao: int                       # segundos
    plataforma: str                    # twitch | youtube
    canal: str
    pasta: Path                        # pasta temporária
    info: dict = field(default_factory=dict)
    progresso: object = None           # callable(fracao, msg)
    log: object = print


def _suavizar(x: np.ndarray, janela: int) -> np.ndarray:
    """Média móvel que repete a borda (sem isso, início e fim do vídeo viram 'picos' falsos)."""
    if len(x) < janela or janela <= 1:
        return x
    meio = janela // 2
    estendido = np.pad(x.astype(float), (meio, janela - 1 - meio), mode="edge")
    return np.convolve(estendido, np.ones(janela) / janela, mode="valid")


def _normalizar(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0, None)
    topo = x.max() if len(x) else 0
    return x / topo if topo > 0 else np.zeros_like(x, dtype=float)


def _ajustar(x: np.ndarray, n: int) -> np.ndarray:
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))


BLOCO_AUDIO = 3 * 3600


@DETECTORES.registrar("audio", "Picos de áudio", "Gritos, risadas, explosões: momentos bem mais altos que o normal "
                      "daquele trecho da live. Funciona em qualquer vídeo.", peso=1.0)
def picos_audio(a: Analise) -> np.ndarray:
    # lives longas (Kai Cenat faz 30h+) são processadas em blocos para não lotar o disco
    bloco = BLOCO_AUDIO if a.duracao > BLOCO_AUDIO * 1.3 else a.duracao
    partes = []
    for n, ini in enumerate(range(0, a.duracao, bloco)):
        fim = min(ini + bloco, a.duracao)
        frac0, frac1 = ini / a.duracao, fim / a.duracao
        prog = (lambda f, m, f0=frac0, f1=frac1: a.progresso and a.progresso(0.05 + (f0 + f * (f1 - f0)) * 0.85, m))
        a.log(f"áudio {ini // 3600:.0f}h–{fim / 3600:.1f}h: baixando (qualidade mínima, só para medir volume)")
        arq = fontes.baixar_audio(a.url, a.pasta / f"audio_{n}", ao_progresso=lambda f, p=prog: p(f * 0.7, "baixando áudio"),
                                  inicio=None if bloco == a.duracao else ini, fim=None if bloco == a.duracao else fim)
        partes.append(_ajustar(midia.energia_por_segundo(arq, lambda f, p=prog: p(0.7 + f * 0.3, "medindo volume"),
                                                         fim - ini), fim - ini))
        arq.unlink(missing_ok=True)
    db = np.concatenate(partes) if partes else np.zeros(0)
    if len(db) < 30:
        return np.zeros(a.duracao)
    # quanto o volume passa da "linha de base" dos últimos ~2 min (a live tem partes calmas e partes agitadas)
    base = _suavizar(db, 121)
    excesso = db - base
    mediana = np.median(excesso)
    mad = np.median(np.abs(excesso - mediana)) * 1.4826 or 1.0
    z = (excesso - mediana) / mad
    # momentos sustentados (vários segundos altos) valem mais que um estalo isolado
    curva = _suavizar(np.clip(z, 0, 8), 5)
    curva[:60] = curva[-60:] = 0  # abertura/encerramento da live (música, tela de "volto já", despedida)
    return _ajustar(_normalizar(curva), a.duracao)


@DETECTORES.registrar("mais_assistidos", "Mais assistidos (YouTube)", "Usa o gráfico de 'partes mais repetidas' "
                      "do YouTube, quando o vídeo tem.", peso=1.5)
def mais_assistidos(a: Analise) -> np.ndarray | None:
    hm = a.info.get("heatmap") or []
    if not hm:
        return None
    x = np.zeros(a.duracao)
    for ponto in hm:
        i, f = int(ponto["start_time"]), int(np.ceil(ponto["end_time"]))
        x[i:f] = ponto["value"]
    # interessa o que se destaca do resto, não o nível geral
    return _normalizar(x - np.median(x))


@DETECTORES.registrar("clipes_twitch", "Clipes da Twitch", "Momentos que os espectadores clipparam durante a live "
                      "(precisa da API oficial da Twitch configurada).", peso=2.0)
def clipes_twitch(a: Analise) -> np.ndarray | None:
    if a.plataforma != "twitch" or not fontes.TwitchAPI.disponivel():
        return None
    m = re.search(r"videos/(\d+)", a.url)
    if not m:
        return None
    clipes = fontes.TwitchAPI.clipes(a.canal, dias=60, limite=100, video_id=m.group(1))
    a.log(f"{len(clipes)} clipe(s) feitos pelos espectadores nesta live")
    if not clipes:
        return None
    x = np.zeros(a.duracao)
    t = np.arange(a.duracao)
    for c in clipes:
        if c.get("vod_offset") is None:
            continue
        centro = c["vod_offset"] + c["duration"] / 2
        x += np.log1p(c["view_count"]) * np.exp(-((t - centro) ** 2) / (2 * 12 ** 2))
    return _normalizar(x)


def combinar(curvas: dict[str, np.ndarray], pesos: dict[str, float]) -> np.ndarray:
    total = sum(pesos[k] for k in curvas) or 1.0
    return sum(curvas[k] * pesos[k] for k in curvas) / total


def escolher_picos(score: np.ndarray, curvas: dict[str, np.ndarray], n: int, duracao: int,
                   antes: float = 0.65, minimo: float = 0.08) -> list[dict]:
    """Os n melhores trechos sem sobreposição. O pico fica a ~65% do corte: dá contexto antes e a reação depois."""
    s = _suavizar(score.astype(float), 3).copy()
    total = len(s)
    out = []
    while len(out) < n:
        i = int(np.argmax(s))
        if s[i] < minimo:
            break
        inicio = max(0, min(int(i - duracao * antes), total - duracao))
        fim = min(total, inicio + duracao)
        out.append({"inicio": float(inicio), "fim": float(fim), "score": round(float(score[i]), 3),
                    "sinais": {k: round(float(c[i]), 3) for k, c in curvas.items()} | {"pico": i}})
        s[max(0, inicio - duracao): fim + duracao] = -1  # nada colado: o próximo fica a 1 corte de distância
    return out
