"""Transcrição local (faster-whisper, roda no PC, sem custo) e legendas animadas palavra por palavra (.ass)."""
import os
import sys
import threading
from pathlib import Path

from ..config import config
from .plugins import ESTILOS

_modelos: dict[str, object] = {}
_trava = threading.Lock()


def _dlls_cuda():
    r"""Se as libs CUDA do pip (nvidia-cublas/cudnn) estiverem instaladas, deixa o Windows achar as DLLs.
    Instalação sugerida (fora do C:, são ~1 GB):
        pip install --target <JASON_MIDIA>\libs nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
    """
    if not hasattr(os, "add_dll_directory"):  # macOS/Linux: nada a fazer
        return
    for base in [config.midia / "libs", *map(Path, sys.path)]:
        nv = base / "nvidia"
        if nv.is_dir():
            for bin_ in nv.glob("*/bin"):
                try:
                    os.add_dll_directory(str(bin_))
                except OSError:
                    pass
                os.environ["PATH"] = str(bin_) + os.pathsep + os.environ.get("PATH", "")


def modelo(nome: str | None = None):
    """Modelo do Whisper (carregado uma vez por nome). Sem nome: o da legenda (`whisper_modelo`)."""
    nome = nome or config.whisper_modelo
    with _trava:
        if nome not in _modelos:
            from faster_whisper import WhisperModel
            _dlls_cuda()
            config.modelos.mkdir(parents=True, exist_ok=True)
            tentativas = {"cuda": [("cuda", "float16")], "cpu": [("cpu", "int8")]}.get(
                config.whisper_dispositivo, [("cuda", "float16"), ("cpu", "int8")])
            ultimo = None
            for disp, tipo in tentativas:
                try:
                    m = WhisperModel(nome, device=disp, compute_type=tipo, download_root=str(config.modelos))
                    if disp == "cuda":  # carrega as DLLs de verdade agora (falha cedo se faltar cuBLAS/cuDNN)
                        list(m.transcribe(_silencio(), language="en")[0])
                    m.dispositivo = disp
                    _modelos[nome] = m
                    break
                except Exception as e:  # sem CUDA -> CPU
                    ultimo = e
            if nome not in _modelos:
                raise RuntimeError(f"não consegui carregar o Whisper: {ultimo}")
        return _modelos[nome]


def _silencio():
    import numpy as np
    return np.zeros(16000, dtype=np.float32)


def transcrever(wav: Path, idioma: str | None = None) -> dict:
    """{'texto', 'idioma', 'palavras': [{'p': 'olá', 'i': 0.0, 'f': 0.4}], 'segmentos': [{'texto', 'i', 'f'}],
    'dispositivo'}. Os segmentos (frases) servem para traduzir a legenda."""
    m = modelo()
    segmentos, info = m.transcribe(str(wav), language=idioma, word_timestamps=True, vad_filter=True,
                                   beam_size=5, condition_on_previous_text=False)
    palavras, textos, frases = [], [], []
    for s in segmentos:
        textos.append(s.text.strip())
        frases.append({"texto": s.text.strip(), "i": round(s.start, 2), "f": round(s.end, 2)})
        for w in s.words or []:
            p = w.word.strip()
            if p:
                palavras.append({"p": p, "i": round(w.start, 2), "f": round(w.end, 2)})
    return {"texto": " ".join(textos), "idioma": info.language, "palavras": palavras, "segmentos": frases,
            "dispositivo": getattr(m, "dispositivo", "?")}


def transcrever_frases(arquivo: Path, idioma: str | None = None, ao_progresso=None, duracao: float | None = None,
                       checar=None) -> dict:
    """Transcrição rápida (sem tempo por palavra, beam 1) de um áudio longo, para achar destaques:
    {'segmentos': [{'texto', 'i', 'f'}], 'idioma', 'idioma_prob'}. Tempos em segundos do arquivo."""
    segmentos, info = modelo(config.whisper_modelo_analise).transcribe(
        str(arquivo), language=idioma, word_timestamps=False, vad_filter=True, beam_size=1,
        condition_on_previous_text=False)
    out = []
    for s in segmentos:
        if checar:
            checar()
        txt = s.text.strip()
        if txt:
            out.append({"texto": txt, "i": round(s.start, 2), "f": round(s.end, 2)})
        if ao_progresso and duracao:
            ao_progresso(min(s.end / duracao, 1.0))
    return {"segmentos": out, "idioma": info.language, "idioma_prob": round(float(info.language_probability), 2)}


def detectar_idioma(wav: Path) -> tuple[str, float]:
    """Idioma falado no áudio (código de 2 letras) e a probabilidade. Só olha os primeiros 30 s."""
    _segs, info = modelo().transcribe(str(wav), language=None, vad_filter=True, beam_size=1)
    return info.language, round(float(info.language_probability), 2)


# ------------------------------------------------------------------ estilos

def _estilo(id, nome, descricao, **o):
    ESTILOS.registrar(id, nome, descricao, **o)(lambda: o)


_estilo("destaque", "Destaque amarelo", "Fonte grossa, CAIXA ALTA, 3 palavras por vez, palavra falada em amarelo.",
        fonte="Arial Black", tamanho=74, cor="FFFFFF", destaque="FFE400", contorno=7, maiusculas=True, por_bloco=3)
_estilo("verde", "Destaque verde", "Igual ao destaque, com a palavra falada em verde.",
        fonte="Arial Black", tamanho=74, cor="FFFFFF", destaque="39FF14", contorno=7, maiusculas=True, por_bloco=3)
_estilo("uma_palavra", "Uma palavra por vez", "Só a palavra falada, grande, no centro (estilo MrBeast).",
        fonte="Arial Black", tamanho=96, cor="FFFFFF", destaque="FFFFFF", contorno=8, maiusculas=True, por_bloco=1)
_estilo("classico", "Clássico", "Frases curtas em branco com contorno, sem destaque.",
        fonte="Arial", tamanho=60, cor="FFFFFF", destaque="FFFFFF", contorno=4, maiusculas=False, por_bloco=6)
_estilo("sem_legenda", "Sem legenda", "Não queima legenda no vídeo.", nenhuma=True)


def _cor(hex_rgb: str) -> str:
    """'FFE400' -> '&H0000E4FF&' (o .ass usa BGR)."""
    r, g, b = hex_rgb[0:2], hex_rgb[2:4], hex_rgb[4:6]
    return f"&H00{b}{g}{r}&"


def _tempo(t: float) -> str:
    t = max(0.0, t)
    h, resto = divmod(t, 3600)
    m, s = divmod(resto, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _limpar(t: str) -> str:
    return t.replace("{", "(").replace("}", ")").replace("\\", "/").replace("\n", " ")


def blocos(palavras: list[dict], por_bloco: int, pausa_max: float = 0.7) -> list[list[dict]]:
    """Agrupa palavras em blocos de até N, quebrando também em pausas longas e em pontuação."""
    out, atual = [], []
    for w in palavras:
        if atual and (len(atual) >= por_bloco or w["i"] - atual[-1]["f"] > pausa_max
                      or atual[-1]["p"][-1:] in ".?!"):
            out.append(atual)
            atual = []
        atual.append(w)
    if atual:
        out.append(atual)
    return out


def gerar_ass(palavras: list[dict], estilo_id: str, legenda_y: int, gancho_y: int, duracao: float,
              gancho: str | None = None, credito: str | None = None, ajustes: dict | None = None,
              gancho_ajustes: dict | None = None) -> str:
    """`ajustes` (editor de vídeo) sobrescreve o estilo: fonte, tamanho, cor, destaque, contorno, maiusculas,
    por_bloco, mostrar. `gancho_ajustes`: fonte, tamanho, cor (texto) e fundo (caixa)."""
    e = dict(ESTILOS[estilo_id].opcoes if estilo_id in ESTILOS else ESTILOS["destaque"].opcoes)
    if ajustes:
        e.update({k: v for k, v in ajustes.items() if k not in ("y", "mostrar")})
        e["nenhuma"] = not ajustes.get("mostrar", True)
    fonte, tam = e.get("fonte", "Arial Black"), e.get("tamanho", 74)
    g = {"fonte": "Arial Black", "tamanho": 64, "cor": "000000", "fundo": "FFFFFF", **(gancho_ajustes or {})}
    linhas = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 0",
        "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        f"Style: Legenda,{fonte},{tam},{_cor(e.get('cor', 'FFFFFF'))},&H000000FF&,&H00000000&,&H80000000&,-1,0,0,0,"
        f"100,100,0,0,1,{e.get('contorno', 6)},2,5,60,60,0,1",
        f"Style: Gancho,{g['fonte']},{g['tamanho']},{_cor(g['cor'])},&H000000FF&,{_cor(g['fundo'])},{_cor(g['fundo'])},"
        "-1,0,0,0,100,100,0,0,3,18,0,8,70,70,0,1",
        "Style: Credito,Arial,34,&H00FFFFFF&,&H000000FF&,&H00000000&,&H00000000&,-1,0,0,0,100,100,0,0,1,2,0,2,40,40,0,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if not e.get("nenhuma"):
        destaque = _cor(e.get("destaque", "FFE400"))
        caixa = (lambda t: t.upper()) if e.get("maiusculas") else (lambda t: t)
        grupos = blocos(palavras, e.get("por_bloco", 3))
        for gi, bloco in enumerate(grupos):
            fim_bloco = bloco[-1]["f"] + 0.25
            if gi + 1 < len(grupos):
                fim_bloco = min(fim_bloco, grupos[gi + 1][0]["i"])
            for wi, w in enumerate(bloco):
                ini = w["i"]
                fim = bloco[wi + 1]["i"] if wi + 1 < len(bloco) else fim_bloco
                if fim <= ini:
                    continue
                partes = []
                for wj, x in enumerate(bloco):
                    t = _limpar(caixa(x["p"]))
                    partes.append(f"{{\\c{destaque}\\fscx108\\fscy108}}{t}{{\\r}}" if wj == wi else t)
                linhas.append(f"Dialogue: 0,{_tempo(ini)},{_tempo(fim)},Legenda,,0,0,0,,"
                              f"{{\\an5\\pos(540,{legenda_y})}}{' '.join(partes)}")
    if gancho:
        linhas.append(f"Dialogue: 1,{_tempo(0)},{_tempo(min(3.5, duracao))},Gancho,,0,0,0,,"
                      f"{{\\an8\\pos(540,{gancho_y})\\fad(0,250)}}{_limpar(gancho)}")
    if credito:
        linhas.append(f"Dialogue: 1,{_tempo(0)},{_tempo(duracao)},Credito,,0,0,0,,"
                      f"{{\\an2\\pos(540,1868)\\alpha&H40&}}{_limpar(credito)}")
    return "\n".join(linhas) + "\n"
