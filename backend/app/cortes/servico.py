"""Operações de banco do cortador (modelos, streamers, fontes, cortes). Sem lógica de vídeo aqui."""
import re
import shutil
import unicodedata
from pathlib import Path

from sqlalchemy import func, select

from ..config import config
from ..db import sessao
from ..models import Corte, Fonte, Modelo, Streamer
from ..plataformas.comum import escrever_txt
from ..servicos import contas


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_") or "streamer"


def normalizar_canal(plataforma: str, canal: str) -> str:
    """Aceita URL ou nome: 'https://twitch.tv/alanzoka' -> 'alanzoka'; 'youtube.com/@IShowSpeed' -> '@IShowSpeed'."""
    c = canal.strip().rstrip("/")
    if plataforma == "twitch":
        return c.split("/")[-1].lstrip("@").lower()
    m = re.search(r"(@[\w.-]+|channel/[\w-]+)", c)
    if m:
        return m.group(1)
    return c if c.startswith("@") else "@" + c


# ------------------------------------------------------------------ modelos de corte

def _modelo_dict(m: Modelo) -> dict:
    return {c.name: getattr(m, c.name) for c in Modelo.__table__.columns}


def listar_modelos() -> list[dict]:
    with sessao() as s:
        return [_modelo_dict(m) for m in s.scalars(select(Modelo).order_by(Modelo.padrao.desc(), Modelo.id))]


def obter_modelo(id: int | None = None) -> dict:
    """O modelo pedido; sem id (ou id apagado), o modelo padrão."""
    with sessao() as s:
        m = s.get(Modelo, id) if id else None
        m = m or s.scalar(select(Modelo).order_by(Modelo.padrao.desc(), Modelo.id))
        if m is None:
            raise KeyError("nenhum modelo de corte cadastrado")
        return _modelo_dict(m)


def _so_um_padrao(s, m: Modelo):
    if m.padrao:
        for outro in s.scalars(select(Modelo).where(Modelo.padrao.is_(True), Modelo.id != m.id)):
            outro.padrao = False


def criar_modelo(**dados) -> dict:
    with sessao() as s:
        m = Modelo(**dados)
        s.add(m)
        s.flush()
        _so_um_padrao(s, m)
        return _modelo_dict(m)


def atualizar_modelo(id: int, dados: dict) -> dict:
    with sessao() as s:
        m = s.get(Modelo, id)
        if m is None:
            raise KeyError(id)
        if dados.get("padrao") is False and m.padrao:
            raise ValueError("escolha outro modelo como padrão em vez de desmarcar este")
        for k, v in dados.items():
            setattr(m, k, {**(m.params or {}), **v} if k == "params" else v)
        _so_um_padrao(s, m)
        return _modelo_dict(m)


def remover_modelo(id: int):
    with sessao() as s:
        m = s.get(Modelo, id)
        if m is None:
            return
        if m.padrao:
            raise ValueError("não dá para apagar o modelo padrão (marque outro como padrão antes)")
        for tabela in (Streamer, Corte):
            for x in s.scalars(select(tabela).where(tabela.modelo_id == id)):
                x.modelo_id = None
        s.delete(m)


# ------------------------------------------------------------------ streamers

def _contagens(s, streamer_ids):
    fontes = dict(s.execute(select(Fonte.streamer_id, func.count()).where(Fonte.streamer_id.in_(streamer_ids))
                            .group_by(Fonte.streamer_id)).all())
    cortes = dict(s.execute(select(Fonte.streamer_id, func.count(Corte.id)).join(Corte)
                            .where(Fonte.streamer_id.in_(streamer_ids)).group_by(Fonte.streamer_id)).all())
    return fontes, cortes


def streamer_dict(st: Streamer, fontes=0, cortes=0) -> dict:
    d = {c.name: getattr(st, c.name) for c in Streamer.__table__.columns}
    return {**d, "total_fontes": fontes, "total_cortes": cortes}


def listar_streamers() -> list[dict]:
    with sessao() as s:
        sts = list(s.scalars(select(Streamer).order_by(Streamer.ativo.desc(), Streamer.nome)))
        f, c = _contagens(s, [x.id for x in sts])
        return [streamer_dict(x, f.get(x.id, 0), c.get(x.id, 0)) for x in sts]


def obter_streamer(id: int) -> Streamer:
    with sessao() as s:
        st = s.get(Streamer, id)
        if st is None:
            raise KeyError(f"streamer {id} não existe")
        return st


def criar_streamer(**dados) -> Streamer:
    dados["canal"] = normalizar_canal(dados["plataforma"], dados["canal"])
    with sessao() as s:
        st = Streamer(**dados)
        s.add(st)
        s.flush()
        return st


def streamer_por_canal(plataforma: str, canal: str, nome: str, idioma: str | None = None) -> tuple[Streamer, bool]:
    """Acha o streamer do canal ou cadastra um novo. Devolve (streamer, criado)."""
    if plataforma in ("twitch", "youtube"):
        canal = normalizar_canal(plataforma, canal)
    with sessao() as s:
        st = s.scalar(select(Streamer).where(Streamer.plataforma == plataforma, func.lower(Streamer.canal) ==
                                             canal.lower()))
        if st:
            return st, False
        st = Streamer(nome=nome or canal, plataforma=plataforma, canal=canal,
                      idioma=idioma if idioma in ("pt", "en", "es") else "pt")
        s.add(st)
        s.flush()
        return st, True


def atualizar_streamer(id: int, dados: dict) -> Streamer:
    with sessao() as s:
        st = s.get(Streamer, id)
        if st is None:
            raise KeyError(id)
        for k, v in dados.items():
            if k == "canal" and v and st.plataforma in ("twitch", "youtube"):
                v = normalizar_canal(st.plataforma, v)
            setattr(st, k, v)
        return st


def remover_streamer(id: int):
    with sessao() as s:
        st = s.get(Streamer, id)
        if st:
            s.delete(st)


# ------------------------------------------------------------------ fontes

def listar_fontes(streamer_id: int | None = None, limite: int = 200, com_cortes: list[str] | None = None) -> list[dict]:
    """Fontes (mais novas primeiro) com a contagem de cortes por status. `com_cortes` = só as que têm algum
    corte num desses status (a Biblioteca usa para "Para revisar")."""
    with sessao() as s:
        q = select(Fonte, Streamer).join(Streamer).order_by(Fonte.id.desc()).limit(limite)
        if streamer_id:
            q = q.where(Fonte.streamer_id == streamer_id)
        if com_cortes:
            q = q.where(Fonte.id.in_(select(Corte.fonte_id).where(Corte.status.in_(com_cortes))))
        linhas = s.execute(q).all()
        por_status: dict[int, dict[str, int]] = {}
        ids = [f.id for f, _ in linhas]
        for fid, st, n in s.execute(select(Corte.fonte_id, Corte.status, func.count()).where(Corte.fonte_id.in_(ids))
                                    .group_by(Corte.fonte_id, Corte.status)):
            por_status.setdefault(fid, {})[st] = n
        return [{**{c.name: getattr(f, c.name) for c in Fonte.__table__.columns},
                 "total_cortes": sum(por_status.get(f.id, {}).values()), "cortes_status": por_status.get(f.id, {}),
                 "streamer_nome": st.nome, "plataforma": st.plataforma}
                for f, st in linhas]


def obter_fonte_dict(id: int) -> dict:
    streamer_id = obter_fonte(id).streamer_id
    return next(x for x in listar_fontes(streamer_id, limite=10_000) if x["id"] == id)


def salvar_fontes(streamer_id: int, itens: list[dict]) -> list[int]:
    """Insere/atualiza fontes encontradas (chave: url). Devolve os ids."""
    ids = []
    with sessao() as s:
        for it in itens:
            f = s.scalar(select(Fonte).where(Fonte.url == it["url"]))
            if f is None:
                f = Fonte(streamer_id=streamer_id, url=it["url"], tipo=it["tipo"])
                s.add(f)
            for k in ("titulo", "duracao", "views", "publicado_em", "miniatura"):
                if it.get(k) is not None:
                    setattr(f, k, it[k])
            f.extra = {**(f.extra or {}), **it.get("extra", {})}
            s.flush()
            ids.append(f.id)
    return ids


def fonte_por_url(url: str) -> Fonte | None:
    with sessao() as s:
        return s.scalar(select(Fonte).where(Fonte.url == url.strip()))


def obter_fonte(id: int) -> Fonte:
    with sessao() as s:
        f = s.get(Fonte, id)
        if f is None:
            raise KeyError(f"fonte {id} não existe")
        return f


def atualizar_fonte_extra(id: int, **campos):
    """Acrescenta chaves ao JSON `extra` da fonte (ex.: idioma detectado)."""
    with sessao() as s:
        f = s.get(Fonte, id)
        f.extra = {**(f.extra or {}), **campos}


def atualizar_fonte(id: int, **campos):
    with sessao() as s:
        f = s.get(Fonte, id)
        for k, v in campos.items():
            setattr(f, k, v)


# ------------------------------------------------------------------ cortes

def rerenderizar(corte_id: int, motivo: str = "Renderizar"):
    """Marca o corte como aprovado e enfileira o render (o vídeo pronto é trocado quando terminar)."""
    from ..jobs.fila import enfileirar  # import tardio: jobs.registro importa este módulo
    c = obter_corte(corte_id)
    atualizar_corte(corte_id, status="aprovado", erro=None)
    return enfileirar("renderizar_corte", {"corte_id": corte_id}, f"{motivo} corte #{corte_id} · {c['streamer_nome']}")


def caminho_quadro_corte(corte_id: int) -> Path:
    """Quadro do trecho do corte (fundo do editor de enquadramento e da prévia)."""
    return config.midia / "quadros" / f"corte_{corte_id}.jpg"


def caminho_miniatura_corte(corte_id: int) -> Path:
    """Miniatura do vídeo pronto (gerada do mp4 na 1ª vez que alguém pede)."""
    return config.midia / "quadros" / f"pronto_{corte_id}.jpg"


def _numeros_na_fonte(s, fonte_ids) -> dict[int, int]:
    """id do corte -> posição dele dentro do vídeo original (1 = o trecho mais cedo)."""
    num, atual, n = {}, None, 0
    for cid, fid in s.execute(select(Corte.id, Corte.fonte_id).where(Corte.fonte_id.in_(set(fonte_ids)))
                              .order_by(Corte.fonte_id, Corte.inicio, Corte.id)):
        n = n + 1 if fid == atual else 1
        atual = fid
        num[cid] = n
    return num


def corte_dict(c: Corte, f: Fonte, st: Streamer, n_na_fonte: int = 0) -> dict:
    d = {col.name: getattr(c, col.name) for col in Corte.__table__.columns}
    return {**d, "n_na_fonte": n_na_fonte, "fonte_url": f.url, "fonte_miniatura": f.miniatura,
            "fonte_publicado_em": f.publicado_em, "fonte_titulo": f.titulo, "fonte_tipo": f.tipo, "streamer_id": st.id,
            "streamer_nome": st.nome, "plataforma": st.plataforma, "conta_id": st.conta_id,
            "streamer_modelo_id": st.modelo_id, "streamer_webcam": st.webcam,
            "fonte_idioma": (f.extra or {}).get("idioma"),
            "tem_quadro": caminho_quadro_corte(c.id).exists()}


def listar_cortes(status: list[str] | None = None, streamer_id: int | None = None, fonte_id: int | None = None,
                  limite: int = 300) -> list[dict]:
    with sessao() as s:
        q = select(Corte, Fonte, Streamer).join(Fonte, Corte.fonte_id == Fonte.id).join(Streamer)
        if status:
            q = q.where(Corte.status.in_(status))
        if streamer_id:
            q = q.where(Fonte.streamer_id == streamer_id)
        if fonte_id:
            q = q.where(Corte.fonte_id == fonte_id)
        q = q.order_by(Corte.score.desc() if fonte_id else Corte.atualizado_em.desc()).limit(limite)
        linhas = s.execute(q).all()
        num = _numeros_na_fonte(s, [f.id for _, f, _ in linhas])
        return [corte_dict(c, f, st, num.get(c.id, 0)) for c, f, st in linhas]


def obter_corte(id: int) -> dict:
    with sessao() as s:
        c = s.get(Corte, id)
        if c is None:
            raise KeyError(f"corte {id} não existe")
        return corte_dict(c, c.fonte, c.fonte.streamer, _numeros_na_fonte(s, [c.fonte_id]).get(c.id, 0))


def atualizar_corte(id: int, **campos) -> dict:
    with sessao() as s:
        c = s.get(Corte, id)
        if c is None:
            raise KeyError(id)
        for k, v in campos.items():
            setattr(c, k, v)
        if c.fim <= c.inicio:
            raise ValueError("o fim do corte precisa ser depois do início")
    return obter_corte(id)


def criar_corte(fonte_id: int, **campos) -> int:
    with sessao() as s:
        c = Corte(fonte_id=fonte_id, **campos)
        s.add(c)
        s.flush()
        return c.id


def substituir_candidatos(fonte_id: int, candidatos: list[dict]) -> int:
    """Troca os candidatos não revisados de uma fonte pelos novos (mantém os já aprovados/renderizados e os que
    vieram do vigia de clipes)."""
    with sessao() as s:
        for c in s.scalars(select(Corte).where(Corte.fonte_id == fonte_id, Corte.status == "candidato")):
            if (c.extra or {}).get("origem") == "vigia":
                continue
            s.delete(c)
        for cand in candidatos:
            s.add(Corte(fonte_id=fonte_id, **cand))
    return len(candidatos)


def cortes_da_fonte(fonte_id: int) -> list[int]:
    """Ids dos cortes ainda em jogo (não descartados nem já na fila)."""
    with sessao() as s:
        return list(s.scalars(select(Corte.id).where(Corte.fonte_id == fonte_id,
                                                     Corte.status.not_in(["descartado", "na_fila"]))))


def pasta_fundos() -> Path:
    p = config.midia / "fundos"
    p.mkdir(parents=True, exist_ok=True)
    return p


def pasta_renderizados() -> Path:
    p = config.midia / "cortes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def publicar_na_fila(corte_id: int, conta_id: str | None = None) -> Path:
    """Copia o corte renderizado (+ .txt) para a pasta da conta: ele entra na fila de postagem."""
    c = obter_corte(corte_id)
    if not c["arquivo"] or not Path(c["arquivo"]).exists():
        raise ValueError("renderize o corte antes de mandar para a fila")
    conta = contas.obter(conta_id or c["conta_id"])
    destino_dir = contas.pasta_videos(conta)
    destino_dir.mkdir(parents=True, exist_ok=True)
    origem = Path(c["arquivo"])
    destino = destino_dir / origem.name
    shutil.copy2(origem, destino)
    titulo, tags = c["titulo"] or c["fonte_titulo"], contas.tags_para_cortes(conta)
    st = obter_streamer(c["streamer_id"])
    tag_streamer = "#" + slug(st.nome).replace("_", "")
    escrever_txt(destino, titulo, f"{tag_streamer} {tags}".strip())
    atualizar_corte(corte_id, status="na_fila")
    return destino
