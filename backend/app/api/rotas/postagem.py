"""Contas, vídeos, posts, agenda, pack."""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select

from ...db import sessao
from ...jobs import enfileirar
from ...models import Post
from ...plataformas import PLATAFORMAS, agendador
from ...plataformas.comum import REDES_TEXTO, escrever_meta, escrever_txt, ler_meta, textos_rede
from ...servicos import agenda, contas, historico, postagem
from .. import schemas as S

router = APIRouter(tags=["postagem"])


def _conta(conta_id: str):
    try:
        return contas.obter(conta_id)
    except KeyError:
        raise HTTPException(404, f"conta {conta_id} não existe") from None


def _arquivo_video(conta, nome: str) -> Path:
    pasta = contas.pasta_videos(conta).resolve()
    p = (pasta / Path(nome).name).resolve()
    if p.parent != pasta or p.suffix.lower() != ".mp4" or not p.exists():
        raise HTTPException(404, "vídeo não encontrado")
    return p


# ------------------------------------------------------------------ contas

@router.get("/contas", response_model=list[S.ContaOut])
def listar_contas():
    return contas.listar()


@router.post("/contas", response_model=S.ContaOut, status_code=201)
def criar_conta(dados: S.ContaIn):
    try:
        return contas.criar(**dados.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.patch("/contas/{conta_id}", response_model=S.ContaOut)
def atualizar_conta(conta_id: str, dados: S.ContaPatch):
    _conta(conta_id)
    return contas.atualizar(conta_id, **dados.model_dump(exclude_unset=True))


@router.post("/contas/{conta_id}/login")
def login(conta_id: str, plataformas: list[str] | None = None):
    """Abre o Chrome da conta (normal, sem automação) para logar. Feche o Chrome inteiro depois."""
    c = _conta(conta_id)
    postagem.abrir_login(c, plataformas or c.plataformas)
    return {"ok": True}


# ------------------------------------------------------------------ vídeos / fila

@router.get("/contas/{conta_id}/videos", response_model=list[S.VideoOut])
def fila(conta_id: str):
    c = _conta(conta_id)
    out = []
    for i in postagem.fila(c):
        out.append({"video": i["video"], "mb": i["mb"], "titulo": i["titulo"], "tags": i["tags"],
                    "descricao": i["descricao"], "redes": i["redes"],
                    "plataformas": {p: {"status": i[p], "para": i[f"{p}_para"], "link": i[f"{p}_link"]}
                                    for p in PLATAFORMAS}})
    return out


@router.get("/contas/{conta_id}/videos/{nome}/arquivo", response_class=FileResponse)
def arquivo(conta_id: str, nome: str):
    return FileResponse(_arquivo_video(_conta(conta_id), nome), media_type="video/mp4")


@router.put("/contas/{conta_id}/videos/{nome}/legenda")
def salvar_legenda(conta_id: str, nome: str, dados: S.LegendaIn):
    escrever_txt(_arquivo_video(_conta(conta_id), nome), dados.titulo, dados.tags)
    return {"ok": True}


def _textos_out(video) -> dict:
    return {**ler_meta(video), "finais": {r: textos_rede(video, r) for r in REDES_TEXTO}}


@router.get("/contas/{conta_id}/videos/{nome}/textos", response_model=S.TextosOut)
def ler_textos(conta_id: str, nome: str):
    """Título, descrição, hashtags, personalização por rede e o texto final que cada rede vai receber."""
    return _textos_out(_arquivo_video(_conta(conta_id), nome))


@router.put("/contas/{conta_id}/videos/{nome}/textos", response_model=S.TextosOut)
def salvar_textos(conta_id: str, nome: str, dados: S.TextosIn):
    video = _arquivo_video(_conta(conta_id), nome)
    escrever_meta(video, dados.model_dump())
    return _textos_out(video)


@router.post("/contas/{conta_id}/videos/hashtags")
def hashtags_em_lote(conta_id: str, dados: S.HashtagsLoteIn):
    """Troca (ou acrescenta) as hashtags de vários vídeos de uma vez."""
    c = _conta(conta_id)
    if dados.videos is not None:
        alvos = [_arquivo_video(c, n) for n in dados.videos]
    else:  # os que ainda não saíram em nenhuma rede
        hist = historico.carregar_hist(c.id)
        alvos = [v for v in contas.videos(c) if not any(agenda.feito(i) for i in hist.get(v.name, {}).values())]
    novas = dados.tags.split()
    for v in alvos:
        m = ler_meta(v)
        atuais = m["tags"].split()
        tags = novas if dados.modo == "substituir" else atuais + [t for t in novas if t.lower() not in
                                                                   {a.lower() for a in atuais}]
        escrever_meta(v, {**m, "tags": " ".join(tags)})
    return {"ok": True, "videos": len(alvos)}


@router.put("/contas/{conta_id}/videos/{nome}/redes/{plataforma}")
def estado_rede(conta_id: str, nome: str, plataforma: str, dados: S.EstadoRedeIn):
    """'Não postar nesta rede' (removido) ou voltar a pendente."""
    c = _conta(conta_id)
    video = _arquivo_video(c, nome)
    if plataforma not in PLATAFORMAS:
        raise HTTPException(404, f"plataforma desconhecida: {plataforma}")
    if dados.status == "removido":
        historico.registrar(c.id, video, plataforma, {"status": "removido"})
    else:
        with sessao() as s:
            for p in s.scalars(select(Post).where(Post.conta_id == c.id, Post.video == video.name,
                                                  Post.plataforma == plataforma)):
                s.delete(p)
    return {"ok": True}


@router.get("/contas/{conta_id}/plano", response_model=list[S.PlanoItem])
def plano(conta_id: str, plataformas: list[str] | None = Query(None), por_hora: int | None = None,
          ate: str | None = None):
    c = _conta(conta_id)
    p = agenda.plano(c, plataformas or c.plataformas, por_hora=por_hora, ate=ate)
    return [{"plataforma": x["plataforma"], "video": x["video"].name, "quando": x["quando"],
             "como": "nativo" if PLATAFORMAS[x["plataforma"]].AGENDA_NATIVA else "windows"} for x in p]


@router.post("/contas/{conta_id}/agendar", response_model=S.JobOut, status_code=202)
def agendar(conta_id: str, dados: S.AgendarIn):
    c = _conta(conta_id)
    lote = f" ({dados.por_hora}/h até {dados.ate or '00:00'})" if dados.por_hora else ""
    return enfileirar("agendar", {"conta": c.id, **dados.model_dump()}, f"Agendar pendentes · {c.nome}{lote}")


@router.post("/contas/{conta_id}/enviar", response_model=S.JobOut, status_code=202)
def enviar(conta_id: str, dados: S.EnviarIn):
    c = _conta(conta_id)
    alvo = dados.video or "próximo da fila"
    modo = " (revisar)" if dados.revisar else ""
    return enfileirar("enviar", {"conta": c.id, **dados.model_dump()}, f"Postar agora · {alvo}{modo}")


# ------------------------------------------------------------------ posts

@router.get("/posts", response_model=list[S.PostOut])
def listar_posts(conta_id: str | None = None, status: str | None = None, de: str | None = None,
                 ate: str | None = None, limite: int = 500):
    """Posts registrados. `de`/`ate` (ISO) filtram pelo horário agendado (`para`) ou registro (`em`)."""
    with sessao() as s:
        q = select(Post).order_by(Post.em.desc()).limit(limite)
        if conta_id:
            q = q.where(Post.conta_id == conta_id)
        if status:
            q = q.where(Post.status.in_(status.split(",")))
        if de:
            q = q.where((Post.para >= de) | (Post.para.is_(None) & (Post.em >= de)))
        if ate:
            q = q.where((Post.para < ate) | (Post.para.is_(None) & (Post.em < ate)))
        return list(s.scalars(q))


@router.patch("/posts/{post_id}", response_model=S.PostOut)
def corrigir_post(post_id: int, dados: S.PostPatch):
    """Correção manual (ex.: marcar como publicado depois de conferir no app)."""
    with sessao() as s:
        p = s.get(Post, post_id)
        if p is None:
            raise HTTPException(404)
        for k, v in dados.model_dump(exclude_unset=True).items():
            setattr(p, k, v)
        p.em = datetime.now().isoformat(timespec="seconds")
        return p


@router.delete("/posts/{post_id}", status_code=204)
def apagar_post(post_id: int):
    """Volta o vídeo a 'pendente' naquela plataforma."""
    with sessao() as s:
        p = s.get(Post, post_id)
        if p:
            s.delete(p)


# ------------------------------------------------------------------ grade, pack, Windows

@router.get("/horarios", response_model=dict[str, S.Grade])
def horarios():
    return {k: v for k, v in agenda.grade().items() if not k.startswith("_")}


@router.put("/horarios", response_model=dict[str, S.Grade])
def salvar_horarios(grade: dict[str, S.Grade]):
    atual = agenda.grade()
    for k, v in grade.items():
        if k in PLATAFORMAS:
            atual[k] = v.model_dump()
    agenda.salvar_grade(atual)
    return horarios()


@router.post("/pack/baixar", response_model=S.JobOut, status_code=202)
def baixar_pack(dados: S.PackIn):
    return enfileirar("baixar_pack", dados.model_dump(), f"Baixar {dados.qtd or len(dados.ids or [])} vídeo(s) do pack")


@router.get("/tarefas-windows", response_model=list[S.TarefaWindowsOut])
def tarefas():
    return agendador.listar()


@router.get("/historico/{conta_id}")
def exportar(conta_id: str):
    """Histórico no formato antigo do postados.json."""
    return historico.carregar_hist(_conta(conta_id).id)
