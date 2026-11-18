"""Editor de vídeo: edição livre de um corte.

Uma edição (corte.edicao, validada por api.schemas.Edicao) tem:
  segmentos   [{i, f}] em segundos da live/vídeo original, na ordem em que entram no vídeo final
  sincronizado / atraso_streamer   streamer e jogo vêm do MESMO arquivo, então ficam juntos por natureza;
              sem sincronia, a trilha do streamer pode ser adiantada/atrasada alguns segundos
  legenda / gancho   estilo do texto (fonte, cor, tamanho, posição)
  layout      jogo e webcam: o que recortar do original (fonte) e onde fica no vertical (saida); fundo

O render (render.py) usa isto no lugar das posições do modelo de corte: concatena os trechos, monta o layout
livre e remapeia a legenda para a nova linha do tempo. O editor (frontend) desenha a MESMA conta num canvas.
"""
import shutil
import sys
from pathlib import Path

from ..config import config
from .layouts import A, L, Montagem, _jogo_sem_a_webcam, _par, regiao_px
from .plugins import ESTILOS, LAYOUTS

# folga baixada antes e depois do corte: é o que deixa puxar o início para trás (ou o fim para frente) no editor
MARGEM = 10.0

QUADRO = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}

# fontes do sistema que o editor oferece: (família, arquivo no Windows, arquivo no macOS)
FONTES_SISTEMA = [
    ("Arial Black", "ariblk.ttf", "Arial Black.ttf"), ("Impact", "impact.ttf", "Impact.ttf"),
    ("Arial", "arialbd.ttf", "Arial Bold.ttf"), ("Segoe UI Black", "seguibl.ttf", None),
    ("Bahnschrift", "bahnschrift.ttf", None), ("Verdana", "verdanab.ttf", "Verdana Bold.ttf"),
    ("Trebuchet MS", "trebucbd.ttf", "Trebuchet MS Bold.ttf"), ("Comic Sans MS", "comicbd.ttf", "Comic Sans MS Bold.ttf"),
    ("Georgia", "georgiab.ttf", "Georgia Bold.ttf"),
]
PASTAS_FONTES = {"win32": [Path("C:/Windows/Fonts")],
                 "darwin": [Path("/System/Library/Fonts/Supplemental"), Path("/Library/Fonts"),
                            Path.home() / "Library" / "Fonts"]}
EXTENSOES_FONTE = (".ttf", ".otf")


# ------------------------------------------------------------------ fontes do texto

def pasta_fontes() -> Path:
    p = config.midia / "fontes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _familia(arquivo: Path) -> str:
    """Nome da família gravado no arquivo da fonte (é por ele que o libass e o navegador acham a fonte)."""
    try:
        from fontTools.ttLib import TTFont
        nomes = TTFont(str(arquivo), lazy=True)["name"]
        for nid in (16, 1):  # família tipográfica, família
            n = nomes.getDebugName(nid)
            if n:
                return n
    except Exception:  # noqa: BLE001 (arquivo estranho: usa o nome do arquivo)
        pass
    return arquivo.stem


def fontes_usuario() -> list[dict]:
    return [{"nome": _familia(p), "arquivo": p.name}
            for p in sorted(pasta_fontes().iterdir()) if p.suffix.lower() in EXTENSOES_FONTE]


def fontes_texto() -> list[dict]:
    """Fontes que o editor oferece: as suas (midia/fontes) primeiro, depois as do sistema que existem aqui."""
    sistema = []
    pastas = PASTAS_FONTES.get(sys.platform)
    for nome, arq_win, arq_mac in FONTES_SISTEMA:
        arq = arq_win if sys.platform == "win32" else arq_mac
        if pastas is None or (arq and any((p / arq).exists() for p in pastas)):
            sistema.append({"nome": nome, "arquivo": None})
    usuario = fontes_usuario()
    vistos = {f["nome"] for f in usuario}
    return usuario + [f for f in sistema if f["nome"] not in vistos]


def copiar_fontes(tmp: Path) -> bool:
    """Copia as fontes enviadas por você para tmp/fontes (o filtro ass= usa caminho relativo: no Windows um
    caminho com 'E:' quebra o filtro). Devolve True se há alguma."""
    fontes = [p for p in pasta_fontes().iterdir() if p.suffix.lower() in EXTENSOES_FONTE]
    if not fontes:
        return False
    destino = tmp / "fontes"
    destino.mkdir(exist_ok=True)
    for p in fontes:
        if not (destino / p.name).exists():
            shutil.copy2(p, destino / p.name)
    return True


# ------------------------------------------------------------------ linha do tempo

def segmentos_arquivo(edicao: dict, base: float, duracao_arquivo: float) -> list[tuple[float, float]]:
    """Trechos da edição em segundos do ARQUIVO baixado (tira o que ficou fora do arquivo)."""
    out = []
    for s in edicao["segmentos"]:
        i, f = max(0.0, s["i"] - base), min(duracao_arquivo, s["f"] - base)
        if f - i >= 0.1:
            out.append((round(i, 3), round(f, 3)))
    if not out:
        raise ValueError("nenhum trecho da edição cai dentro do vídeo baixado")
    return out


def duracao(segs: list[tuple[float, float]]) -> float:
    return sum(f - i for i, f in segs)


def remapear(itens: list[dict], segs: list[tuple[float, float]]) -> list[dict]:
    """Palavras/frases {i, f, ...} em segundos do arquivo -> na linha do tempo do vídeo editado.
    Um item que aparece em dois trechos (trecho repetido) sai duas vezes; o que caiu num corte some."""
    out, deslocamento = [], 0.0
    for a, b in segs:
        for w in itens:
            if a <= w["i"] < b:
                out.append({**w, "i": round(w["i"] - a + deslocamento, 3),
                            "f": round(min(w["f"], b) - a + deslocamento, 3)})
        deslocamento += b - a
    return sorted(out, key=lambda w: w["i"])


def filtro_segmentos(segs: list[tuple[float, float]], tem_audio: bool) -> str:
    """trim + concat dos trechos: gera [vc] (e [ac]) a partir de [0:v]/[0:a]."""
    n = len(segs)
    partes, pares = [], []
    if n == 1:
        a, b = segs[0]
        f = f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS[vc]"
        if tem_audio:
            f += f";[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[ac]"
        return f
    partes.append(f"[0:v]split={n}" + "".join(f"[vs{k}]" for k in range(n)))
    if tem_audio:
        partes.append(f"[0:a]asplit={n}" + "".join(f"[as{k}]" for k in range(n)))
    for k, (a, b) in enumerate(segs):
        partes.append(f"[vs{k}]trim=start={a}:end={b},setpts=PTS-STARTPTS[v{k}]")
        pares.append(f"[v{k}]")
        if tem_audio:
            partes.append(f"[as{k}]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a{k}]")
            pares.append(f"[a{k}]")
    saida = "[vc][ac]" if tem_audio else "[vc]"
    partes.append(f"{''.join(pares)}concat=n={n}:v=1:a={1 if tem_audio else 0}{saida}")
    return ";".join(partes)


# ------------------------------------------------------------------ layout livre

def _caixa_px(c: dict) -> tuple[int, int, int, int]:
    """Caixa em frações do vertical -> (w, h, x, y) em pixels pares (x/y podem ser negativos: sai da tela)."""
    w, h = _par(c["w"] * L), _par(c["h"] * A)
    return w, h, int(round(c["x"] * L)), int(round(c["y"] * A))


def _cobrir(entrada: str, fonte: dict, sw: int, sh: int, w: int, h: int, saida: str, extra: str = "") -> str:
    cw, ch, cx, cy = regiao_px(fonte, sw, sh)
    return (f"[{entrada}]{extra}crop={cw}:{ch}:{cx}:{cy},scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1[{saida}]")


def _atraso(seg: float) -> str:
    """Filtro que adianta/atrasa a trilha do streamer (completa as pontas repetindo o quadro)."""
    if abs(seg) < 0.01:
        return ""
    if seg > 0:
        return f"tpad=start_duration={seg:.3f}:start_mode=clone,"
    return f"trim=start={-seg:.3f},setpts=PTS-STARTPTS,tpad=stop_duration={-seg:.3f}:stop_mode=clone,"


def montar_livre(sw: int, sh: int, edicao: dict, cam: dict | None, jogo: dict | None,
                 fundo_arquivo: str | None) -> Montagem:
    """Layout do editor: fundo (desfocado/preto/imagem) + jogo e webcam onde você colocou.
    `cam`/`jogo` = recorte do corte (a edição pode ter o próprio recorte do jogo)."""
    lay = edicao["layout"]
    zj, zc = lay["jogo"], lay.get("webcam")
    fonte_jogo = zj.get("fonte") or jogo or QUADRO
    fonte_cam = (zc.get("fonte") or cam) if zc else None
    mostrar_cam = bool(zc and fonte_cam)
    atraso = 0.0 if edicao.get("sincronizado", True) else float(edicao.get("atraso_streamer") or 0)

    jw, jh, jx, jy = _caixa_px(zj["saida"])
    tipo_fundo = lay.get("fundo", "desfocado")
    if tipo_fundo == "imagem" and not fundo_arquivo:
        tipo_fundo = "desfocado"
    ramos = ["jogo_in"] + (["fundo_in"] if tipo_fundo == "desfocado" else []) + (["cam_in"] if mostrar_cam else [])
    f = [f"[0:v]split={len(ramos)}" + "".join(f"[{r}]" for r in ramos)] if len(ramos) > 1 else \
        ["[0:v]null[jogo_in]"]
    entradas = []
    if tipo_fundo == "desfocado":
        f.append(_cobrir("fundo_in", fonte_jogo, sw, sh, L, A, "fundo0").replace(
            ",setsar=1[fundo0]", ",boxblur=24:2,eq=brightness=-0.12,setsar=1[fundo]"))
    elif tipo_fundo == "imagem":
        entradas = [fundo_arquivo]
        f.append(f"[1:v]scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A},setsar=1,format=yuv420p[fundo]")
    else:
        f.append(f"color=c=black:s={L}x{A}:r=30,format=yuv420p[fundo]")
    f.append(_cobrir("jogo_in", fonte_jogo, sw, sh, jw, jh, "jogo"))
    camadas = [("jogo", jx, jy)]
    if mostrar_cam:
        cw, ch, cx, cy = _caixa_px(zc["saida"])
        f.append(_cobrir("cam_in", fonte_cam, sw, sh, cw, ch, "cam", _atraso(atraso)))
        camadas.append(("cam", cx, cy))
        if not lay.get("webcam_na_frente", True):
            camadas.reverse()
    atual = "fundo"
    for k, (nome, x, y) in enumerate(camadas):
        prox = "base" if k == len(camadas) - 1 else f"c{k}"
        curto = ":shortest=1" if k == 0 else ""
        f.append(f"[{atual}][{nome}]overlay={x}:{y}{curto}" + (",setsar=1" if prox == "base" else "") + f"[{prox}]")
        atual = prox
    leg, gan = edicao.get("legenda") or {}, edicao.get("gancho") or {}
    return Montagem(";".join(f), legenda_y=int(A * float(leg.get("y", 0.55))), gancho_y=int(A * float(gan.get("y", 0.05))),
                    entradas=entradas, sem_webcam=not mostrar_cam)


def mostra_webcam(edicao: dict | None) -> bool:
    return bool(edicao and (edicao.get("layout") or {}).get("webcam"))


# ------------------------------------------------------------------ ponto de partida (como o modelo deixaria)

def _caixa(x, y, w, h) -> dict:
    return {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)}


def _divisao(params: dict, padrao: float) -> float:
    return max(0.2, min(0.8, float(params.get("divisao") or padrao)))


def layout_do_modelo(modelo: dict, sw: int, sh: int, cam: dict | None, jogo: dict | None,
                     tem_fundo: bool) -> dict:
    """Converte o layout do modelo de corte em caixas do editor (o vídeo sai igual ao que o modelo faria)."""
    p, nome = modelo.get("params") or {}, modelo["layout"]
    precisa = LAYOUTS[nome].opcoes.get("precisa_webcam") if nome in LAYOUTS else False
    contido = lambda r: _par(L * regiao_px(r, sw, sh)[1] / regiao_px(r, sw, sh)[0]) / A  # noqa: E731

    if precisa and not cam:  # o layout fica "sem webcam": jogo inteiro no meio, fundo desfocado
        h = min(1.0, contido(jogo))
        return {"jogo": {"saida": _caixa(0, (1 - h) / 2, 1, h), "fonte": jogo}, "webcam": None, "fundo": "desfocado"}
    if nome == "jogo_em_cima":
        d = _divisao(p, 0.55)
        fj = _jogo_sem_a_webcam(jogo, cam, sw, sh, L, _par(A * d))
        return {"jogo": {"saida": _caixa(0, 0, 1, d), "fonte": fj}, "webcam": {"saida": _caixa(0, d, 1, 1 - d)},
                "fundo": "preto"}
    if nome == "webcam_em_cima":
        d = _divisao(p, 0.36)
        fj = _jogo_sem_a_webcam(jogo, cam, sw, sh, L, A - _par(A * d))
        return {"jogo": {"saida": _caixa(0, d, 1, 1 - d), "fonte": fj}, "webcam": {"saida": _caixa(0, 0, 1, d)},
                "fundo": "preto"}
    if nome == "tela_cheia":
        h = contido(None)
        return {"jogo": {"saida": _caixa(0, (1 - h) / 2, 1, h), "fonte": None}, "webcam": None, "fundo": "desfocado"}
    if nome == "fundo_imagem":
        base = _par(A * _divisao(p, 0.62)) if cam else A
        jw_, jh_, _, _ = regiao_px(jogo, sw, sh)
        vw = L - 80
        vh = _par(vw * jh_ / jw_)
        topo_fixo = p.get("topo")
        topo = _par(A * max(0.0, min(0.4, float(topo_fixo)))) if topo_fixo is not None else 60
        espaco = base - topo - 160
        if vh > espaco:
            vh = _par(espaco)
            vw = _par(vh * jw_ / jh_)
        if topo_fixo is None:
            topo = _par(max(60, (base - vh - 160) / 2))
        r = {"jogo": {"saida": _caixa((L - vw) / 2 / L, topo / A, vw / L, vh / A), "fonte": jogo},
             "webcam": {"saida": _caixa(0, base / A, 1, 1 - base / A)} if cam else None,
             "fundo": "imagem" if tem_fundo else "desfocado"}
        return r
    # so_gameplay e layouts sem webcam
    return {"jogo": {"saida": _caixa(0, 0, 1, 1), "fonte": jogo}, "webcam": None, "fundo": "preto"}


def edicao_padrao(c: dict, modelo: dict, montagem: Montagem, sw: int, sh: int, cam: dict | None,
                  tem_fundo: bool) -> dict:
    """Edição inicial = exatamente o que o modelo de corte geraria (o editor parte daqui)."""
    estilo_id = c.get("estilo_legenda") or modelo["estilo_legenda"]
    e = ESTILOS[estilo_id].opcoes if estilo_id in ESTILOS else ESTILOS["destaque"].opcoes
    legenda = {"fonte": e.get("fonte", "Arial Black"), "tamanho": e.get("tamanho", 74), "cor": e.get("cor", "FFFFFF"),
               "destaque": e.get("destaque", "FFE400"), "contorno": e.get("contorno", 7),
               "maiusculas": bool(e.get("maiusculas", True)), "por_bloco": e.get("por_bloco", 3),
               "y": round(montagem.legenda_y / A, 4), "mostrar": not e.get("nenhuma")}
    lay = layout_do_modelo(modelo, sw, sh, cam, c.get("jogo"), tem_fundo)
    return {"segmentos": [{"i": c["inicio"], "f": c["fim"]}], "sincronizado": True, "atraso_streamer": 0.0,
            "legenda": legenda, "gancho": {"fonte": "Arial Black", "tamanho": 64, "cor": "000000", "fundo": "FFFFFF",
                                            "y": round(montagem.gancho_y / A, 4)},
            "layout": {**lay, "webcam_na_frente": True}}
