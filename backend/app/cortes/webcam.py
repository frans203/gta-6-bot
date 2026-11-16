"""Acha a webcam do streamer no quadro: o rosto que aparece SEMPRE no mesmo lugar (rostos do jogo se mexem).
Sem IA paga: detector de rosto YuNet do próprio OpenCV (modelo de 230 KB, roda local, acha rostos pequenos, de
lado, com boné/fone), com os detectores clássicos Haar como reserva, + agrupamento por posição.
Sem nenhum rosto fixo, o corte segue sem a parte do streamer; com rosto fixo mas incerto, pede o recorte."""
import threading
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from ..config import config

YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
             "face_detection_yunet_2023mar.onnx")
_trava = threading.Lock()

CASCATAS = ["haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"]
CONFIANCA_MINIMA = 0.45   # a partir daqui: streamer identificado, segue sozinho
CONFIANCA_DUVIDA = 0.15   # entre as duas: há uma câmera fixa, mas a posição é incerta -> pede o recorte manual
                          # abaixo (ou nenhum rosto fixo): não há webcam -> o corte sai sem a parte do streamer


def classificar(det: dict | None) -> str:
    """'auto' (usa), 'duvida' (sabe que existe, pede o recorte) ou 'nenhuma' (segue sem webcam)."""
    if not det:
        return "nenhuma"
    if det["confianca"] >= CONFIANCA_MINIMA:
        return "auto"
    if det["confianca"] >= CONFIANCA_DUVIDA and det.get("amostras", 0) >= 3:
        return "duvida"
    return "nenhuma"


def _rostos(dets, cinza, minimo: int):
    """Rostos de frente e de perfil (o de perfil roda também no quadro espelhado: só detecta um lado)."""
    larg = cinza.shape[1]
    frente, perfil = dets
    yield from frente.detectMultiScale(cinza, scaleFactor=1.1, minNeighbors=6, minSize=(minimo, minimo))
    yield from perfil.detectMultiScale(cinza, scaleFactor=1.1, minNeighbors=6, minSize=(minimo, minimo))
    for (x, y, w, h) in perfil.detectMultiScale(cv2.flip(cinza, 1), scaleFactor=1.1, minNeighbors=6,
                                                minSize=(minimo, minimo)):
        yield (larg - x - w, y, w, h)


def _modelo_yunet() -> Path | None:
    """Caminho do modelo YuNet (baixa uma vez para JASON_MIDIA/modelos/rosto). None se não der para baixar."""
    arq = config.modelos / "rosto" / "face_detection_yunet_2023mar.onnx"
    with _trava:
        if not arq.exists():
            try:
                arq.parent.mkdir(parents=True, exist_ok=True)
                with urllib.request.urlopen(YUNET_URL, timeout=60) as r:
                    dados = r.read()
                tmp = arq.with_suffix(".baixando")
                tmp.write_bytes(dados)
                tmp.replace(arq)
            except Exception:
                return None
    return arq


class _Detector:
    """YuNet (preferido) ou Haar. Devolve rostos (x, y, w, h) em pixels do quadro original."""

    def __init__(self):
        self.yunet, self.escala, self.haar = None, 1.0, None
        self.modelo = _modelo_yunet()
        if self.modelo is None:
            self.haar = [cv2.CascadeClassifier(cv2.data.haarcascades + c) for c in CASCATAS]

    def rostos(self, quadro) -> list[tuple[float, float, float, float]]:
        alt, larg = quadro.shape[:2]
        if self.haar is not None:
            cinza = cv2.equalizeHist(cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY))
            return [tuple(map(float, r)) for r in _rostos(self.haar, cinza, max(24, alt // 28))]
        # vídeos pequenos (480p) são ampliados: a câmera do streamer costuma ser um canto minúsculo
        escala = max(1.0, 640 / alt)
        img = cv2.resize(quadro, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC) if escala > 1 else quadro
        h, w = img.shape[:2]
        if self.yunet is None or self.yunet.getInputSize() != (w, h):
            self.yunet = cv2.FaceDetectorYN.create(str(self.modelo), "", (w, h), 0.6, 0.3, 5000)
        _, faces = self.yunet.detect(img)
        if faces is None:
            return []
        return [(float(f[0] / escala), float(f[1] / escala), float(f[2] / escala), float(f[3] / escala))
                for f in faces]


def _amostras(video: Path, n: int):
    """n quadros espalhados pelo vídeo. Lê em sequência (grab é barato): pular com CAP_PROP_POS_FRAMES nos mp4 do
    yt-dlp chega a levar 25 s para 36 quadros."""
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    alvos = set(np.linspace(0, total - 1, n).astype(int).tolist())
    i, ultimo = 0, max(alvos)
    while i <= ultimo and cap.grab():
        if i in alvos:
            ok, quadro = cap.retrieve()
            if ok:
                yield quadro
        i += 1
    cap.release()


def detectar(video: Path, salvar_quadro: Path | None = None, n_amostras: int = 36) -> dict | None:
    """Rosto fixo mais frequente como webcam {x, y, w, h, confianca, amostras} em frações do quadro (0..1), ou
    None se não há nenhum rosto repetido no mesmo lugar. Use classificar() para decidir o que fazer."""
    detector = _Detector()
    rostos, quadros, alt, larg = [], [], 0, 0
    for q in _amostras(video, n_amostras):
        alt, larg = q.shape[:2]
        quadros.append(q)
        # um rosto por quadro e posição (detectores podem achar o mesmo rosto duas vezes)
        vistos = []
        for (x, y, w, h) in detector.rostos(q):
            c = (x + w / 2, y + h / 2)
            if any(abs(c[0] - v[0]) < w / 2 and abs(c[1] - v[1]) < h / 2 for v in vistos):
                continue
            vistos.append(c)
            rostos.append((c[0], c[1], w, h))
    if salvar_quadro and quadros:
        salvar_quadro.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(salvar_quadro), quadros[len(quadros) // 2])
    if not rostos or not quadros:
        return None

    pts = np.array(rostos, dtype=float)
    # agrupa rostos cujos centros estão a menos de 6% da largura um do outro; fica com o grupo mais frequente
    raio = 0.06 * larg
    melhor = max(range(len(pts)), key=lambda i: np.sum(np.hypot(*(pts[:, :2] - pts[i, :2]).T) < raio))
    grupo = pts[np.hypot(*(pts[:, :2] - pts[melhor, :2]).T) < raio]
    if len(grupo) < 2:
        return None  # nenhum rosto repetido no mesmo lugar: não há webcam
    cx, cy, fw, fh = np.median(grupo, axis=0)

    # a webcam costuma ter ~4x a largura do rosto, 16:9, com o rosto um pouco acima do centro
    cw = min(fw * 4.2, larg * 0.5)
    ch = min(cw * 9 / 16, alt * 0.6)
    x0 = float(np.clip(cx - cw / 2, 0, larg - cw))
    y0 = float(np.clip(cy - ch * 0.42, 0, alt - ch))
    # webcams costumam encostar nas bordas: se está perto, encosta
    margem = 0.05
    if x0 < larg * margem:
        x0 = 0.0
    if larg - (x0 + cw) < larg * margem:
        x0 = larg - cw
    if y0 < alt * margem:
        y0 = 0.0
    if alt - (y0 + ch) < alt * margem:
        y0 = alt - ch
    x0, y0, x1, y1 = _moldura(quadros, cx, cy, fw, fh, (x0, y0, x0 + cw, y0 + ch))
    x0, y0 = (0.0 if x0 < larg * margem else x0), (0.0 if y0 < alt * margem else y0)
    x1, y1 = (larg if larg - x1 < larg * margem else x1), (alt if alt - y1 < alt * margem else y1)
    return {"x": round(float(x0 / larg), 4), "y": round(float(y0 / alt), 4), "w": round(float((x1 - x0) / larg), 4),
            "h": round(float((y1 - y0) / alt), 4), "confianca": round(len(grupo) / len(quadros), 2),
            "amostras": int(len(grupo))}


def _moldura(quadros, cx, cy, fw, fh, estimada):
    """Ajusta a caixa estimada pela moldura real da câmera: a borda do overlay é uma linha reta PARADA em todos os
    quadros (as bordas do jogo se mexem). Procura, em volta do rosto, a coluna/linha com o maior gradiente mediano
    ao longo do tempo. Lados sem borda clara (ex.: câmera encostada no canto) ficam com a estimativa."""
    alt, larg = quadros[0].shape[:2]
    red = min(1.0, 540 / alt)  # trabalha em no máximo 540p (memória e velocidade)
    perfis_x, perfis_y = [], []
    fcx, fcy, ffw, ffh = cx * red, cy * red, fw * red, fh * red
    for q in quadros:
        g = cv2.cvtColor(cv2.resize(q, None, fx=red, fy=red) if red < 1 else q, cv2.COLOR_BGR2GRAY).astype(np.int16)
        h, w = g.shape
        r0, r1 = int(max(0, fcy - ffh)), int(min(h, fcy + ffh))
        c0, c1 = int(max(0, fcx - ffw)), int(min(w, fcx + ffw))
        perfis_x.append(np.abs(np.diff(g[r0:r1], axis=1)).mean(axis=0))
        perfis_y.append(np.abs(np.diff(g[:, c0:c1], axis=0)).mean(axis=1))
    px, py = np.median(perfis_x, axis=0), np.median(perfis_y, axis=0)
    h, w = len(py) + 1, len(px) + 1

    def borda(perfil, a, b):
        a, b = int(max(0, a)), int(min(len(perfil), b))
        if b - a < 2:
            return None, 0.0
        i = int(np.argmax(perfil[a:b]))
        return a + i + 1, float(perfil[a + i])

    achadas = {"esq": borda(px, fcx - 6 * ffw, fcx - ffw), "dir": borda(px, fcx + ffw, fcx + 6 * ffw),
               "topo": borda(py, fcy - 5 * ffh, fcy - ffh), "base": borda(py, fcy + ffh, fcy + 5 * ffh)}
    forte = max(v for _, v in achadas.values())
    base_ruido = float(np.median(np.concatenate([px, py])))
    ok = {k: (pos / red) for k, (pos, v) in achadas.items()
          if pos is not None and v >= 0.4 * forte and v >= 8 * max(base_ruido, 0.5)}
    x0, y0, x1, y1 = estimada
    x0, x1 = ok.get("esq", x0), ok.get("dir", x1)
    y0, y1 = ok.get("topo", y0), ok.get("base", y1)
    # bom senso: a caixa contém o rosto e tem tamanho de webcam; senão fica a estimativa
    if not (x0 < cx - fw / 2 and x1 > cx + fw / 2 and y0 < cy - fh / 2 and y1 > cy + fh / 2
            and 1.5 * fw <= x1 - x0 <= 0.6 * larg and 1.5 * fh <= y1 - y0 <= 0.75 * alt):
        return estimada
    return x0, y0, x1, y1
