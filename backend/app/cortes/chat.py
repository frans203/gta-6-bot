"""Chat gravado das lives do YouTube como sinal de destaque.

O yt-dlp baixa o chat (legenda 'live_chat', JSON com uma ação por linha e o tempo no vídeo). Contamos por
segundo: mensagens, mensagens de risada/choque e super chats. O chat reage alguns segundos DEPOIS do momento,
então a curva é puxada ATRASO_CHAT s para trás. As contagens ficam em cache (midia/chat/fonte_<id>.npz) e o
JSON bruto é apagado.

Twitch: o chat de um VOD só sai por endpoints internos (GQL), que o projeto não usa (regra: só a Helix)."""
import json
import re
from pathlib import Path

import numpy as np

ATRASO_CHAT = 8  # s entre o momento e o pico de mensagens
_REACAO = re.compile(r"k{3,}|(?:ha){2,}|(?:ja){2,}|(?:rs){2,}|\blo+l\b|\blmao\b|\bkekw\b|\bomegalul\b|\blul\b|\bpog\w*\b"
                     r"|\bwtf\b|\bomg\b|\bno way\b|\bclip\b|\bclipa\b|meu deus|caralho|porra|😂|🤣|😱|😭|💀|🔥|‼|!!",
                     re.I)
_EMOJI_REACAO = re.compile(r"face-with-tears-of-joy|rolling-on-the-floor|skull|loudly-crying|scream|fire|"
                           r"hand-pink-waving|yt.*(laugh|lol|kek)", re.I)


def _acoes(linha: dict):
    rep = linha.get("replayChatItemAction") or {}
    t = rep.get("videoOffsetTimeMsec")
    for a in rep.get("actions") or []:
        item = (a.get("addChatItemAction") or {}).get("item") or {}
        yield t, item


def _texto(render: dict) -> tuple[str, bool]:
    """(texto, tem emoji de risada/choque) de uma mensagem."""
    partes, emoji = [], False
    for r in (render.get("message") or {}).get("runs") or []:
        if "text" in r:
            partes.append(r["text"])
        elif "emoji" in r:
            e = r["emoji"]
            nomes = " ".join(e.get("shortcuts") or []) + " " + str(e.get("emojiId", ""))
            partes.append(e.get("emojiId", "") if len(str(e.get("emojiId", ""))) <= 2 else "")
            emoji = emoji or bool(_EMOJI_REACAO.search(nomes))
    return "".join(partes), emoji


def contar(arquivo: Path, duracao: int) -> dict[str, np.ndarray]:
    """Lê o live_chat.json linha a linha (pode ter dezenas de MB) -> {mensagens, reacoes, super} por segundo."""
    msgs, reac, sup = np.zeros(duracao), np.zeros(duracao), np.zeros(duracao)
    with open(arquivo, encoding="utf-8", errors="replace") as fp:
        for bruta in fp:
            try:
                linha = json.loads(bruta)
            except ValueError:
                continue
            for t, item in _acoes(linha):
                if t is None:
                    continue
                s = int(int(t) / 1000)
                if not 0 <= s < duracao:
                    continue
                pago = item.get("liveChatPaidMessageRenderer")
                render = item.get("liveChatTextMessageRenderer") or pago
                if not render:
                    continue
                msgs[s] += 1
                texto, emoji = _texto(render)
                if emoji or _REACAO.search(texto):
                    reac[s] += 1
                if pago:
                    sup[s] += 1
    return {"mensagens": msgs, "reacoes": reac, "super": sup}


def salvar_cache(caminho: Path, contagens: dict[str, np.ndarray], ate: float | None = None):
    """Grava as contagens. `ate` = até que segundo o chat foi baixado (None = inteiro)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.stem + ".novo.npz")
    np.savez_compressed(tmp, **contagens, _ate=np.array(-1.0 if ate is None else float(ate)))
    tmp.replace(caminho)


def ler_cache(caminho: Path, duracao: int, precisa_ate: float | None = None) -> dict[str, np.ndarray] | None:
    """Contagens em cache, se cobrem até `precisa_ate` (senão None: baixa de novo, até mais longe)."""
    if not caminho.exists():
        return None
    from .detectores import _ajustar
    with np.load(caminho) as z:
        ate = float(z["_ate"]) if "_ate" in z.files else -1.0
        if precisa_ate is not None and 0 <= ate < precisa_ate:
            return None
        return {k: _ajustar(z[k], duracao) for k in z.files if k != "_ate"}


def curvas(contagens: dict[str, np.ndarray], faixa: tuple[int, int]) -> dict[str, np.ndarray]:
    """{chat, chat_mensagens, chat_reacoes}: quanto o chat passa do normal daquele trecho da live (0..1)."""
    from .detectores import _normalizar, _suavizar, mascarar
    from .fala import _z
    dur = len(contagens["mensagens"])
    ini, fim = faixa

    def puxar(x):  # o chat reage depois: alinha o pico com o momento
        return np.concatenate([x[ATRASO_CHAT:], np.zeros(min(ATRASO_CHAT, len(x)))])

    def curva(x):
        out = np.zeros(dur)
        out[ini:fim] = _z(_suavizar(puxar(x)[ini:fim], 5))
        return mascarar(_suavizar(out, 5), faixa)

    m, r = curva(contagens["mensagens"]), curva(contagens["reacoes"] + 3 * contagens["super"])
    return {"chat": _normalizar(0.45 * m + 0.55 * r), "chat_mensagens": m, "chat_reacoes": r}
