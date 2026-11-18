"""Modelos de corte, streamers, fontes (VODs/clipes), cortes e plugins."""
import hashlib
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response

from ...cortes import edicao as ed
from ...cortes import fontes, plugins, render, servico, vigia
from ...jobs import enfileirar
from ...plataformas import PLATAFORMAS
from .. import schemas as S

router = APIRouter(tags=["cortador"])


def _404(fn, *a):
    try:
        return fn(*a)
    except KeyError as e:
        raise HTTPException(404, str(e)) from None


# ------------------------------------------------------------------ plugins

@router.get("/plugins", response_model=S.PluginsOut)
def listar_plugins():
    plugins.carregar()
    return {"layouts": plugins.LAYOUTS.listar(), "estilos": plugins.ESTILOS.listar(),
            "detectores": plugins.DETECTORES.listar(), "plataformas": list(PLATAFORMAS)}


# ------------------------------------------------------------------ modelos de corte

def _validar_modelo(dados: dict):
    plugins.carregar()
    if "layout" in dados and dados["layout"] not in plugins.LAYOUTS:
        raise HTTPException(400, f"layout desconhecido: {dados['layout']}")
    if dados.get("estilo_legenda") and dados["estilo_legenda"] not in plugins.ESTILOS:
        raise HTTPException(400, f"estilo de legenda desconhecido: {dados['estilo_legenda']}")


@router.get("/modelos", response_model=list[S.ModeloOut])
def listar_modelos():
    return servico.listar_modelos()


@router.post("/modelos", response_model=S.ModeloOut, status_code=201)
def criar_modelo(dados: S.ModeloIn):
    d = dados.model_dump()
    _validar_modelo(d)
    return servico.criar_modelo(**d)


@router.patch("/modelos/{modelo_id}", response_model=S.ModeloOut)
def atualizar_modelo(modelo_id: int, dados: S.ModeloPatch):
    d = dados.model_dump(exclude_unset=True)
    if "params" in d:
        d["params"] = dados.params.model_dump(exclude_unset=True)
    _validar_modelo(d)
    try:
        return servico.atualizar_modelo(modelo_id, d)
    except KeyError:
        raise HTTPException(404) from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.delete("/modelos/{modelo_id}", status_code=204)
def remover_modelo(modelo_id: int):
    try:
        servico.remover_modelo(modelo_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.post("/previa", response_class=Response, responses={200: {"content": {"image/jpeg": {}}}})
async def previa(dados: S.PreviaIn):
    """Um quadro 1080x1920 do modelo, renderizado pelo mesmo ffmpeg do corte final (JPEG)."""
    try:
        modelo = servico.obter_modelo(dados.modelo_id) if dados.modelo_id or not dados.layout else {
            "nome": "rascunho", "layout": dados.layout, "estilo_legenda": dados.estilo_legenda or "destaque",
            "params": {}}
    except KeyError as e:
        raise HTTPException(404, str(e)) from None
    if dados.layout:
        modelo = {**modelo, "layout": dados.layout}
    if dados.estilo_legenda:
        modelo = {**modelo, "estilo_legenda": dados.estilo_legenda}
    if dados.params:
        modelo = {**modelo, "params": {**(modelo.get("params") or {}), **dados.params.model_dump(exclude_none=True)}}
    _validar_modelo(modelo)
    quadro, cam, jogo, credito, gancho, fundo = None, None, None, "twitch.tv/streamer", dados.gancho, dados.fundo
    exemplo = True
    if dados.corte_id:
        c = _404(servico.obter_corte, dados.corte_id)
        quadro = servico.caminho_quadro_corte(c["id"])
        cam, jogo = c["webcam"], c["jogo"]
        exemplo = not render.sem_webcam(c)
        credito = render.credito(servico.obter_streamer(c["streamer_id"]))
        gancho = gancho if gancho is not None else c["gancho"]
        fundo = fundo or c["fundo"]
    elif dados.streamer_id:
        st = _404(servico.obter_streamer, dados.streamer_id)
        quadro, cam, credito = render.caminho_quadro(st.id), st.webcam, render.credito(st)
    if quadro is None or not quadro.exists():
        quadro = next(iter(sorted((servico.pasta_renderizados().parent / "quadros").glob("*.jpg"),
                                  key=lambda p: -p.stat().st_mtime)), None)
    cam = dados.webcam.model_dump() if dados.webcam else cam
    jogo = dados.jogo.model_dump() if dados.jogo else jogo
    try:
        jpg = await run_in_threadpool(render.previa, modelo, quadro, cam, jogo, None, gancho, credito, fundo,
                                      exemplo or bool(dados.webcam),
                                      dados.edicao.model_dump() if dados.edicao else None)
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from None
    return Response(jpg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


# ------------------------------------------------------------------ streamers

@router.get("/streamers", response_model=list[S.StreamerOut])
def listar_streamers():
    return servico.listar_streamers()


@router.post("/streamers", response_model=S.StreamerOut, status_code=201)
def criar_streamer(dados: S.StreamerIn):
    st = servico.criar_streamer(**dados.model_dump())
    return servico.streamer_dict(st)


@router.get("/streamers/{streamer_id}", response_model=S.StreamerOut)
def obter_streamer(streamer_id: int):
    return servico.streamer_dict(_404(servico.obter_streamer, streamer_id))


@router.patch("/streamers/{streamer_id}", response_model=S.StreamerOut)
def atualizar_streamer(streamer_id: int, dados: S.StreamerPatch):
    campos = dados.model_dump(exclude_unset=True)
    st = _404(servico.atualizar_streamer, streamer_id, campos)
    return servico.streamer_dict(st)


@router.delete("/streamers/{streamer_id}", status_code=204)
def remover_streamer(streamer_id: int):
    servico.remover_streamer(streamer_id)


@router.post("/streamers/{streamer_id}/buscar", response_model=S.JobOut, status_code=202)
def buscar_fontes(streamer_id: int, dados: S.BuscarFontesIn):
    """Procura VODs ou clipes recentes do canal (job)."""
    st = _404(servico.obter_streamer, streamer_id)
    nome = "VODs" if dados.tipo == "vod" else "clipes"
    return enfileirar("buscar_fontes", {"streamer_id": st.id, **dados.model_dump()}, f"Buscar {nome} · {st.nome}")


@router.post("/streamers/{streamer_id}/webcam/detectar", response_model=S.JobOut, status_code=202)
def detectar_webcam(streamer_id: int, fonte_id: int | None = None):
    """Detecta a posição da webcam num trecho de um VOD do streamer (job)."""
    st = _404(servico.obter_streamer, streamer_id)
    return enfileirar("detectar_webcam", {"streamer_id": st.id, "fonte_id": fonte_id}, f"Detectar webcam · {st.nome}")


@router.get("/streamers/{streamer_id}/vigia", response_model=S.VigiaOut)
def ler_vigia(streamer_id: int):
    """Vigia de clipes da Twitch deste streamer: configuração, últimos clipes vistos e os que estão esperando."""
    return vigia.resumo(_404(servico.obter_streamer, streamer_id))


@router.put("/streamers/{streamer_id}/vigia", response_model=S.VigiaOut)
def configurar_vigia(streamer_id: int, dados: S.VigiaConfig):
    _404(servico.obter_streamer, streamer_id)
    if dados.dur_min > dados.dur_max:
        raise HTTPException(400, "a duração mínima precisa ser menor que a máxima")
    try:
        return vigia.configurar(streamer_id, dados.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.post("/streamers/{streamer_id}/vigia/agora", response_model=S.JobOut, status_code=202)
def vigiar_agora(streamer_id: int):
    """Olha os clipes agora (sem esperar o intervalo)."""
    st = _404(servico.obter_streamer, streamer_id)
    if st.plataforma != "twitch":
        raise HTTPException(400, "o vigia de clipes só funciona com canais da Twitch")
    return enfileirar("vigiar_clipes", {"streamer_id": st.id}, f"Vigia de clipes · {st.nome}")


@router.get("/vigia", response_model=list[S.VigiaStreamerOut])
def painel_vigia():
    """Todos os streamers da Twitch com o resumo do vigia (Painel)."""
    out = []
    for d in servico.listar_streamers():
        if d["plataforma"] != "twitch":
            continue
        st = servico.obter_streamer(d["id"])
        out.append({"streamer_id": st.id, "nome": st.nome, "canal": st.canal, **vigia.resumo(st)})
    return out


@router.get("/streamers/{streamer_id}/quadro", response_class=FileResponse)
def quadro(streamer_id: int):
    """Último quadro de referência usado na detecção da webcam (para ajustar o retângulo na tela)."""
    p = servico.pasta_renderizados().parent / "quadros" / f"streamer_{streamer_id}.jpg"
    if not p.exists():
        raise HTTPException(404, "sem quadro: rode a detecção de webcam primeiro")
    return FileResponse(p, media_type="image/jpeg")


# ------------------------------------------------------------------ fontes

@router.get("/fontes", response_model=list[S.FonteOut])
def listar_fontes(streamer_id: int | None = None, com_cortes: list[str] | None = Query(None)):
    """`com_cortes=candidato&com_cortes=enquadrar...` = só os vídeos com algum corte nesses status."""
    return servico.listar_fontes(streamer_id, com_cortes=com_cortes)


@router.post("/fontes", response_model=S.FonteOut, status_code=201)
def adicionar_fonte(dados: S.FonteIn):
    """Adiciona um VOD/clipe pela URL (Twitch ou YouTube)."""
    _404(servico.obter_streamer, dados.streamer_id)
    tipo = "clipe" if "/clip/" in dados.url or "clips.twitch.tv" in dados.url else "vod"
    fid = servico.salvar_fontes(dados.streamer_id, [{"url": dados.url.strip(), "tipo": tipo, "titulo": dados.url}])[0]
    enfileirar("info_fonte", {"fonte_id": fid}, f"Ler dados da fonte #{fid}")
    return next(f for f in servico.listar_fontes(dados.streamer_id) if f["id"] == fid)


@router.post("/fontes/{fonte_id}/analisar", response_model=S.JobOut, status_code=202)
def analisar(fonte_id: int, dados: S.AnalisarIn):
    """Encontra os melhores trechos (picos de áudio, mais assistidos, clipes) e cria cortes candidatos (job)."""
    f = _404(servico.obter_fonte, fonte_id)
    return enfileirar("analisar_fonte", {"fonte_id": f.id, **dados.model_dump()}, f"Analisar · {f.titulo[:60]}")


# ------------------------------------------------------------------ cortes

@router.get("/cortes", response_model=list[S.CorteOut])
def listar_cortes(status: list[str] | None = Query(None), streamer_id: int | None = None,
                  fonte_id: int | None = None):
    return servico.listar_cortes(status, streamer_id, fonte_id)


@router.get("/cortes/{corte_id}", response_model=S.CorteOut)
def obter_corte(corte_id: int):
    return _404(servico.obter_corte, corte_id)


@router.patch("/cortes/{corte_id}", response_model=S.CorteOut)
def editar_corte(corte_id: int, dados: S.CortePatch):
    campos = dados.model_dump(exclude_unset=True)
    atual = _404(servico.obter_corte, corte_id)
    if campos.get("edicao"):
        for s in campos["edicao"]["segmentos"]:
            if s["f"] - s["i"] < 0.2:
                raise HTTPException(400, "cada trecho precisa ter pelo menos 0,2 s")
    extra = dict(atual["extra"] or {})
    sem = campos.pop("sem_webcam", None)
    if sem:  # "não tem streamer neste corte"
        campos["webcam"], extra["webcam"] = None, "nenhuma"
    elif "webcam" in campos:  # marcada à mão (ou apagada para detectar de novo)
        extra.pop("webcam", None)
        if campos["webcam"]:
            campos["webcam"] = {**campos["webcam"], "origem": "manual", "confianca": None}
    if sem or "webcam" in campos:
        campos["extra"] = extra
    if (sem or campos.get("webcam")) and atual["status"] == "enquadrar" and "status" not in campos:
        campos["status"] = "candidato"
    if campos.get("status") == "descartado":  # libera o trecho baixado para o enquadramento
        shutil.rmtree(render.pasta_tmp(f"corte_{corte_id}"), ignore_errors=True)
    try:
        novo = servico.atualizar_corte(corte_id, **campos)
    except KeyError:
        raise HTTPException(404) from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    # mudou a região do streamer de um corte já gerado: atualiza o vídeo sozinho
    if (sem or campos.get("webcam")) and atual["status"] == "pronto":
        servico.rerenderizar(corte_id, "Atualizar")
        novo = servico.obter_corte(corte_id)
    return novo


@router.post("/cortes/{corte_id}/enquadrar", response_model=S.JobOut, status_code=202)
def enquadrar(corte_id: int):
    """Baixa o trecho, salva um quadro e procura a webcam do streamer, sem renderizar (job)."""
    c = _404(servico.obter_corte, corte_id)
    return enfileirar("enquadrar_corte", {"corte_id": corte_id}, f"Enquadrar corte #{corte_id} · {c['streamer_nome']}")


@router.get("/cortes/{corte_id}/quadro", response_class=FileResponse)
def quadro_corte(corte_id: int):
    """Quadro do trecho do corte (fundo do editor de enquadramento)."""
    p = servico.caminho_quadro_corte(corte_id)
    if not p.exists():
        raise HTTPException(404, "sem quadro: clique em Enquadrar (ou renderize) primeiro")
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/cortes/{corte_id}/renderizar", response_model=S.JobOut, status_code=202)
def renderizar(corte_id: int):
    """Baixa o trecho, transcreve, monta o vertical com legenda e salva o mp4 (job, usa a GPU)."""
    _404(servico.obter_corte, corte_id)
    return servico.rerenderizar(corte_id)


@router.get("/cortes/{corte_id}/arquivo", response_class=FileResponse)
def arquivo_corte(corte_id: int):
    c = _404(servico.obter_corte, corte_id)
    if not c["arquivo"] or not Path(c["arquivo"]).exists():
        raise HTTPException(404, "corte ainda não renderizado")
    return FileResponse(c["arquivo"], media_type="video/mp4")


@router.get("/cortes/{corte_id}/miniatura", response_class=FileResponse)
def miniatura_corte(corte_id: int):
    """JPEG de um quadro do vídeo pronto (para a grade da Biblioteca). Gerado uma vez e refeito se o mp4 mudar."""
    c = _404(servico.obter_corte, corte_id)
    if not c["arquivo"] or not Path(c["arquivo"]).exists():
        raise HTTPException(404, "corte ainda não renderizado")
    mp4, jpg = Path(c["arquivo"]), servico.caminho_miniatura_corte(corte_id)
    if not jpg.exists() or jpg.stat().st_mtime < mp4.stat().st_mtime:
        try:
            render.salvar_miniatura(mp4, jpg)
        except Exception as e:
            raise HTTPException(500, f"não consegui gerar a miniatura: {e}") from None
    return FileResponse(jpg, media_type="image/jpeg")


# ------------------------------------------------------------------ editor de vídeo

@router.get("/cortes/{corte_id}/editor", response_model=S.EditorOut)
def editor(corte_id: int):
    """Tudo que o editor precisa: tamanho e posição do trecho baixado, legenda (em segundos do arquivo), a edição
    salva e a edição "padrão" (como o modelo de corte deixaria). `pronto=false`: rode POST .../editor/preparar."""
    c = _404(servico.obter_corte, corte_id)
    st = servico.obter_streamer(c["streamer_id"])
    modelo = render.modelo_do_corte(c)
    base = {"fontes": ed.fontes_texto(), "credito": render.credito(st),
            "barra": (modelo.get("params") or {}).get("barra", True),
            "fundo_imagem": c["fundo"] or (modelo.get("params") or {}).get("fundo")}
    tem_audio = True
    if render.trecho_pronto(c):
        tem_audio = render.midia.ffprobe(render.caminho_trecho(corte_id))["tem_audio"]
    if not render.trecho_pronto(c) or (tem_audio and not render.transcricao_vale(c)):
        return {"pronto": False, **base}
    info = render.midia.ffprobe(render.caminho_trecho(corte_id))
    cam = c["webcam"] if c["webcam"] and not render.sem_webcam(c) else None
    fundo = render.caminho_fundo(base["fundo_imagem"])
    montagem = render.montar(info["largura"], info["altura"], modelo, cam, c["jogo"], c["fundo"])
    padrao = ed.edicao_padrao(c, modelo, montagem, info["largura"], info["altura"], cam, bool(fundo))
    arq = (c.get("transcricao") or {}).get("arquivo") or {}
    return {"pronto": True, "largura": info["largura"], "altura": info["altura"], "duracao": info["duracao"],
            "base": render.base_do_trecho(c), "palavras": arq.get("palavras", []), "edicao": c.get("edicao"),
            "padrao": padrao, **base}


@router.post("/cortes/{corte_id}/editor/preparar", response_model=S.JobOut, status_code=202)
def preparar_editor(corte_id: int):
    """Baixa o trecho (com folga) e transcreve, para abrir no editor (job)."""
    c = _404(servico.obter_corte, corte_id)
    return enfileirar("preparar_editor", {"corte_id": corte_id}, f"Preparar editor · corte #{corte_id} · "
                                                                 f"{c['streamer_nome']}")


@router.get("/cortes/{corte_id}/bruto", response_class=FileResponse)
def bruto(corte_id: int):
    """O trecho baixado (com a folga), para o editor tocar. Aceita Range (dá para pular no vídeo)."""
    p = render.caminho_trecho(corte_id)
    if not p.exists():
        raise HTTPException(404, "trecho ainda não baixado: prepare o editor")
    return FileResponse(p, media_type="video/mp4")


@router.get("/fontes-texto", response_model=list[S.FonteTexto])
def listar_fontes_texto():
    return ed.fontes_texto()


@router.get("/fontes-texto/{arquivo}", response_class=FileResponse)
def arquivo_fonte_texto(arquivo: str):
    """Arquivo de uma fonte enviada por você (o editor carrega com @font-face)."""
    p = ed.pasta_fontes() / Path(arquivo).name
    if not p.exists() or p.suffix.lower() not in ed.EXTENSOES_FONTE:
        raise HTTPException(404)
    return FileResponse(p, media_type="font/otf" if p.suffix.lower() == ".otf" else "font/ttf")


@router.post("/fontes-texto", response_model=S.FonteTexto, status_code=201,
             openapi_extra={"requestBody": {"content": {"application/octet-stream": {}}}})
async def enviar_fonte_texto(request: Request, nome: str = Query(..., description="nome do arquivo .ttf/.otf")):
    """Envia uma fonte (.ttf ou .otf) para usar na legenda e no gancho."""
    ext = Path(nome).suffix.lower()
    if ext not in ed.EXTENSOES_FONTE:
        raise HTTPException(415, "envie um arquivo .ttf ou .otf")
    dados = await request.body()
    if not dados or len(dados) > 15_000_000:
        raise HTTPException(400, "arquivo vazio ou grande demais (máx. 15 MB)")
    destino = ed.pasta_fontes() / (servico.slug(Path(nome).stem) + ext)
    destino.write_bytes(dados)
    return next(f for f in ed.fontes_usuario() if f["arquivo"] == destino.name)


@router.post("/cortes/{corte_id}/publicar", response_model=S.CorteOut)
def publicar(corte_id: int, dados: S.PublicarCorteIn):
    """Manda o corte renderizado para a fila de postagem da conta."""
    try:
        servico.publicar_na_fila(corte_id, dados.conta_id)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e)) from None
    return servico.obter_corte(corte_id)


# ------------------------------------------------------------------ fluxo rápido: colar um link

@router.post("/identificar", response_model=S.IdentificarOut)
async def identificar(dados: S.IdentificarIn):
    """Lê o link (sem baixar): plataforma, canal, título, duração e, se o site informar, o idioma."""
    try:
        i = await run_in_threadpool(fontes.identificar, dados.url)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    fonte = servico.fonte_por_url(i["url"])
    sts = servico.listar_streamers()
    if fonte:  # vídeo já cadastrado: vale o streamer dono dele (o canal do link pode ser um repost)
        st = next((x for x in sts if x["id"] == fonte.streamer_id), None)
    else:
        st = next((x for x in sts if x["plataforma"] == i["plataforma"]
                   and x["canal"].lower() == i["canal"].lower()), None)
    return {**i, "streamer_id": st["id"] if st else None, "streamer_nome": st["nome"] if st else None,
            "streamer_modelo_id": st["modelo_id"] if st else None, "fonte_id": fonte.id if fonte else None}


@router.post("/cortar", response_model=S.CortarVideoOut, status_code=202)
async def cortar_video(dados: S.CortarVideoIn):
    """Cola um link -> cadastra o streamer (se novo) e o vídeo -> job que acha os N melhores trechos e já prepara
    cada um (streamer, barras pretas, idioma)."""
    try:
        i = await run_in_threadpool(fontes.identificar, dados.url)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    existente = servico.fonte_por_url(i["url"])
    if existente:  # vídeo já cadastrado: continua no streamer dono dele
        st, criado = servico.obter_streamer(existente.streamer_id), False
    elif not i["canal"]:
        raise HTTPException(400, "não consegui descobrir o canal deste vídeo")
    else:
        st, criado = servico.streamer_por_canal(i["plataforma"], i["canal"], i["canal_nome"], i["idioma"])
    if dados.modelo_id and criado:
        servico.atualizar_streamer(st.id, {"modelo_id": dados.modelo_id})
    fid = servico.salvar_fontes(st.id, [{k: i[k] for k in ("url", "tipo", "titulo", "duracao", "views",
                                                         "publicado_em", "miniatura")}])[0]
    if i["idioma"]:
        servico.atualizar_fonte_extra(fid, idioma_site=i["idioma"])
    job = enfileirar("cortar_video", {"fonte_id": fid, "streamer_id": st.id, "quantidade": dados.quantidade,
                                      "duracao": dados.duracao, "modelo_id": dados.modelo_id},
                     f"Cortar · {i['titulo'][:60]}")
    return {"job": job, "fonte_id": fid, "streamer_id": st.id, "streamer_criado": criado}


@router.get("/fontes/{fonte_id}", response_model=S.FonteOut)
def obter_fonte(fonte_id: int):
    return _404(servico.obter_fonte_dict, fonte_id)


@router.post("/fontes/{fonte_id}/aplicar", response_model=list[S.CorteOut])
def aplicar_em_todos(fonte_id: int, dados: S.AplicarCortesIn):
    """Mesmo modelo / idioma da legenda / imagem de fundo para todos os cortes do vídeo."""
    _404(servico.obter_fonte, fonte_id)
    campos = dados.model_dump(exclude_unset=True)
    if campos.get("fundo") and not render.caminho_fundo(campos["fundo"]):
        raise HTTPException(400, "imagem de fundo não encontrada")
    for cid in servico.cortes_da_fonte(fonte_id):
        servico.atualizar_corte(cid, **campos)
    return servico.listar_cortes(fonte_id=fonte_id)


@router.post("/fontes/{fonte_id}/renderizar", response_model=list[S.JobOut], status_code=202)
def renderizar_todos(fonte_id: int):
    """Renderiza todos os cortes do vídeo que estão prontos para isso (pula os que esperam marcar a webcam)."""
    jobs = []
    for c in servico.listar_cortes(fonte_id=fonte_id):
        if c["status"] in ("candidato", "pronto", "erro"):
            servico.atualizar_corte(c["id"], status="aprovado", erro=None)
            jobs.append(enfileirar("renderizar_corte", {"corte_id": c["id"]},
                                   f"Renderizar corte #{c['id']} · {c['streamer_nome']}"))
    return jobs


# ------------------------------------------------------------------ imagens de fundo

TIPOS_IMAGEM = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@router.get("/fundos", response_model=list[S.FundoOut])
def listar_fundos():
    return [{"nome": p.name, "kb": p.stat().st_size // 1024}
            for p in sorted(servico.pasta_fundos().iterdir(), key=lambda p: -p.stat().st_mtime) if p.is_file()]


@router.post("/fundos", response_model=S.FundoOut, status_code=201,
             openapi_extra={"requestBody": {"content": {t: {"schema": {"type": "string", "format": "binary"}}
                                                        for t in TIPOS_IMAGEM}, "required": True}})
async def enviar_fundo(request: Request):
    """Envia uma imagem de fundo (corpo = os bytes da imagem; Content-Type image/jpeg, png ou webp)."""
    ext = TIPOS_IMAGEM.get(request.headers.get("content-type", "").split(";")[0])
    if not ext:
        raise HTTPException(415, "envie uma imagem JPG, PNG ou WEBP")
    dados = await request.body()
    if not 0 < len(dados) <= 20 * 1024 * 1024:
        raise HTTPException(413, "a imagem precisa ter até 20 MB")
    nome = f"fundo_{hashlib.sha1(dados).hexdigest()[:12]}{ext}"
    (servico.pasta_fundos() / nome).write_bytes(dados)
    return {"nome": nome, "kb": len(dados) // 1024}


@router.get("/fundos/{nome}", response_class=FileResponse)
def arquivo_fundo(nome: str):
    p = render.caminho_fundo(nome)
    if not p:
        raise HTTPException(404)
    return FileResponse(p)


@router.delete("/fundos/{nome}", status_code=204)
def remover_fundo(nome: str):
    p = render.caminho_fundo(nome)
    if p:
        p.unlink()
