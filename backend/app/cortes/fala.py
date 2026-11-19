"""Sinais tirados da FALA da live (transcrição local do Whisper, sem IA paga).

A transcrição do trecho escolhido vira curvas de uma nota por segundo, no tempo da live:
  ritmo     fala bem mais rápida que a média dos ~2 min em volta (empolgação, discussão)
  explosao  fala rápida logo depois de um silêncio (o "NÃO!" depois de um momento tenso)
  gatilho   palavras de choque/gancho (palavras_gancho.json, por idioma) e exclamações
  risada    "kkkk", "hahaha", "[risos]", palavras repetidas ("não não NÃO")
As frases (segmentos do Whisper) também servem para começar/terminar o corte no limite de uma frase e para
sugerir o texto do gancho."""
import json
import re
import unicodedata
from functools import cache
from pathlib import Path

import numpy as np

PESOS = {"ritmo": 0.30, "explosao": 0.20, "gatilho": 0.30, "risada": 0.20}
SILENCIO_EXPLOSAO = 2.0       # s de pausa antes da fala contar como "explosão"
RITMO_EXPLOSAO = 2.8          # palavras/s para contar como explosão
_RISADA = re.compile(r"\b(k{3,}|(?:ha){2,}h?|(?:he){3,}|(?:ja){2,}|(?:rs){2,}|lol|lmao|kek)\b|\[(?:risos?|laughs?|laughter|risas)\]"
                     r"|\((?:risos?|laughs?|laughter|risas)\)", re.I)


def _sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


@cache
def palavras_gancho() -> dict[str, list[str]]:
    """{idioma: [expressões]}. Edite cortes/palavras_gancho.json para mudar as listas."""
    return json.loads((Path(__file__).with_name("palavras_gancho.json")).read_text("utf-8"))


@cache
def _regex_gatilho(idioma: str | None) -> re.Pattern | None:
    lista = palavras_gancho()
    termos = lista.get((idioma or "")[:2], []) + lista.get("todos", [])
    if not termos:
        return None
    termos = sorted({_sem_acento(t) for t in termos}, key=len, reverse=True)
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(t) for t in termos) + r")(?![\w])")


def _z(x: np.ndarray, base: int = 121) -> np.ndarray:
    """Quanto x passa da média móvel em volta, em desvios robustos (mesma conta dos picos de áudio)."""
    from .detectores import _suavizar
    if len(x) < 10:
        return np.zeros_like(x, dtype=float)
    excesso = x - _suavizar(x, base)
    med = np.median(excesso)
    mad = np.median(np.abs(excesso - med)) * 1.4826 or (np.std(excesso) or 1.0)
    return np.clip((excesso - med) / mad, 0, 6)


def nota_texto(texto: str, idioma: str | None) -> tuple[float, float]:
    """(gatilho, risada) de uma frase: quantas expressões de choque/gancho e quanta risada ela tem."""
    t = _sem_acento(texto)
    gat = 0.0
    rx = _regex_gatilho(idioma)
    if rx:
        gat += len(rx.findall(t))
    gat += 0.5 * texto.count("!") + (0.5 if "?!" in texto or "!?" in texto else 0.0)
    pal = re.findall(r"\w+", t)
    if len(pal) >= 3 and any(pal[k] == pal[k + 1] == pal[k + 2] for k in range(len(pal) - 2)):
        gat += 1.0  # "não não não", "no no no"
    letras = [c for c in texto if c.isalpha()]
    if len(letras) >= 4 and sum(c.isupper() for c in letras) / len(letras) > 0.7:
        gat += 0.5  # o Whisper às vezes escreve grito em CAIXA ALTA
    ris = float(len(_RISADA.findall(texto)))
    return gat, ris


def curvas(segmentos: list[dict], duracao: int, faixa: tuple[int, int], idioma: str | None) -> dict[str, np.ndarray]:
    """Segmentos [{texto, i, f}] (segundos da live) -> {'fala': curva final, 'fala_ritmo': ..., ...}, 0..1."""
    from .detectores import _normalizar, _suavizar, mascarar
    ini, fim = faixa
    palavras = np.zeros(duracao)
    gat = np.zeros(duracao)
    ris = np.zeros(duracao)
    exp = np.zeros(duracao)
    anterior = None
    for s in segmentos:
        a, b = int(max(ini, s["i"])), int(min(fim, np.ceil(s["f"])))
        if b <= a:
            continue
        n = len(re.findall(r"\w+", s["texto"]))
        palavras[a:b] += n / (b - a)
        g, r = nota_texto(s["texto"], idioma)
        gat[a:b] += g
        ris[a:b] += r
        if anterior is not None and s["i"] - anterior >= SILENCIO_EXPLOSAO and n / max(s["f"] - s["i"], 0.5) >= RITMO_EXPLOSAO:
            exp[a:min(b, a + 4)] += 1.0
        anterior = s["f"]
    trecho = slice(ini, fim)
    ritmo = np.zeros(duracao)
    ritmo[trecho] = _z(_suavizar(palavras[trecho], 3))
    out = {"fala_ritmo": _normalizar(_suavizar(ritmo, 5)),
           "fala_explosao": _normalizar(_suavizar(exp, 3)),
           "fala_gatilho": _normalizar(_suavizar(np.log1p(gat), 5)),
           "fala_risada": _normalizar(_suavizar(np.log1p(ris), 5))}
    total = sum(out[f"fala_{k}"] * p for k, p in PESOS.items())
    out["fala"] = _normalizar(_suavizar(total, 5))
    return {k: mascarar(v, faixa) for k, v in out.items()}  # a suavização não vaza para fora do trecho


def ajustar_as_frases(inicio: float, fim: float, pico: int, frases: list[tuple[float, float]], duracao: int,
                      faixa: tuple[int, int], folga: float = 8.0) -> tuple[float, float, bool]:
    """Puxa o início para o começo de uma frase e o fim para o fim de uma frase (até `folga` s), sem passar do
    pico e mantendo a duração entre 70% e 130% da pedida. Devolve (inicio, fim, ajustou)."""
    ini_ok = [a for a, _ in frases if inicio - folga <= a <= inicio + 3 and a <= pico - 3]
    fim_ok = [b for _, b in frases if fim - folga <= b <= fim + folga and b >= pico + 2]
    novo_i = min(ini_ok, key=lambda a: abs(a - inicio)) - 0.15 if ini_ok else inicio  # respiro antes da sílaba
    candidatos = [b for b in fim_ok if duracao * 0.7 <= b - novo_i <= duracao * 1.3]
    if candidatos:
        novo_f = min(candidatos, key=lambda b: abs(b - (novo_i + duracao))) + 0.3
    else:
        novo_f = novo_i + (fim - inicio)
    novo_i, novo_f = max(float(faixa[0]), novo_i), min(float(faixa[1]), novo_f)
    if not (ini_ok or candidatos) or novo_f - novo_i < duracao * 0.6:
        return inicio, fim, False
    return round(novo_i, 2), round(novo_f, 2), True


def sugerir_gancho(segmentos: list[dict], inicio: float, fim: float, fala: np.ndarray, idioma: str | None,
                   maximo: int = 60) -> str | None:
    """A frase mais forte dentro do corte (nota da fala + gatilhos), curta o bastante para o topo do vídeo."""
    melhor, nota_melhor = None, 0.0
    for s in segmentos:
        if s["i"] < inicio or s["f"] > fim:
            continue
        txt = re.sub(r"\s+", " ", _RISADA.sub("", s["texto"])).strip(" .,-")
        if not (3 <= len(txt) <= maximo) or len(re.findall(r"\w+", txt)) < 2:
            continue
        a, b = int(s["i"]), max(int(s["i"]) + 1, int(np.ceil(s["f"])))
        g, _r = nota_texto(s["texto"], idioma)
        nota = float(fala[a:b].mean()) + 0.3 * min(g, 3)
        if nota > nota_melhor:
            melhor, nota_melhor = txt, nota
    if not melhor or nota_melhor < 0.25:
        return None
    return melhor[0].upper() + melhor[1:]
