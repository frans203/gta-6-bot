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

def listar_fontes(streamer_id: int | None = None, limite: int = 200) -> list[dict]:
    with sessao() as s:
        q = select(Fonte).order_by(Fonte.id.desc()).limit(limite)
        if streamer_id:
            q = q.where(Fonte.streamer_id == streamer_id)
        fontes = list(s.scalars(q))
        n = dict(s.execute(select(Corte.fonte_id, func.count()).where(Corte.fonte_id.in_([f.id for f in fontes]))
                           .group_by(Corte.fonte_id)).all())
        return [{**{c.name: getattr(f, c.name) for c in Fonte.__table__.columns}, "total_cortes": n.get(f.id, 0)}
                for f in fontes]


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

def caminho_quadro_corte(corte_id: int) -> Path:
    """Quadro do trecho do corte (fundo do editor de enquadramento e da prévia)."""
    return config.midia / "quadros" / f"corte_{corte_id}.jpg"


def corte_dict(c: Corte, f: Fonte, st: Streamer) -> dict:
    d = {col.name: getattr(c, col.name) for col in Corte.__table__.columns}
    return {**d, "fonte_url": f.url, "fonte_titulo": f.titulo, "fonte_tipo": f.tipo, "streamer_id": st.id,
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
        return [corte_dict(c, f, st) for c, f, st in s.execute(q).all()]


def obter_corte(id: int) -> dict:
    with sessao() as s:
        c = s.get(Corte, id)
        if c is None:
            raise KeyError(f"corte {id} não existe")
        return corte_dict(c, c.fonte, c.fonte.streamer)


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


def substituir_candidatos(fonte_id: int, candidatos: list[dict]) -> int:
    """Troca os candidatos não revisados de uma fonte pelos novos (mantém os já aprovados/renderizados)."""
    with sessao() as s:
        for c in s.scalars(select(Corte).where(Corte.fonte_id == fonte_id, Corte.status == "candidato")):
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
    titulo, tags = c["titulo"] or c["fonte_titulo"], conta.tags or ""
    st = obter_streamer(c["streamer_id"])
    tag_streamer = "#" + slug(st.nome).replace("_", "")
    escrever_txt(destino, titulo, f"{tag_streamer} {tags}".strip())
    atualizar_corte(corte_id, status="na_fila")
    return destino
