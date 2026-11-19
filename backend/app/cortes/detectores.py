"""Detectores de destaques (sem IA paga): cada um devolve uma curva com uma nota por segundo do vídeo (0..1),
sempre no tempo da live. A análise soma as curvas com pesos e escolhe os picos. Para criar um detector novo,
registre uma função `f(ctx: Analise) -> np.ndarray | None` com @DETECTORES.registrar.

Trecho: quando o usuário escolhe um pedaço da live (ex.: da 4ª à 6ª hora), `Analise.inicio/fim` limitam o que é
baixado/transcrito, e as curvas ficam zeradas fora dele. Um detector pode guardar curvas auxiliares em
`ctx.extras` (entram nos `sinais` do corte, para o aprendizado e o "por quê", mas não na nota)."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..config import config
from . import fontes, midia
from .plugins import DETECTORES


@dataclass
class Analise:
    url: str
    duracao: int                       # segundos (o vídeo inteiro)
    plataforma: str                    # twitch | youtube | kick | outro
    canal: str
    pasta: Path                        # pasta temporária
    info: dict = field(default_factory=dict)
    progresso: object = None           # callable(fracao, msg)
    log: object = print
    inicio: int = 0                    # trecho escolhido (segundos da live)
    fim: int | None = None
    fonte_id: int | None = None
    idioma: str | None = None          # idioma falado, se já se sabe (senão o Whisper descobre)
    checar: object = None              # callable que levanta se o job foi cancelado
    etapas: dict = field(default_factory=dict)   # detector -> (fração inicial, final) do progresso do job
    guardar_audio: bool = False        # o detector de áudio mantém os arquivos para o da fala usar
    audios: list = field(default_factory=list)   # [(inicio, fim, arquivo)]
    fala: dict | None = None           # {'segmentos': [...] em s da live, 'idioma', 'idioma_prob'}
    extras: dict = field(default_factory=dict)   # curvas auxiliares (sinais)

    @property
    def faixa(self) -> tuple[int, int]:
        fim = self.duracao if self.fim is None else min(int(self.fim), self.duracao)
        return max(0, int(self.inicio)), fim

    def avisar(self, etapa: str, f: float, msg: str):
        a, b = self.etapas.get(etapa, (0.05, 0.9))
        if self.progresso:
            self.progresso(a + (b - a) * min(max(f, 0.0), 1.0), msg)


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


def mascarar(curva: np.ndarray, faixa: tuple[int, int]) -> np.ndarray:
    """Zera fora do trecho escolhido e renormaliza (o que importa é o que se destaca DENTRO do trecho)."""
    out = np.zeros_like(curva, dtype=float)
    out[faixa[0]:faixa[1]] = curva[faixa[0]:faixa[1]]
    return _normalizar(out)


BLOCO_AUDIO = 3 * 3600


@DETECTORES.registrar("audio", "Picos de áudio", "Gritos, risadas, explosões: momentos bem mais altos que o normal "
                      "daquele trecho da live. Funciona em qualquer vídeo.", peso=1.0)
def picos_audio(a: Analise) -> np.ndarray:
    ini0, fim0 = a.faixa
    total = fim0 - ini0
    inteiro = ini0 == 0 and fim0 == a.duracao
    # lives longas (Kai Cenat faz 30h+) são processadas em blocos para não lotar o disco
    bloco = BLOCO_AUDIO if total > BLOCO_AUDIO * 1.3 else total
    partes = []
    for n, ini in enumerate(range(ini0, fim0, bloco)):
        fim = min(ini + bloco, fim0)
        f0, f1 = (ini - ini0) / total, (fim - ini0) / total
        prog = (lambda f, m, f0=f0, f1=f1: a.avisar("audio", f0 + f * (f1 - f0), m))
        a.log(f"áudio {ini / 3600:.1f}h–{fim / 3600:.1f}h: baixando (qualidade mínima, só para medir volume)")
        um_so = inteiro and bloco == total
        arq = fontes.baixar_audio(a.url, a.pasta / f"audio_{n}", ao_progresso=lambda f, p=prog: p(f * 0.7, "baixando áudio"),
                                  inicio=None if um_so else ini, fim=None if um_so else fim)
        partes.append(_ajustar(midia.energia_por_segundo(arq, lambda f, p=prog: p(0.7 + f * 0.3, "medindo volume"),
                                                         fim - ini), fim - ini))
        if a.guardar_audio:
            a.audios.append((ini, fim, arq))
        else:
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
    if ini0 == 0:
        curva[:60] = 0  # abertura da live (música, tela de "já começa")
    if fim0 == a.duracao:
        curva[-60:] = 0  # encerramento (despedida, raid)
    out = np.zeros(a.duracao)
    out[ini0:ini0 + len(curva)] = _ajustar(curva, fim0 - ini0)
    return _normalizar(out)


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
    return _normalizar(x - np.median(x[slice(*a.faixa)] if a.faixa[1] > a.faixa[0] else x))


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


def _cache_fala(a: Analise) -> Path | None:
    if a.fonte_id is None:
        return None
    ini, fim = a.faixa
    return config.midia / "transcricoes" / f"fonte_{a.fonte_id}_{ini}_{fim}.json"


@DETECTORES.registrar("fala", "Fala do streamer", "Transcreve o trecho com o Whisper (local, grátis) e procura fala "
                      "acelerada, gritos depois de silêncio, risadas e palavras de choque. Também faz o corte começar "
                      "e terminar no limite de uma frase e sugere o texto do gancho.", peso=1.5)
def fala_streamer(a: Analise) -> np.ndarray | None:
    from . import fala, legendas
    ini0, fim0 = a.faixa
    if fim0 - ini0 > config.fala_max_h * 3600:
        a.log(f"fala: trecho de {(fim0 - ini0) / 3600:.1f}h passa do limite de {config.fala_max_h:g}h; pulei "
              "(escolha um trecho menor para usar a fala)")
        return None
    cache = _cache_fala(a)
    if cache and cache.exists():
        a.fala = json.loads(cache.read_text("utf-8"))
        a.log(f"fala: usando a transcrição já feita deste trecho ({len(a.fala['segmentos'])} frases)")
    else:
        blocos = a.audios or []
        if not blocos:  # o detector de áudio não rodou (ou não guardou): baixa só para transcrever
            a.avisar("fala", 0.0, "baixando o áudio para transcrever")
            arq = fontes.baixar_audio(a.url, a.pasta / "fala", inicio=ini0, fim=fim0)
            blocos = [(ini0, fim0, arq)]
        segmentos, idioma, prob = [], a.idioma, 0.0
        for ini, fim, arq in blocos:
            a.log(f"fala {ini / 3600:.1f}h–{fim / 3600:.1f}h: transcrevendo (Whisper local)")
            f0, f1 = (ini - ini0) / (fim0 - ini0), (fim - ini0) / (fim0 - ini0)
            tr = legendas.transcrever_frases(
                arq, idioma, duracao=fim - ini, checar=a.checar,
                ao_progresso=lambda f, f0=f0, f1=f1: a.avisar("fala", f0 + f * (f1 - f0), "transcrevendo a fala"))
            idioma = idioma or tr["idioma"]
            prob = max(prob, tr["idioma_prob"])
            segmentos += [{**s, "i": round(s["i"] + ini, 2), "f": round(s["f"] + ini, 2)} for s in tr["segmentos"]]
        a.fala = {"segmentos": segmentos, "idioma": idioma, "idioma_prob": prob}
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache.with_suffix(".novo")
            tmp.write_text(json.dumps(a.fala, ensure_ascii=False), "utf-8")
            tmp.replace(cache)
        a.log(f"fala: {len(segmentos)} frases ({idioma})")
    if not a.fala["segmentos"]:
        return None
    cs = fala.curvas(a.fala["segmentos"], a.duracao, a.faixa, a.fala.get("idioma"))
    principal = cs.pop("fala")
    a.extras.update(cs)
    return principal


@DETECTORES.registrar("chat_youtube", "Chat (YouTube)", "Picos de mensagens e de risadas/emojis no chat gravado das "
                      "lives do YouTube, quando o vídeo tem.", peso=2.0)
def chat_youtube(a: Analise) -> np.ndarray | None:
    from . import chat
    if a.plataforma != "youtube":
        return None
    cache = config.midia / "chat" / f"fonte_{a.fonte_id}.npz" if a.fonte_id is not None else None
    fim = a.faixa[1]
    contagens = chat.ler_cache(cache, a.duracao, fim) if cache else None
    if contagens is None:
        if not a.info.get("tem_chat"):
            return None
        a.log(f"chat: baixando o chat gravado até {fim / 3600:.1f}h (o YouTube entrega devagar, ~8x o tempo real)")
        r = fontes.baixar_chat_youtube(a.url, a.pasta / "chat", ate=None if fim >= a.duracao - 60 else fim,
                                       ao_progresso=lambda f: a.avisar("chat_youtube", f * 0.95, "baixando o chat"))
        if not r:
            return None
        arq, ate = r
        a.avisar("chat_youtube", 0.97, "contando as mensagens do chat")
        contagens = chat.contar(arq, a.duracao)
        arq.unlink(missing_ok=True)
        if cache:
            chat.salvar_cache(cache, contagens, ate)
    total = int(contagens["mensagens"][slice(*a.faixa)].sum())
    a.log(f"chat: {total} mensagens no trecho")
    if total < 50:
        return None
    cs = chat.curvas(contagens, a.faixa)
    principal = cs.pop("chat")
    a.extras.update(cs)
    return principal


def combinar(curvas: dict[str, np.ndarray], pesos: dict[str, float]) -> np.ndarray:
    total = sum(pesos[k] for k in curvas) or 1.0
    return sum(curvas[k] * pesos[k] for k in curvas) / total


def escolher_picos(score: np.ndarray, curvas: dict[str, np.ndarray], n: int, duracao: int,
                   antes: float = 0.65, minimo: float = 0.08, faixa: tuple[int, int] | None = None,
                   frases: list[tuple[float, float]] | None = None) -> list[dict]:
    """Os n melhores trechos sem sobreposição, dentro da `faixa`. O pico fica a ~65% do corte: dá contexto antes
    e a reação depois. Com `frases` (da transcrição), início e fim caem no limite de uma frase."""
    from .fala import ajustar_as_frases
    s = _suavizar(score.astype(float), 3).copy()
    total = len(s)
    lo, hi = faixa or (0, total)
    s[:lo] = -1
    s[hi:] = -1
    hi = min(hi, total)
    out = []
    while len(out) < n:
        i = int(np.argmax(s))
        if s[i] < minimo:
            break
        inicio = max(lo, min(int(i - duracao * antes), hi - duracao))
        fim = min(hi, inicio + duracao)
        inicio, fim, ajustou = (float(inicio), float(fim), False)
        if frases:
            inicio, fim, ajustou = ajustar_as_frases(inicio, fim, i, frases, duracao, (lo, hi))
        sinais = {k: round(float(c[i]), 3) for k, c in curvas.items()} | {"pico": i}
        if ajustou:
            sinais["frase"] = 1
        out.append({"inicio": float(inicio), "fim": float(fim), "score": round(float(score[i]), 3), "sinais": sinais})
        a, b = int(inicio), int(np.ceil(fim))
        s[max(0, a - duracao): b + duracao] = -1  # nada colado: o próximo fica a 1 corte de distância
    return out
