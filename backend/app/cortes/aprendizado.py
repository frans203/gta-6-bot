"""O cortador aprende com o que você aprova e descarta (sem IA paga: regressão logística em numpy).

Cada corte guarda os `sinais` do momento escolhido (áudio, fala, chat, clipes...). Cortes aprovados/renderizados/
mandados para a fila contam como bons; descartados na revisão (status candidato/enquadrar) contam como ruins.
Um descarte depois de pronto quase sempre é por outro motivo (webcam, repetido) e fica de fora.

Com exemplos suficientes, a análise pega 3x mais candidatos pela soma das curvas e reordena pela probabilidade
de você aprovar. O estado fica em dados/pesos_aprendidos.json (ligar/desligar pela tela Modelos)."""
import json
from datetime import datetime

import numpy as np
from sqlalchemy import select

from ..config import config
from ..db import sessao
from ..models import Corte

SINAIS = ["audio", "mais_assistidos", "clipes_twitch", "fala", "chat_youtube",
          "fala_ritmo", "fala_explosao", "fala_gatilho", "fala_risada", "chat_mensagens", "chat_reacoes"]
POSITIVOS = {"aprovado", "renderizando", "pronto", "na_fila", "publicado"}
DESCARTE_NA_REVISAO = {None, "candidato", "enquadrar"}
MIN_EXEMPLOS, MIN_POR_CLASSE = 30, 10
MISTURA = 0.6   # nota final = (1 - MISTURA) * nota das curvas + MISTURA * probabilidade aprendida


def _arquivo():
    return config.dados / "pesos_aprendidos.json"


def _ler() -> dict:
    try:
        return json.loads(_arquivo().read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar(d: dict):
    arq = _arquivo()
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_suffix(".novo")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(arq)


def vetor(sinais: dict) -> np.ndarray:
    return np.array([float(sinais.get(k) or 0.0) for k in SINAIS])


def exemplos() -> tuple[np.ndarray, np.ndarray]:
    """(X, y) dos cortes já revisados que vieram dos detectores."""
    xs, ys = [], []
    with sessao() as s:
        for c in s.scalars(select(Corte).where(Corte.status.in_(POSITIVOS | {"descartado"}))):
            sinais = c.sinais or {}
            if not any(k in sinais for k in SINAIS):
                continue  # clipe inteiro, vigia, corte manual: não tem sinais dos detectores
            if c.status == "descartado":
                if (c.extra or {}).get("descartado_de") not in DESCARTE_NA_REVISAO:
                    continue
                ys.append(0)
            else:
                ys.append(1)
            xs.append(vetor(sinais))
    return (np.array(xs) if xs else np.zeros((0, len(SINAIS)))), np.array(ys, dtype=float)


def ajustar(X: np.ndarray, y: np.ndarray, l2: float = 0.05, passos: int = 800, taxa: float = 0.5):
    """Regressão logística com pesos por classe (poucos descartes não somem no meio de muitas aprovações)."""
    n, d = X.shape
    w, b = np.zeros(d), 0.0
    pos = y.sum()
    peso = np.where(y == 1, n / (2 * max(pos, 1)), n / (2 * max(n - pos, 1)))
    for _ in range(passos):
        p = 1 / (1 + np.exp(-(X @ w + b)))
        erro = (p - y) * peso
        w -= taxa * (X.T @ erro / n + l2 * w)
        b -= taxa * erro.mean()
    return w, b


def treinar() -> dict:
    """Retreina com o que há no banco (é rápido) e grava. Devolve o estado (o que a tela Modelos mostra)."""
    atual = _ler()
    X, y = exemplos()
    pos, neg = int(y.sum()), int(len(y) - y.sum())
    estado = {"ligado": atual.get("ligado", True), "exemplos": len(y), "aprovados": pos, "descartados": neg,
              "minimo": MIN_EXEMPLOS, "minimo_por_tipo": MIN_POR_CLASSE, "pronto": False, "pesos": {}, "vies": 0.0,
              "treinado_em": datetime.now().isoformat(timespec="minutes")}
    if len(y) >= MIN_EXEMPLOS and pos >= MIN_POR_CLASSE and neg >= MIN_POR_CLASSE:
        w, b = ajustar(X, y)
        estado.update(pronto=True, pesos={k: round(float(v), 3) for k, v in zip(SINAIS, w)}, vies=round(float(b), 3))
    _gravar(estado)
    return estado


def estado() -> dict:
    e = _ler()
    return e if e else treinar()


def ligar(ligado: bool) -> dict:
    e = estado() | {"ligado": ligado}
    _gravar(e)
    return e


def modelo_ativo() -> dict | None:
    """O modelo treinado, se estiver pronto e ligado (senão a análise usa só os pesos fixos)."""
    e = treinar()
    return e if e["pronto"] and e["ligado"] else None


def probabilidade(modelo: dict, sinais: dict) -> float:
    w = np.array([modelo["pesos"].get(k, 0.0) for k in SINAIS])
    return float(1 / (1 + np.exp(-(vetor(sinais) @ w + modelo["vies"]))))


def reordenar(candidatos: list[dict], n: int, modelo: dict | None) -> list[dict]:
    """Os n melhores entre os candidatos: pela nota das curvas, ou misturada com a probabilidade aprendida."""
    if not modelo:
        return candidatos[:n]
    topo = max((c["score"] for c in candidatos), default=1.0) or 1.0
    for c in candidatos:
        p = probabilidade(modelo, c["sinais"])
        c["sinais"]["aprendido"] = round(p, 3)
        c["_nota"] = (1 - MISTURA) * c["score"] / topo + MISTURA * p
    escolhidos = sorted(candidatos, key=lambda c: c["_nota"], reverse=True)[:n]
    for c in escolhidos:
        c.pop("_nota", None)
    return escolhidos
