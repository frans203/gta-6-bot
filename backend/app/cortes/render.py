"""Renderiza um corte: baixa o trecho -> acha a webcam (ou pede enquadramento manual) -> transcreve -> monta o
vertical do modelo de corte com legenda -> mp4 sem metadados. Também gera a prévia (1 quadro) de um modelo."""
import json
import shutil
import subprocess
from pathlib import Path

from ..config import config
from . import fontes, legendas, midia, servico, traducao, webcam
from .layouts import A, L, Montagem
from .plugins import LAYOUTS, carregar

# posição sugerida no editor quando não há nada detectado (canto inferior direito, comum em lives)
WEBCAM_EXEMPLO = {"x": 0.7, "y": 0.65, "w": 0.28, "h": 0.3}


def pasta_tmp(nome: str) -> Path:
    p = config.midia / "tmp" / nome
    p.mkdir(parents=True, exist_ok=True)
    return p


def caminho_quadro(streamer_id: int) -> Path:
    return config.midia / "quadros" / f"streamer_{streamer_id}.jpg"


def credito(st) -> str:
    """Crédito escrito no vídeo (o streamer sempre aparece)."""
    return {"twitch": f"twitch.tv/{st.canal}", "youtube": f"youtube.com/{st.canal}",
            "kick": f"kick.com/{st.canal}"}.get(st.plataforma, st.nome)


def sem_webcam(c: dict) -> bool:
    """O enquadramento concluiu que este corte não tem o streamer na tela (ou o usuário disse isso)."""
    return (c.get("extra") or {}).get("webcam") == "nenhuma"


def webcam_confirmada(cam: dict | None) -> bool:
    """Webcam detectada com confiança ou marcada à mão (sugestões fracas não contam)."""
    return bool(cam) and cam.get("origem") in ("auto", "manual")


# ------------------------------------------------------------------ montagem (render e prévia)

def caminho_fundo(nome: str | None) -> Path | None:
    """Imagem de fundo enviada pelo usuário (midia/fundos/<nome>), se existir."""
    if not nome:
        return None
    p = config.midia / "fundos" / Path(nome).name
    return p if p.exists() else None


def montar(sw: int, sh: int, modelo: dict, cam: dict | None, jogo: dict | None,
           fundo: str | None = None) -> Montagem:
    """Monta o filtro do layout do modelo. `fundo` (nome do arquivo) troca a imagem de fundo do modelo."""
    p = dict(modelo.get("params") or {})
    arquivo = caminho_fundo(fundo or p.get("fundo"))
    if arquivo:
        p["fundo_arquivo"] = str(arquivo)
    m = LAYOUTS[modelo["layout"]].funcao(sw, sh, cam, jogo, p)
    if m.sem_webcam:  # as posições do modelo foram pensadas com a webcam: usa as do próprio layout
        p = {}
    if p.get("legenda_y") is not None:
        m.legenda_y = int(A * float(p["legenda_y"]))
    if p.get("gancho_y") is not None:
        m.gancho_y = int(A * float(p["gancho_y"]))
    m.legenda_y = max(80, min(A - 80, m.legenda_y))
    m.gancho_y = max(20, min(A - 200, m.gancho_y))
    return m


def _filtro_final(montagem: Montagem, modelo: dict, dur: float | None) -> str:
    f = f"{montagem.filtro};[base]ass=legenda.ass[leg]"
    if dur and (modelo.get("params") or {}).get("barra", True):
        return (f"{f};color=c=0xFFE45C:s={L}x10:r=30,format=rgba[barra];"
                f"[leg][barra]overlay=x='-w+w*t/{dur:.3f}':y={A - 10}:shortest=1[v]")
    return f"{f};[leg]null[v]"


def _ass(palavras, estilo, montagem, modelo, dur, gancho, credito_txt) -> str:
    mostrar_credito = (modelo.get("params") or {}).get("credito", True)
    return legendas.gerar_ass(palavras, estilo, montagem.legenda_y, montagem.gancho_y, dur, gancho=gancho,
                              credito=credito_txt if mostrar_credito else None)


def _entradas_extras(montagem: Montagem) -> list[str]:
    args = []
    for e in montagem.entradas:
        args += ["-loop", "1", "-i", e]
    return args


def previa(modelo: dict, quadro: Path | None, cam: dict | None = None, jogo: dict | None = None,
           estilo: str | None = None, gancho: str | None = None, credito_txt: str = "twitch.tv/streamer",
           fundo: str | None = None, exemplo_webcam: bool = True) -> bytes:
    """Um quadro 1080x1920 (JPEG) exatamente como o render faria (mesmo filtro e mesma legenda .ass)."""
    carregar()
    tmp = pasta_tmp("previa")
    if quadro and quadro.exists():
        import cv2
        img = cv2.imread(str(quadro))
        sh, sw = img.shape[:2]
        entrada = ["-i", str(quadro)]
    else:
        sw, sh = 1920, 1080
        entrada = ["-f", "lavfi", "-i", f"testsrc2=s={sw}x{sh}:d=1"]
    if LAYOUTS[modelo["layout"]].opcoes.get("precisa_webcam") and not cam and exemplo_webcam:
        cam = WEBCAM_EXEMPLO
    montagem = montar(sw, sh, modelo, cam, jogo, fundo)
    exemplo = "olha isso aqui que coisa".split()
    palavras = [{"p": p, "i": i * 0.3, "f": i * 0.3 + 0.28} for i, p in enumerate(exemplo)]
    (tmp / "legenda.ass").write_text(_ass(palavras, estilo or modelo["estilo_legenda"], montagem, modelo, 5.0,
                                          gancho, credito_txt), "utf-8")
    saida = tmp / "previa.jpg"
    cmd = ["ffmpeg", "-hide_banner", "-v", "error", "-y", *entrada, *_entradas_extras(montagem), "-filter_complex",
           _filtro_final(montagem, modelo, None), "-map", "[v]", "-frames:v", "1", "-q:v", "4", str(saida)]
    r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       creationflags=midia.SEM_JANELA)
    if r.returncode:
        raise RuntimeError("ffmpeg falhou na prévia: " + r.stderr.strip()[-800:])
    return saida.read_bytes()


# ------------------------------------------------------------------ preparo (trecho + quadro + webcam)

def _trecho(c: dict, tmp: Path, progresso, log) -> tuple[Path, dict, float, float]:
    """Baixa o trecho do corte (reaproveita se já baixou o mesmo trecho). Devolve (arquivo, info, ini, dur)."""
    bruto, meta = tmp / "trecho.mp4", tmp / "trecho.json"
    inteiro = c["fonte_tipo"] == "clipe"
    chave = {"url": c["fonte_url"], "inicio": None if inteiro else c["inicio"], "fim": None if inteiro else c["fim"]}
    if bruto.exists() and meta.exists() and json.loads(meta.read_text("utf-8")) == chave:
        log("trecho já baixado: reaproveitando")
    else:
        progresso(0.02, "baixando o trecho")
        fontes.baixar_trecho(c["fonte_url"], chave["inicio"], chave["fim"], bruto,
                             ao_progresso=lambda f: progresso(0.02 + f * 0.3, "baixando o trecho"))
        meta.write_text(json.dumps(chave), "utf-8")
    info = midia.ffprobe(bruto)
    if inteiro:  # clipe: o corte pode ter sido aparado na revisão
        ini_rel, dur = c["inicio"], min(c["fim"], info["duracao"]) - c["inicio"]
    else:
        ini_rel, dur = 0.0, info["duracao"]
    log(f"trecho: {info['largura']}x{info['altura']} {info['duracao']:.1f}s")
    return bruto, info, ini_rel, dur


def _salvar_quadro(bruto: Path, destino: Path, t: float):
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(bruto),
                    "-frames:v", "1", "-q:v", "3", str(destino)], check=True, capture_output=True,
                   creationflags=midia.SEM_JANELA)


def analisar_trecho(c: dict, bruto: Path, tmp: Path, ini_rel: float, dur: float, progresso, log) -> dict:
    """Barras pretas (vira a área do jogo, se ninguém marcou) e idioma falado (uma vez por fonte).
    Guarda em corte.extra e devolve o extra atualizado."""
    extra = dict(c.get("extra") or {})
    campos = {}
    if "espaco_preto" not in extra:
        progresso(0.33, "medindo as barras pretas")
        area = midia.area_util(bruto, 2 * ini_rel + dur)  # amostra no meio do trecho
        if area:
            extra["espaco_preto"] = area.pop("espaco_preto")
            extra["area_util"] = area
            if extra["espaco_preto"] >= 0.08 and not c["jogo"]:
                campos["jogo"] = area  # o jogo é só a parte com imagem
            log(f"espaço preto: {extra['espaco_preto']:.0%}")
    idioma = c.get("fonte_idioma")
    if not idioma and midia.ffprobe(bruto)["tem_audio"]:
        progresso(0.34, "descobrindo o idioma falado")
        wav = midia.extrair_wav(bruto, tmp / "audio.wav")
        idioma, prob = legendas.detectar_idioma(wav)
        servico.atualizar_fonte_extra(c["fonte_id"], idioma=idioma, idioma_prob=prob)
        log(f"idioma falado: {idioma} ({prob:.0%})")
    if idioma:
        extra["idioma"] = idioma
    servico.atualizar_corte(c["id"], extra=extra, **campos)
    c.update(extra=extra, fonte_idioma=idioma, **campos)
    return extra


def enquadrar(c: dict, bruto: Path, ini_rel: float, dur: float, progresso, log) -> tuple[str, dict | None]:
    """Decide a webcam do corte. Devolve (situação, webcam):
      'ok'       webcam identificada (ou marcada à mão): monta com o streamer
      'nenhuma'  não há webcam no vídeo: segue o fluxo, monta sem a parte do streamer
      'duvida'   há uma câmera fixa, mas a posição é incerta: o corte fica 'enquadrar' e o usuário recorta
    """
    quadro = servico.caminho_quadro_corte(c["id"])
    cam = c["webcam"]
    if webcam_confirmada(cam) or sem_webcam(c):
        if not quadro.exists():
            _salvar_quadro(bruto, quadro, ini_rel + dur / 2)
        return ("ok", cam) if webcam_confirmada(cam) else ("nenhuma", None)
    progresso(0.34, "procurando a webcam do streamer")
    det = webcam.detectar(bruto, salvar_quadro=quadro)
    if not quadro.exists():
        _salvar_quadro(bruto, quadro, ini_rel + dur / 2)
    situacao = webcam.classificar(det)
    if situacao == "auto":
        cam = {**det, "origem": "auto"}
        servico.atualizar_corte(c["id"], webcam=cam)
        servico.atualizar_streamer(c["streamer_id"], {"webcam": {k: det[k] for k in "xywh"}})  # sugestão futura
        log(f"webcam detectada (confiança {det['confianca']:.0%}): {cam}")
        return "ok", cam
    if situacao == "duvida":
        servico.atualizar_corte(c["id"], webcam={**det, "origem": "sugerida"}, status="enquadrar", erro=None)
        log(f"há uma webcam, mas a posição é incerta (rosto fixo em {det['confianca']:.0%} das amostras): "
            "confira/recorte na revisão")
        return "duvida", None
    extra = {**(c.get("extra") or {}), "webcam": "nenhuma"}
    servico.atualizar_corte(c["id"], webcam=None, extra=extra)
    c.update(webcam=None, extra=extra)
    log("sem webcam neste trecho: o corte sai sem a parte do streamer")
    return "nenhuma", None


def modelo_do_corte(c: dict) -> dict:
    return servico.obter_modelo(c["modelo_id"] or c.get("streamer_modelo_id"))


def preparar_enquadramento(corte_id: int, progresso=lambda f, m=None: None, log=print) -> dict:
    """Só baixa o trecho, salva o quadro e tenta achar a webcam (para conferir antes de renderizar)."""
    carregar()
    c = servico.obter_corte(corte_id)
    tmp = pasta_tmp(f"corte_{corte_id}")
    bruto, _info, ini_rel, dur = _trecho(c, tmp, progresso, log)
    extra = analisar_trecho(c, bruto, tmp, ini_rel, dur, progresso, log)
    if not LAYOUTS[modelo_do_corte(c)["layout"]].opcoes.get("precisa_webcam"):
        # o modelo atual não mostra a webcam, mas procura o streamer mesmo assim: se achar, a tela oferece trocar
        # para um modelo com o streamer (e a posição já fica guardada no corte)
        quadro = servico.caminho_quadro_corte(corte_id)
        cam = c["webcam"] if webcam_confirmada(c["webcam"]) else None
        if cam is None:
            progresso(0.4, "procurando a webcam do streamer")
            det = webcam.detectar(bruto, salvar_quadro=quadro)
            if webcam.classificar(det) == "auto":
                cam = {**det, "origem": "auto"}
                servico.atualizar_corte(corte_id, webcam=cam)
                log(f"webcam detectada (confiança {det['confianca']:.0%}), mas o modelo atual não a usa")
        if not quadro.exists():
            _salvar_quadro(bruto, quadro, ini_rel + dur / 2)
        return {"webcam": cam, "situacao": "ok", "mensagem": "este modelo não usa webcam", **extra}
    situacao, cam = enquadrar(c, bruto, ini_rel, dur, progresso, log)
    progresso(1.0, "pronto")
    mensagem = {"ok": "webcam identificada", "nenhuma": "sem webcam: segue sem o streamer",
                "duvida": "webcam com posição incerta: recorte à mão"}[situacao]
    return {"webcam": cam, "situacao": situacao, "mensagem": mensagem, **extra}


# ------------------------------------------------------------------ render

def renderizar(corte_id: int, progresso=lambda f, m=None: None, log=print, checar=lambda: None) -> dict:
    carregar()
    c = servico.obter_corte(corte_id)
    st = servico.obter_streamer(c["streamer_id"])
    tmp = pasta_tmp(f"corte_{corte_id}")
    manter_tmp = False
    try:
        bruto, info, ini_rel, dur = _trecho(c, tmp, progresso, log)
        analisar_trecho(c, bruto, tmp, ini_rel, dur, progresso, log)
        checar()

        # 1) modelo + enquadramento
        modelo = modelo_do_corte(c)
        log(f"modelo: {modelo['nome']} ({modelo['layout']})")
        cam = None
        if LAYOUTS[modelo["layout"]].opcoes.get("precisa_webcam"):
            situacao, cam = enquadrar(c, bruto, ini_rel, dur, progresso, log)
            if situacao == "duvida":
                manter_tmp = True  # o trecho fica baixado para o render depois do recorte manual
                return {"enquadrar": True, "mensagem": "há uma webcam, mas a posição é incerta: recorte na revisão"}
        elif not servico.caminho_quadro_corte(corte_id).exists():
            _salvar_quadro(bruto, servico.caminho_quadro_corte(corte_id), ini_rel + dur / 2)
        montagem = montar(info["largura"], info["altura"], modelo, cam, c["jogo"], c["fundo"])
        checar()

        # 2) transcrição
        estilo = c["estilo_legenda"] or modelo["estilo_legenda"]
        transcricao = {"texto": "", "palavras": []}
        palavras = []
        if estilo != "sem_legenda" and info["tem_audio"]:
            progresso(0.4, "transcrevendo (Whisper local)")
            wav = midia.extrair_wav(bruto, tmp / "audio.wav")
            falado = c.get("fonte_idioma") or st.idioma
            transcricao = legendas.transcrever(wav, falado)
            log(f"transcrição ({transcricao.get('dispositivo')}): {transcricao['texto'][:120]}")
            palavras = [{**w, "i": w["i"] - ini_rel, "f": w["f"] - ini_rel} for w in transcricao["palavras"]
                        if ini_rel <= w["i"] < ini_rel + dur]
            alvo = c.get("idioma_legenda")
            if alvo and alvo != falado:
                progresso(0.55, f"traduzindo a legenda ({falado} -> {alvo})")
                frases = [{**x, "i": max(0.0, x["i"] - ini_rel), "f": min(dur, x["f"] - ini_rel)}
                          for x in transcricao["segmentos"] if x["f"] > ini_rel and x["i"] < ini_rel + dur]
                palavras = traducao.traduzir_palavras(frases, falado, alvo)
                log(f"legenda traduzida: {' '.join(w['p'] for w in palavras)[:120]}")
        checar()

        # 3) legenda .ass + render
        (tmp / "legenda.ass").write_text(_ass(palavras, estilo, montagem, modelo, dur, c["gancho"], credito(st)),
                                         "utf-8")
        saida = servico.pasta_renderizados() / f"{servico.slug(st.nome)}_{corte_id:05d}.mp4"
        args = ["-ss", f"{ini_rel:.3f}", "-t", f"{dur:.3f}", "-i", str(bruto), *_entradas_extras(montagem),
                "-filter_complex",
                _filtro_final(montagem, modelo, dur), "-map", "[v]"]
        if info["tem_audio"]:
            args += ["-map", "0:a:0", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k",
                     "-ar", "48000"]
        args += [*midia.codificador(), "-pix_fmt", "yuv420p", "-map_metadata", "-1", "-map_chapters", "-1",
                 "-metadata", "encoder=", "-movflags", "+faststart", "-t", f"{dur:.3f}", str(saida)]
        progresso(0.6, "montando o vídeo vertical")
        midia.rodar(args, duracao=dur, cwd=tmp, ao_progresso=lambda f: progresso(0.6 + f * 0.38, "codificando"))

        titulo = c["titulo"] or c["fonte_titulo"]
        servico.atualizar_corte(corte_id, status="pronto", arquivo=str(saida), titulo=titulo, erro=None,
                                transcricao={"texto": transcricao.get("texto", ""), "palavras": palavras})
        progresso(1.0, "pronto")
        return {"arquivo": str(saida), "duracao": round(dur, 1), "modelo": modelo["nome"], "webcam": cam}
    finally:
        if not manter_tmp:
            shutil.rmtree(tmp, ignore_errors=True)
