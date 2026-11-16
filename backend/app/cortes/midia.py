"""Utilitários de ffmpeg/ffprobe."""
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

SEM_JANELA = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW: não pisca console no Windows


def ffprobe(caminho: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format",
                        str(caminho)], capture_output=True, text=True, creationflags=SEM_JANELA, check=True)
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    fps = 30.0
    if v and v.get("avg_frame_rate", "0/0") != "0/0":
        n, dd = v["avg_frame_rate"].split("/")
        fps = float(n) / float(dd) if float(dd) else 30.0
    return {"largura": int(v["width"]) if v else 0, "altura": int(v["height"]) if v else 0,
            "duracao": float(d["format"].get("duration") or 0), "fps": fps, "tem_audio": a is not None}


def rodar(args: list[str], duracao: float | None = None, ao_progresso=None, cwd: Path | None = None):
    """Roda o ffmpeg mostrando o progresso (0..1) pelo -progress."""
    cmd = ["ffmpeg", "-hide_banner", "-y", "-nostats", "-progress", "pipe:1", *args]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd,
                         encoding="utf-8", errors="replace", creationflags=SEM_JANELA)
    erros: list[str] = []

    import threading

    def ler_erros():
        for linha in p.stderr:
            erros.append(linha)
            del erros[:-40]

    t = threading.Thread(target=ler_erros, daemon=True)
    t.start()
    for linha in p.stdout:
        m = re.match(r"out_time_us=(\d+)", linha)
        if m and duracao and ao_progresso:
            ao_progresso(min(int(m.group(1)) / 1e6 / duracao, 1.0))
    p.wait()
    t.join(2)
    if p.returncode:
        raise RuntimeError("ffmpeg falhou: " + "".join(erros[-8:]).strip()[-1500:])


@lru_cache
def nvenc_ok() -> bool:
    """A GPU NVIDIA consegue codificar H.264? (só precisa do driver, não do CUDA toolkit)."""
    try:
        subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.2",
                        "-c:v", "h264_nvenc", "-f", "null", "-"], check=True, capture_output=True, timeout=30,
                       creationflags=SEM_JANELA)
        return True
    except Exception:
        return False


@lru_cache
def videotoolbox_ok() -> bool:
    """Mac: codificador de vídeo do próprio chip (bem mais rápido que o libx264)."""
    if sys.platform != "darwin":
        return False
    try:
        subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.2",
                        "-c:v", "h264_videotoolbox", "-f", "null", "-"], check=True, capture_output=True, timeout=30)
        return True
    except Exception:
        return False


def codificador() -> list[str]:
    if videotoolbox_ok():
        return ["-c:v", "h264_videotoolbox", "-b:v", "10M", "-maxrate", "14M", "-profile:v", "high"]
    if nvenc_ok():
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "23", "-b:v", "0",
                "-maxrate", "14M", "-bufsize", "28M", "-profile:v", "high"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "21", "-profile:v", "high"]


def extrair_wav(video: Path, destino: Path) -> Path:
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
                    str(destino)], check=True, creationflags=SEM_JANELA)
    return destino


def energia_por_segundo(arquivo: Path, ao_progresso=None, duracao: float | None = None) -> np.ndarray:
    """Volume (dB RMS) de cada segundo do áudio, lendo em blocos (serve para VODs de várias horas)."""
    taxa = 8000
    p = subprocess.Popen(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(arquivo), "-vn", "-ac", "1",
                          "-ar", str(taxa), "-f", "s16le", "-"], stdout=subprocess.PIPE, creationflags=SEM_JANELA)
    valores = []
    bloco = taxa * 2 * 60  # 60 s por leitura
    resto = b""
    while True:
        dados = p.stdout.read(bloco)
        if not dados:
            break
        dados = resto + dados
        n = len(dados) // (taxa * 2) * (taxa * 2)
        resto = dados[n:]
        amostras = np.frombuffer(dados[:n], dtype=np.int16).astype(np.float32).reshape(-1, taxa)
        rms = np.sqrt(np.mean(amostras ** 2, axis=1))
        valores.append(20 * np.log10(rms + 1.0))
        if ao_progresso and duracao:
            ao_progresso(min(sum(len(v) for v in valores) / duracao, 1.0))
    p.wait()
    return np.concatenate(valores) if valores else np.zeros(0, dtype=np.float32)


def area_util(video: Path, duracao: float, amostra: float = 12.0) -> dict | None:
    """Área com imagem de verdade (sem as barras pretas), em frações do quadro: {x, y, w, h, espaco_preto}.
    Usa o cropdetect do ffmpeg no meio do trecho e fica com o recorte mais frequente (cenas escuras do jogo
    não enganam). None se não conseguir medir."""
    from collections import Counter
    info = ffprobe(video)
    sw, sh = info["largura"], info["altura"]
    if not sw or not sh:
        return None
    ini = max(0.0, duracao / 2 - amostra / 2)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{ini:.2f}", "-t", f"{amostra:.2f}", "-i", str(video),
                        "-vf", "fps=2,cropdetect=limit=24:round=2:reset=0", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=SEM_JANELA)
    achados = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
    if not achados:
        return None
    w, h, x, y = map(int, Counter(achados).most_common(1)[0][0])
    if w < sw * 0.2 or h < sh * 0.2:  # quadro quase todo preto (fade, tela de loading): não confia
        return None
    return {"x": round(x / sw, 4), "y": round(y / sh, 4), "w": round(w / sw, 4), "h": round(h / sh, 4),
            "espaco_preto": round(1 - (w * h) / (sw * sh), 3)}
