"""Jobs do cortador: buscar fontes, ler dados, analisar (achar destaques), detectar webcam, enquadrar, renderizar."""
import math
import shutil

from ..config import config
from ..jobs.fila import tarefa
from ..models import Fonte
from . import detectores, fontes, render, servico, vigia, webcam
from .plugins import DETECTORES, carregar


@tarefa("buscar_fontes", recurso=lambda p: "rede:busca")
def buscar_fontes(ctx, p):
    st = servico.obter_streamer(p["streamer_id"])
    ctx.progresso(None, f"procurando {p.get('tipo', 'vod')}s de {st.canal}")
    itens = fontes.listar_canal(st.plataforma, st.canal, p.get("tipo", "vod"), p.get("limite", 5),
                                p.get("periodo_dias", 7))
    ids = servico.salvar_fontes(st.id, itens)
    return {"encontradas": len(ids), "ids": ids}


@tarefa("info_fonte", recurso=lambda p: "rede:busca")
def info_fonte(ctx, p):
    f = servico.obter_fonte(p["fonte_id"])
    i = fontes.info(f.url)
    servico.atualizar_fonte(f.id, titulo=i["titulo"] or f.titulo, duracao=i["duracao"], views=i["views"],
                            publicado_em=i["publicado_em"], miniatura=i["miniatura"])
    return {"titulo": i["titulo"], "duracao": i["duracao"]}


class _Faixa:
    """Repassa o progresso de uma etapa para uma faixa [a, b] do progresso total do job."""

    def __init__(self, ctx, a: float, b: float):
        self.ctx, self.a, self.b = ctx, a, b
        self.log, self.checar = ctx.log, ctx.checar

    def progresso(self, f, m=None):
        self.ctx.progresso(None if f is None else self.a + (self.b - self.a) * f, m)


@tarefa("analisar_fonte", recurso=lambda p: "analise")
def analisar_fonte(ctx, p):
    return _analisar(ctx, p)


def _analisar(ctx, p):
    """Cria cortes candidatos. Clipe (ou vídeo curto): o vídeo todo. VOD: picos dos detectores."""
    carregar()
    f: Fonte = servico.obter_fonte(p["fonte_id"])
    st = servico.obter_streamer(f.streamer_id)
    servico.atualizar_fonte(f.id, status="analisando")
    try:
        if f.tipo == "clipe":
            dur = f.duracao or fontes.info(f.url)["duracao"] or 30
            cand = [{"inicio": 0.0, "fim": float(dur), "score": 1.0, "sinais": {"views": f.views or 0},
                     "titulo": f.titulo}]
        else:
            ctx.progresso(0.02, "lendo dados do vídeo")
            info = fontes.info(f.url)
            servico.atualizar_fonte(f.id, titulo=info["titulo"] or f.titulo, duracao=info["duracao"],
                                    views=info["views"], miniatura=info["miniatura"])
            dur_total = int(math.ceil(info["duracao"] or 0))
            if not dur_total:
                raise ValueError("vídeo sem duração (live ainda ao vivo?)")
        if f.tipo != "clipe" and dur_total <= int(p.get("duracao", 45)) * 1.3:
            # vídeo curto: o corte é o vídeo inteiro
            cand = [{"inicio": 0.0, "fim": float(dur_total), "score": 1.0, "sinais": {}, "titulo": f.titulo}]
        elif f.tipo != "clipe":
            cand = _detectar(ctx, p, f, st, info, dur_total)
        ctx.progresso(0.97, f"{len(cand)} trecho(s) encontrados")
        servico.substituir_candidatos(f.id, cand)
        servico.atualizar_fonte(f.id, status="analisada")
        return {"candidatos": len(cand)}
    except Exception:
        servico.atualizar_fonte(f.id, status="erro")
        raise


def trecho_da_analise(p: dict, f: Fonte, dur_total: int) -> tuple[int, int]:
    """Trecho pedido no job (inicio/fim em s); sem ele, o último usado nesta fonte; senão o vídeo inteiro."""
    t = {"inicio": p["inicio"], "fim": p["fim"]} if p.get("fim") else (f.extra or {}).get("trecho") or {}
    ini = int(max(0, t.get("inicio") or 0))
    fim = int(min(dur_total, t.get("fim") or dur_total))
    return (ini, fim) if fim - ini >= 60 else (0, dur_total)


def _detectar(ctx, p: dict, f: Fonte, st, info: dict, dur_total: int) -> list[dict]:
    """Roda os detectores no trecho escolhido, escolhe os picos e (se já houver exemplos) reordena pelo que o
    usuário costuma aprovar."""
    from . import aprendizado, fala
    duracao = int(p.get("duracao", 45))
    n = int(p.get("max_cortes", 8))
    ini, fim = trecho_da_analise(p, f, dur_total)
    servico.atualizar_fonte_extra(f.id, trecho={"inicio": ini, "fim": fim})
    if (ini, fim) != (0, dur_total):
        ctx.log(f"trecho escolhido: {ini / 3600:.2f}h até {fim / 3600:.2f}h")
    escolhidos = p.get("detectores") or list(DETECTORES.itens)
    usa_fala = "fala" in escolhidos and fim - ini <= config.fala_max_h * 3600
    chat = st.plataforma == "youtube" and "chat_youtube" in escolhidos and info.get("tem_chat")
    a_ = 0.30 if usa_fala else 0.55  # fim da etapa do áudio
    f_ = 0.60 if chat else 0.90       # fim da etapa da fala (ou do áudio, sem fala)
    etapas = {"audio": (0.05, a_ if usa_fala else f_), "fala": (a_, f_), "chat_youtube": (f_, 0.92)}
    extra = f.extra or {}
    tmp = render.pasta_tmp(f"fonte_{f.id}")
    analise = detectores.Analise(url=f.url, duracao=dur_total, plataforma=st.plataforma, canal=st.canal,
                                 pasta=tmp, info=info, progresso=ctx.progresso, log=ctx.log, inicio=ini, fim=fim,
                                 fonte_id=f.id, idioma=extra.get("idioma") or extra.get("idioma_site"),
                                 checar=ctx.checar, etapas=etapas, guardar_audio=usa_fala)
    curvas, pesos = {}, {}
    try:
        for d in escolhidos:
            ctx.checar()
            plug = DETECTORES[d]
            curva = plug.funcao(analise)
            if curva is not None and len(curva) and curva.max() > 0:
                curvas[d] = detectores.mascarar(detectores._ajustar(curva, dur_total), (ini, fim))
                pesos[d] = plug.opcoes.get("peso", 1.0)
                ctx.log(f"detector {d}: ok")
            else:
                ctx.log(f"detector {d}: sem dados para este vídeo")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not curvas:
        raise RuntimeError("nenhum detector conseguiu dados deste vídeo")
    tr = analise.fala
    if tr and tr.get("idioma") and tr.get("idioma_prob", 0) >= 0.7 and not extra.get("idioma"):
        servico.atualizar_fonte_extra(f.id, idioma=tr["idioma"], idioma_prob=tr["idioma_prob"])
    frases = [(s["i"], s["f"]) for s in tr["segmentos"]] if tr else None
    score = detectores.combinar(curvas, pesos)
    sinais = curvas | analise.extras
    modelo = aprendizado.modelo_ativo()
    cand = detectores.escolher_picos(score, sinais, n * 3 if modelo else n, duracao, faixa=(ini, fim), frases=frases)
    if modelo:
        ctx.log(f"reordenando pelo que você costuma aprovar ({modelo['exemplos']} exemplos)")
    cand = aprendizado.reordenar(cand, n, modelo)
    for c in cand:
        c["titulo"] = f.titulo
        if tr and "fala" in curvas:
            g = fala.sugerir_gancho(tr["segmentos"], c["inicio"], c["fim"], curvas["fala"], tr.get("idioma"))
            if g:
                c["gancho"] = g
    return cand


@tarefa("detectar_webcam", recurso=lambda p: "rede:busca")
def detectar_webcam(ctx, p):
    st = servico.obter_streamer(p["streamer_id"])
    fs = servico.listar_fontes(st.id)
    alvo = next((x for x in fs if x["id"] == p.get("fonte_id")), None) or (fs[0] if fs else None)
    if not alvo:
        raise ValueError("busque pelo menos um VOD ou clipe deste streamer antes")
    tmp = render.pasta_tmp(f"webcam_{st.id}")
    try:
        dur = alvo["duracao"] or 60
        ini = None if alvo["tipo"] == "clipe" else max(0.0, dur / 2)
        fim = None if alvo["tipo"] == "clipe" else min(dur, (ini or 0) + 25)
        ctx.progresso(0.1, "baixando uma amostra do vídeo")
        amostra = fontes.baixar_trecho(alvo["url"], ini, fim, tmp / "amostra.mp4", altura=720)
        ctx.progresso(0.7, "procurando o rosto fixo")
        cam = webcam.detectar(amostra, salvar_quadro=render.caminho_quadro(st.id))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if cam:
        servico.atualizar_streamer(st.id, {"webcam": cam})
    return {"webcam": cam, "mensagem": "webcam encontrada" if cam else "nenhuma webcam fixa encontrada"}


@tarefa("enquadrar_corte", recurso=lambda p: "rede:busca")
def enquadrar_corte(ctx, p):
    """Baixa o trecho, salva o quadro e procura a webcam, sem renderizar (para conferir o enquadramento)."""
    antes = servico.obter_corte(p["corte_id"])["status"]
    try:
        r = render.preparar_enquadramento(p["corte_id"], progresso=ctx.progresso, log=ctx.log)
    except Exception as e:
        servico.atualizar_corte(p["corte_id"], erro=str(e)[:1000])
        raise
    if antes == "pronto" and r.get("situacao") in ("ok", "nenhuma"):
        servico.rerenderizar(p["corte_id"], "Atualizar")
        ctx.log("região do streamer atualizada: gerando o vídeo de novo")
        r["rerenderizando"] = True
    return r


@tarefa("vigiar_clipes", recurso=lambda p: f"vigia:{p['streamer_id']}")
def vigiar_clipes(ctx, p):
    """Uma olhada nos clipes novos do streamer (cria cortes para revisar; não renderiza nem posta)."""
    from ..jobs.fila import enfileirar
    ctx.progresso(None, "olhando os clipes na Twitch")
    try:
        return vigia.ciclo(p["streamer_id"], log=ctx.log, enfileirar=enfileirar)
    except Exception:
        vigia.adiar(p["streamer_id"])
        raise


@tarefa("preparar_editor", recurso="gpu")
def preparar_editor(ctx, p):
    """Baixa o trecho com folga e transcreve o arquivo inteiro (o editor de vídeo precisa dos dois)."""
    return render.preparar_editor(p["corte_id"], progresso=ctx.progresso, log=ctx.log)


@tarefa("renderizar_corte", recurso="gpu")
def renderizar_corte(ctx, p):
    servico.atualizar_corte(p["corte_id"], status="renderizando")
    try:
        return render.renderizar(p["corte_id"], progresso=ctx.progresso, log=ctx.log, checar=ctx.checar)
    except Exception as e:
        servico.atualizar_corte(p["corte_id"], status="erro", erro=str(e)[:1000])
        raise


@tarefa("cortar_video", recurso=lambda p: "analise")
def cortar_video(ctx, p):
    """Fluxo rápido (colar um link): acha os N melhores trechos e já prepara cada um (baixa o trecho, procura o
    streamer, mede as barras pretas e descobre o idioma). Sem câmera no vídeo, o corte segue sem o streamer;
    só os que têm câmera com posição incerta ficam 'enquadrar' para o usuário recortar."""
    _analisar(_Faixa(ctx, 0.0, 0.45), {"fonte_id": p["fonte_id"], "max_cortes": p.get("quantidade", 3),
                                       "duracao": p.get("duracao", 45), "inicio": p.get("inicio"),
                                       "fim": p.get("fim")})
    cortes = [c for c in servico.listar_cortes(fonte_id=p["fonte_id"]) if c["status"] == "candidato"]
    cortes.sort(key=lambda c: c["inicio"])
    if p.get("modelo_id"):  # o modelo escolhido na tela vale para os cortes deste vídeo
        for c in cortes:
            servico.atualizar_corte(c["id"], modelo_id=p["modelo_id"])
    resumo = {"cortes": len(cortes), "identificados": 0, "sem_webcam": 0, "enquadrar": 0, "erros": 0}
    for i, c in enumerate(cortes):
        ctx.checar()
        faixa = _Faixa(ctx, 0.45 + 0.55 * i / len(cortes), 0.45 + 0.55 * (i + 1) / len(cortes))
        faixa.progresso(0.0, f"preparando o corte {i + 1} de {len(cortes)}")
        try:
            r = render.preparar_enquadramento(c["id"], progresso=faixa.progresso, log=ctx.log)
            resumo[{"ok": "identificados", "nenhuma": "sem_webcam", "duvida": "enquadrar"}[r["situacao"]]] += 1
        except Exception as e:  # um trecho com problema não derruba os outros
            ctx.log(f"corte #{c['id']}: {e}")
            servico.atualizar_corte(c["id"], status="erro", erro=str(e)[:1000])
            resumo["erros"] += 1
    resumo["enquadrar"] += _sugerir_pela_mesma_live(p["fonte_id"], ctx.log)
    resumo["sem_webcam"] = sum(1 for c in servico.listar_cortes(fonte_id=p["fonte_id"])
                               if (c["extra"] or {}).get("webcam") == "nenhuma")
    ctx.progresso(1.0, f"{resumo['cortes']} corte(s) prontos para revisar")
    return resumo


def _sugerir_pela_mesma_live(fonte_id: int, log) -> int:
    """Se outros cortes do MESMO vídeo acharam a webcam com segurança, sabemos que ela existe e onde fica:
    os cortes deste vídeo em dúvida ou "sem webcam" passam a pedir o recorte, já com essa posição sugerida
    (se a câmera estava desligada no trecho, o usuário clica em "Não tem streamer"). Devolve quantos passaram
    de "sem webcam" para "enquadrar"."""
    import statistics
    cortes = [c for c in servico.listar_cortes(fonte_id=fonte_id) if c["status"] not in ("descartado", "na_fila")]
    autos = [c["webcam"] for c in cortes if (c["webcam"] or {}).get("origem") == "auto"]
    if not autos:
        return 0
    pos = {k: round(statistics.median(w[k] for w in autos), 4) for k in "xywh"}
    novos = 0
    for c in cortes:
        extra = dict(c["extra"] or {})
        duvida = c["status"] == "enquadrar"
        if not duvida and extra.get("webcam") != "nenhuma":
            continue
        novos += 0 if duvida else 1
        extra.pop("webcam", None)
        servico.atualizar_corte(c["id"], webcam={**pos, "origem": "sugerida", "confianca": None}, extra=extra,
                                status="enquadrar")
    log(f"webcam vista com segurança em {len(autos)} corte(s) deste vídeo: os incertos pedem recorte com essa "
        "posição sugerida")
    return novos
