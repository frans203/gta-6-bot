"""Tabelas do banco (SQLAlchemy 2.0). Mudou algo aqui? Gere uma migração:
    cd backend; alembic revision --autogenerate -m "descricao"
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[str]: JSON}


def agora() -> datetime:
    return datetime.now().replace(microsecond=0)


class Conta(Base):
    """Um conjunto de perfis (TikTok + YouTube + Instagram) logados num mesmo perfil do Chrome."""
    __tablename__ = "contas"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)     # slug: gta6, gamer_en
    nome: Mapped[str] = mapped_column(String(100))
    idioma: Mapped[str] = mapped_column(String(5), default="pt")
    pasta: Mapped[str] = mapped_column(String(500))                    # vídeos prontos (.mp4 + .txt)
    perfil: Mapped[str] = mapped_column(String(500))                   # pasta do perfil do Chrome
    plataformas: Mapped[list[str]] = mapped_column(default=lambda: ["tiktok", "youtube", "instagram"])
    tags: Mapped[str] = mapped_column(Text, default="")               # hashtags padrão dos cortes
    padrao: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Post(Base):
    """Estado de um vídeo numa plataforma (antigo postados.json)."""
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("conta_id", "video", "plataforma"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conta_id: Mapped[str] = mapped_column(ForeignKey("contas.id"), index=True)
    video: Mapped[str] = mapped_column(String(200), index=True)        # nome do arquivo (gta6_001.mp4)
    plataforma: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30))
    para: Mapped[str | None] = mapped_column(String(20))               # ISO "2026-11-14T19:00" (agendado)
    link: Mapped[str | None] = mapped_column(String(500))
    erro: Mapped[str | None] = mapped_column(Text)
    print: Mapped[str | None] = mapped_column(String(200))
    tarefa: Mapped[str | None] = mapped_column(String(200))
    obs: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[dict[str, Any]] = mapped_column(default=dict)
    em: Mapped[str] = mapped_column(String(20))                        # ISO de quando foi registrado


class Modelo(Base):
    """Modelo de corte: como o vertical é montado (layout + posições + estilo de legenda)."""
    __tablename__ = "modelos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    layout: Mapped[str] = mapped_column(String(40))                    # plugin de layout (cortes/layouts.py)
    estilo_legenda: Mapped[str] = mapped_column(String(40), default="destaque")
    # divisao (fração da altura para o jogo), legenda_y / gancho_y (fração da altura), barra, credito
    params: Mapped[dict[str, Any]] = mapped_column(default=dict)
    padrao: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Streamer(Base):
    __tablename__ = "streamers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    plataforma: Mapped[str] = mapped_column(String(20))                # twitch | youtube
    canal: Mapped[str] = mapped_column(String(200))                    # login da Twitch ou @handle do YouTube
    idioma: Mapped[str] = mapped_column(String(5), default="pt")
    conta_id: Mapped[str | None] = mapped_column(ForeignKey("contas.id"))
    # última webcam confirmada {x,y,w,h} 0..1: só sugestão inicial no enquadramento de cada corte
    webcam: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    modelo_id: Mapped[int | None] = mapped_column(ForeignKey("modelos.id", ondelete="SET NULL"))  # None = padrão
    campanha_url: Mapped[str | None] = mapped_column(String(500))
    notas: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)

    fontes: Mapped[list["Fonte"]] = relationship(back_populates="streamer", cascade="all, delete-orphan")


class Fonte(Base):
    """Um VOD ou clipe encontrado num canal (matéria-prima dos cortes)."""
    __tablename__ = "fontes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    streamer_id: Mapped[int] = mapped_column(ForeignKey("streamers.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))                      # vod | clipe
    url: Mapped[str] = mapped_column(String(500), unique=True)
    titulo: Mapped[str] = mapped_column(String(500), default="")
    duracao: Mapped[float | None] = mapped_column(Float)
    views: Mapped[int | None] = mapped_column(Integer)
    publicado_em: Mapped[str | None] = mapped_column(String(20))
    miniatura: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="nova")    # nova | analisando | analisada | erro
    extra: Mapped[dict[str, Any]] = mapped_column(default=dict)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)

    streamer: Mapped[Streamer] = relationship(back_populates="fontes")
    cortes: Mapped[list["Corte"]] = relationship(back_populates="fonte", cascade="all, delete-orphan")


class Corte(Base):
    """Um trecho candidato/aprovado/renderizado."""
    __tablename__ = "cortes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fonte_id: Mapped[int] = mapped_column(ForeignKey("fontes.id"), index=True)
    inicio: Mapped[float] = mapped_column(Float)
    fim: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float, default=0)
    sinais: Mapped[dict[str, Any]] = mapped_column(default=dict)       # {chat: 0.8, audio: 0.4, ...}
    # candidato | enquadrar | aprovado | renderizando | pronto | na_fila | descartado | erro
    status: Mapped[str] = mapped_column(String(20), default="candidato", index=True)
    modelo_id: Mapped[int | None] = mapped_column(ForeignKey("modelos.id", ondelete="SET NULL"))  # None = do streamer
    estilo_legenda: Mapped[str | None] = mapped_column(String(40))     # None = do modelo
    # enquadramento deste corte, em frações do quadro original: {x,y,w,h, origem: auto|manual, confianca}
    webcam: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    jogo: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)  # None = quadro inteiro (recorte central)
    idioma_legenda: Mapped[str | None] = mapped_column(String(5))      # None = o idioma falado (sem traduzir)
    fundo: Mapped[str | None] = mapped_column(String(200))             # imagem de fundo (midia/fundos/<nome>)
    # o que o enquadramento descobriu: {idioma, idioma_prob, espaco_preto, area_util: {x,y,w,h}}
    extra: Mapped[dict[str, Any]] = mapped_column(default=dict)
    titulo: Mapped[str] = mapped_column(String(300), default="")
    gancho: Mapped[str | None] = mapped_column(String(120))            # texto no topo nos 1os segundos
    arquivo: Mapped[str | None] = mapped_column(String(500))           # mp4 renderizado
    transcricao: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    # editor de vídeo: trechos (tempos da live), layout livre e estilo do texto. None = só o modelo de corte
    edicao: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    erro: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora, onupdate=agora)

    fonte: Mapped[Fonte] = relationship(back_populates="cortes")


class Job(Base):
    """Tarefa longa executada pelo worker (postar, baixar, analisar, renderizar...)."""
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), index=True)
    titulo: Mapped[str] = mapped_column(String(300), default="")
    params: Mapped[dict[str, Any]] = mapped_column(default=dict)
    recurso: Mapped[str | None] = mapped_column(String(80))            # jobs com o mesmo recurso rodam 1 por vez
    # fila | rodando | ok | erro | cancelando | cancelado
    status: Mapped[str] = mapped_column(String(20), default="fila", index=True)
    progresso: Mapped[float | None] = mapped_column(Float)            # 0..1 (None = indeterminado)
    mensagem: Mapped[str] = mapped_column(String(500), default="")
    resultado: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    erro: Mapped[str | None] = mapped_column(Text)
    log: Mapped[str] = mapped_column(Text, default="")
    pid: Mapped[int | None] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime)
    terminado_em: Mapped[datetime | None] = mapped_column(DateTime)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora, onupdate=agora, index=True)
