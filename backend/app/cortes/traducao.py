"""Tradução local e gratuita da legenda (sem API paga): modelos OPUS-MT empacotados pelo Argos Translate,
rodando no CTranslate2 (o mesmo motor do faster-whisper). Cada par de idiomas tem ~80 MB e é baixado
uma vez para JASON_MIDIA/modelos/traducao.

Dependência extra: sentencepiece. Nesta máquina o C: está cheio, então ela fica em JASON_MIDIA/libs:
    python -m pip install --target <JASON_MIDIA>\\libs sentencepiece
"""
import io
import json
import re
import sys
import threading
import urllib.request
import zipfile
from pathlib import Path

from ..config import config

INDICE = "https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json"
IDIOMAS = {"pt": "Português", "en": "Inglês", "es": "Espanhol"}

_modelos: dict[tuple[str, str], tuple] = {}
_trava = threading.Lock()


def _pasta() -> Path:
    return config.modelos / "traducao"


def _importar_sentencepiece():
    libs = str(config.midia / "libs")
    if libs not in sys.path:
        sys.path.append(libs)
    import sentencepiece
    return sentencepiece


def _baixar_pacote(de: str, para: str) -> Path:
    """Baixa e extrai o pacote do par (de -> para). Devolve a pasta do pacote."""
    with urllib.request.urlopen(INDICE, timeout=60) as r:
        indice = json.load(r)
    pacote = next((p for p in indice if p["from_code"] == de and p["to_code"] == para), None)
    if not pacote:
        raise ValueError(f"não há modelo de tradução {de} -> {para}")
    _pasta().mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(pacote["links"][0], timeout=600) as r:
        dados = r.read()
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        raiz = z.namelist()[0].split("/")[0]
        z.extractall(_pasta())
    return _pasta() / raiz


def _modelo(de: str, para: str):
    with _trava:
        if (de, para) not in _modelos:
            import ctranslate2
            spm = _importar_sentencepiece()
            pasta = next((p for p in _pasta().glob(f"translate-{de}_{para}-*") if p.is_dir()), None) if \
                _pasta().exists() else None
            pasta = pasta or _baixar_pacote(de, para)
            sp = spm.SentencePieceProcessor(model_file=str(pasta / "sentencepiece.model"))
            tr = ctranslate2.Translator(str(pasta / "model"), device="cpu", inter_threads=1)
            _modelos[(de, para)] = (sp, tr)
        return _modelos[(de, para)]


def traduzir(textos: list[str], de: str, para: str) -> list[str]:
    """Traduz frases. Sem par direto (ex.: es -> pt), passa pelo inglês."""
    if de == para or not textos:
        return list(textos)
    if de != "en" and para != "en":
        return traduzir(traduzir(textos, de, "en"), "en", para)
    sp, tr = _modelo(de, para)
    r = tr.translate_batch([sp.encode(t, out_type=str) for t in textos], beam_size=4, max_batch_size=16)
    return ["".join(x.hypotheses[0]).replace("▁", " ").strip() for x in r]


def _por_frase(seg: dict) -> list[dict]:
    """Um segmento do Whisper pode ter várias frases; o modelo de tradução às vezes traduz só a primeira.
    Quebra em frases e reparte o tempo do segmento pelo tamanho de cada uma."""
    partes = [x for x in re.split(r"(?<=[.!?…])\s+", seg["texto"].strip()) if x.strip()]
    if len(partes) <= 1:
        return [seg] if seg["texto"].strip() else []
    total, t0, out = sum(len(x) for x in partes), seg["i"], []
    for x in partes:
        d = (seg["f"] - seg["i"]) * len(x) / total
        out.append({"texto": x, "i": t0, "f": t0 + d})
        t0 += d
    return out


def traduzir_palavras(segmentos: list[dict], de: str, para: str) -> list[dict]:
    """Traduz frase por frase e reparte o tempo de cada frase entre as palavras traduzidas (proporcional ao
    tamanho), para a legenda palavra por palavra continuar sincronizada com a fala."""
    frases = [f for s in segmentos for f in _por_frase(s)]
    traduzidas = traduzir([s["texto"] for s in frases], de, para)
    palavras = []
    for s, t in zip(frases, traduzidas, strict=True):
        ws = t.split()
        if not ws:
            continue
        total = sum(len(w) + 1 for w in ws)
        dur, t0 = max(0.2, s["f"] - s["i"]), s["i"]
        for w in ws:
            d = dur * (len(w) + 1) / total
            palavras.append({"p": w, "i": round(t0, 2), "f": round(t0 + d * 0.95, 2)})
            t0 += d
    return palavras
