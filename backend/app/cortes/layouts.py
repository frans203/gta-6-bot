"""Layouts verticais (1080x1920). Cada layout devolve um trecho de filter_complex do ffmpeg que termina em [base]
e as posições padrão da legenda e do gancho. Para criar um layout novo, registre uma função com @LAYOUTS.registrar.

Assinatura: funcao(sw, sh, cam, jogo, params) -> Montagem
  sw, sh   tamanho do vídeo de origem
  cam      retângulo da webcam {x,y,w,h} em frações do quadro (None = não marcada)
  jogo     retângulo da gameplay {x,y,w,h} em frações (None = quadro inteiro, recorte central)
  params   parâmetros do modelo de corte (ex.: divisao = fração da altura que fica com o jogo;
           fundo_arquivo = caminho da imagem de fundo, quando o layout usa uma)
Cada região é recortada e preenche o espaço dela "cobrindo" (corta o excesso no centro, sem distorcer).
"""
from dataclasses import dataclass, field

from .plugins import LAYOUTS

L, A = 1080, 1920
QUADRO_INTEIRO = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}


@dataclass
class Montagem:
    filtro: str          # filter_complex que gera [base]
    legenda_y: int       # centro vertical padrão da legenda
    gancho_y: int        # topo padrão do texto de gancho
    entradas: list[str] = field(default_factory=list)  # imagens extras (viram [1:v], [2:v]... no filtro)
    sem_webcam: bool = False  # montado sem a parte do streamer: as posições do modelo não valem


def _par(n: float) -> int:
    return max(2, int(n) // 2 * 2)


def regiao_px(r: dict | None, sw: int, sh: int) -> tuple[int, int, int, int]:
    """Retângulo em frações -> (w, h, x, y) em pixels pares, dentro do quadro."""
    r = r or QUADRO_INTEIRO
    x, y = _par(max(0.0, min(1.0, r["x"])) * sw), _par(max(0.0, min(1.0, r["y"])) * sh)
    w = _par(min(r["w"] * sw, sw - x))
    h = _par(min(r["h"] * sh, sh - y))
    return w, h, x, y


def _preencher(entrada: str, r: dict | None, sw: int, sh: int, w: int, h: int, saida: str) -> str:
    """Recorta a região r e faz ela cobrir w x h (sem distorcer)."""
    cw, ch, cx, cy = regiao_px(r, sw, sh)
    return (f"[{entrada}]crop={cw}:{ch}:{cx}:{cy},scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}[{saida}]")


def _jogo_sem_a_webcam(jogo: dict | None, cam: dict, sw: int, sh: int, w: int, h: int) -> dict | None:
    """Sem área do jogo marcada, o recorte é o centro do quadro. Se a webcam (num canto) invade esse recorte, empurra
    o recorte para o outro lado, para o streamer não aparecer duas vezes (na gameplay e embaixo)."""
    if jogo or cam["w"] > 0.4:
        return jogo
    cw = min(sw, sh * w / h)
    x0 = (sw - cw) / 2
    c0, c1 = cam["x"] * sw, (cam["x"] + cam["w"]) * sw
    if (c0 + c1) / 2 < sw / 2 and c1 > x0:          # webcam à esquerda
        x0 = min(c1, sw - cw)
    elif (c0 + c1) / 2 >= sw / 2 and c0 < x0 + cw:  # webcam à direita
        x0 = max(0.0, c0 - cw)
    else:
        return None
    return {"x": x0 / sw, "y": 0.0, "w": cw / sw, "h": 1.0}


def _divisao(params: dict, padrao: float) -> int:
    d = float(params.get("divisao") or padrao)
    return _par(A * max(0.2, min(0.8, d)))


def _sem_webcam(sw: int, sh: int, jogo: dict | None, params: dict | None) -> Montagem:
    """Corte sem o streamer (câmera desligada ou vídeo sem webcam): o jogo inteiro no meio, com o próprio
    vídeo desfocado atrás."""
    jw, jh, jx, jy = regiao_px(jogo, sw, sh)
    f = (f"[0:v]split=2[fundo_in][frente_in];"
         f"[fundo_in]crop={jw}:{jh}:{jx}:{jy},scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A},"
         f"boxblur=24:2,eq=brightness=-0.12[fundo];"
         f"[frente_in]crop={jw}:{jh}:{jx}:{jy},scale={L}:-2[frente];"
         f"[fundo][frente]overlay=(W-w)/2:(H-h)/2,setsar=1[base]")
    altura = int(L * jh / jw)
    return Montagem(f, legenda_y=min(A - 260, (A + altura) // 2 + 170), gancho_y=max(80, (A - altura) // 2 - 300),
                    sem_webcam=True)


@LAYOUTS.registrar("jogo_em_cima", "Jogo em cima + streamer embaixo",
                   "Gameplay na parte de cima e a webcam do streamer embaixo. A divisão entre os dois é ajustável "
                   "no modelo. Sem webcam no vídeo, sai o jogo inteiro com fundo desfocado.",
                   precisa_webcam=True, usa_jogo=True, usa_divisao=True)
def jogo_em_cima(sw: int, sh: int, cam: dict | None, jogo: dict | None = None, params: dict | None = None) -> Montagem:
    if not cam:
        return _sem_webcam(sw, sh, jogo, params)
    hj = _divisao(params or {}, 0.55)
    jogo = _jogo_sem_a_webcam(jogo, cam, sw, sh, L, hj)
    f = (f"[0:v]split=2[jogo_in][cam_in];"
         f"{_preencher('jogo_in', jogo, sw, sh, L, hj, 'jogo')};"
         f"{_preencher('cam_in', cam, sw, sh, L, A - hj, 'cam')};"
         f"[jogo][cam]vstack=inputs=2,setsar=1[base]")
    return Montagem(f, legenda_y=hj, gancho_y=90)


@LAYOUTS.registrar("webcam_em_cima", "Webcam em cima + jogo embaixo",
                   "Rosto do streamer no topo e a gameplay embaixo. Sem webcam no vídeo, sai o jogo inteiro.",
                   precisa_webcam=True, usa_jogo=True, usa_divisao=True)
def webcam_em_cima(sw: int, sh: int, cam: dict | None, jogo: dict | None = None,
                   params: dict | None = None) -> Montagem:
    if not cam:
        return _sem_webcam(sw, sh, jogo, params)
    hc = _divisao(params or {}, 0.36)
    jogo = _jogo_sem_a_webcam(jogo, cam, sw, sh, L, A - hc)
    f = (f"[0:v]split=2[cam_in][jogo_in];"
         f"{_preencher('cam_in', cam, sw, sh, L, hc, 'cam')};"
         f"{_preencher('jogo_in', jogo, sw, sh, L, A - hc, 'jogo')};"
         f"[cam][jogo]vstack=inputs=2,setsar=1[base]")
    return Montagem(f, legenda_y=hc, gancho_y=90)


@LAYOUTS.registrar("so_gameplay", "Só o jogo (recorte 9:16)",
                   "Recorta um pedaço do quadro em 9:16 (o centro, ou a área marcada como jogo).", usa_jogo=True)
def so_gameplay(sw: int, sh: int, cam: dict | None, jogo: dict | None = None, params: dict | None = None) -> Montagem:
    return Montagem(f"{_preencher('0:v', jogo, sw, sh, L, A, 'cheio')};[cheio]setsar=1[base]",
                    legenda_y=1300, gancho_y=160)


@LAYOUTS.registrar("tela_cheia", "Vídeo inteiro + fundo desfocado",
                   "Mostra o quadro 16:9 inteiro no meio, com o próprio vídeo desfocado atrás. "
                   "Não perde nada da tela; bom para Just Chatting e reacts.")
def tela_cheia(sw: int, sh: int, cam: dict | None, jogo: dict | None = None, params: dict | None = None) -> Montagem:
    f = (f"[0:v]split=2[fundo_in][frente_in];"
         f"[fundo_in]scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A},boxblur=24:2,"
         f"eq=brightness=-0.12[fundo];"
         f"[frente_in]scale={L}:-2[frente];"
         f"[fundo][frente]overlay=(W-w)/2:(H-h)/2,setsar=1[base]")
    altura_video = int(L * sh / sw)
    return Montagem(f, legenda_y=min(A - 260, (A + altura_video) // 2 + 170),
                    gancho_y=max(80, (A - altura_video) // 2 - 300))


@LAYOUTS.registrar("fundo_imagem", "Imagem de fundo + vídeo + streamer embaixo",
                   "Sua imagem de fundo (backdrop) ocupando a tela, o vídeo inteiro em cima (sem cortar e sem as "
                   "barras pretas), a legenda logo abaixo dele e a webcam do streamer embaixo. Ideal quando o "
                   "vídeo tem muito espaço preto. Sem imagem, usa o próprio vídeo desfocado como fundo. "
                   "Sem webcam, o vídeo fica centralizado.",
                   precisa_webcam=True, usa_jogo=True, usa_divisao=True, usa_fundo=True)
def fundo_imagem(sw: int, sh: int, cam: dict | None, jogo: dict | None = None,
                 params: dict | None = None) -> Montagem:
    params = params or {}
    base = _divisao(params, 0.62) if cam else A         # onde começa a webcam (sem webcam: o vídeo usa a tela)
    margem = 40
    jw, jh, jx, jy = regiao_px(jogo, sw, sh)
    # vídeo "contido": cabe na largura (com margem) e no espaço entre o topo e a webcam
    vw = L - 2 * margem
    vh = _par(vw * jh / jw)
    topo_fixo = params.get("topo")
    topo = _par(A * max(0.0, min(0.4, float(topo_fixo)))) if topo_fixo is not None else 60
    espaco = base - topo - 160                           # deixa lugar para a legenda embaixo do vídeo
    if vh > espaco:
        vh = _par(espaco)
        vw = _par(vh * jw / jh)
    if topo_fixo is None:                                # centraliza vídeo + legenda acima da webcam
        topo = _par(max(60, (base - vh - 160) / 2))
    vx = (L - vw) // 2
    entradas, f = [], ""
    if params.get("fundo_arquivo"):
        entradas = [params["fundo_arquivo"]]
        f += (f"[1:v]scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A},setsar=1,"
              f"format=yuv420p[fundo];[0:v]split=2[jogo_in][cam_in];")
    else:
        f += (f"[0:v]split=3[fundo_in][jogo_in][cam_in];"
              f"[fundo_in]scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A},boxblur=24:2,"
              f"eq=brightness=-0.15,setsar=1[fundo];")
    if cam:
        f += (f"[jogo_in]crop={jw}:{jh}:{jx}:{jy},scale={vw}:{vh},setsar=1[jogo];"
              f"{_preencher('cam_in', cam, sw, sh, L, A - base, 'cam')};"
              f"[fundo][jogo]overlay={vx}:{topo}[f1];"
              f"[f1][cam]overlay=0:{base},setsar=1[base]")
    else:
        f = f.replace("split=3[fundo_in][jogo_in][cam_in]", "split=2[fundo_in][jogo_in]").replace(
            "split=2[jogo_in][cam_in]", "null[jogo_in]")
        f += (f"[jogo_in]crop={jw}:{jh}:{jx}:{jy},scale={vw}:{vh},setsar=1[jogo];"
              f"[fundo][jogo]overlay={vx}:{topo},setsar=1[base]")
    legenda = min(base - 70, topo + vh + 75)
    return Montagem(f, legenda_y=legenda, gancho_y=max(20, topo - 120), entradas=entradas, sem_webcam=not cam)
