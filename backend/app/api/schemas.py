"""Modelos de entrada/saída da API (viram tipos TypeScript no front via OpenAPI)."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Plataforma = Literal["tiktok", "youtube", "instagram"]


class Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ contas e vídeos

class ContaOut(Saida):
    id: str
    nome: str
    idioma: str
    pasta: str
    perfil: str
    plataformas: list[str]
    tags: str
    padrao: bool


class ContaIn(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]{2,40}$")
    nome: str
    idioma: Literal["pt", "en", "es"] = "pt"
    plataformas: list[Plataforma] = ["tiktok", "youtube", "instagram"]
    tags: str | None = None


class ContaPatch(BaseModel):
    nome: str | None = None
    idioma: Literal["pt", "en", "es"] | None = None
    plataformas: list[Plataforma] | None = None
    tags: str | None = None


class EstadoPlataforma(BaseModel):
    status: str                      # pendente | publicado | agendado | agendado_pc | atrasado | erro | ...
    para: str | None = None
    link: str | None = None


class TextoYoutube(BaseModel):
    titulo: str | None = Field(None, max_length=100)
    descricao: str | None = Field(None, max_length=5000)


class TextoLegenda(BaseModel):
    legenda: str | None = Field(None, max_length=2200)


class TextosRedes(BaseModel):
    """Personalização por rede: vazio = usa o texto geral."""
    youtube: TextoYoutube = TextoYoutube()
    tiktok: TextoLegenda = TextoLegenda()
    instagram: TextoLegenda = TextoLegenda()


class TextosIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=100)
    descricao: str = Field("", max_length=2000)
    tags: str = Field("", max_length=1000, description="hashtags separadas por espaço")
    redes: TextosRedes = TextosRedes()


class TextosOut(BaseModel):
    titulo: str
    descricao: str
    tags: str
    redes: dict[str, dict[str, str]]
    finais: dict[str, dict[str, str]] = Field(description="o que cada rede vai receber de fato")


class HashtagsLoteIn(BaseModel):
    tags: str = Field(min_length=1, max_length=1000)
    modo: Literal["substituir", "adicionar"] = "substituir"
    videos: list[str] | None = Field(None, description="None = todos os vídeos ainda não postados em nenhuma rede")


class EstadoRedeIn(BaseModel):
    status: Literal["removido", "pendente"] = Field(description="removido = não postar nesta rede; pendente = volta")


class VideoOut(BaseModel):
    video: str
    mb: float
    titulo: str | None
    tags: str | None
    descricao: str = ""
    redes: dict[str, dict[str, str]] = {}
    plataformas: dict[str, EstadoPlataforma]


class LegendaIn(BaseModel):
    titulo: str
    tags: str


class PlanoItem(BaseModel):
    plataforma: str
    video: str
    quando: datetime
    como: Literal["nativo", "windows"]


class AgendarIn(BaseModel):
    plataformas: list[Plataforma] | None = None
    por_hora: int | None = Field(None, ge=1, le=12)
    ate: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")


class EnviarIn(BaseModel):
    plataformas: list[Plataforma] | None = None
    video: str | None = None
    revisar: bool = False


class PostOut(Saida):
    id: int
    conta_id: str
    video: str
    plataforma: str
    status: str
    para: str | None
    link: str | None
    erro: str | None
    print: str | None
    tarefa: str | None
    obs: str | None
    em: str


class PostPatch(BaseModel):
    status: str | None = None
    para: str | None = None
    link: str | None = None
    obs: str | None = None


# ------------------------------------------------------------------ jobs

class JobOut(Saida):
    id: int
    tipo: str
    titulo: str
    params: dict[str, Any]
    recurso: str | None
    status: str                      # fila | rodando | ok | erro | cancelando | cancelado
    progresso: float | None
    mensagem: str
    resultado: dict[str, Any] | None
    erro: str | None
    criado_em: datetime
    iniciado_em: datetime | None
    terminado_em: datetime | None
    atualizado_em: datetime


class JobDetalheOut(JobOut):
    log: str


class PackIn(BaseModel):
    qtd: int | None = Field(5, ge=1, le=100)
    ids: list[int] | None = None


# ------------------------------------------------------------------ cortador

class Regiao(BaseModel):
    """Retângulo no quadro original, em frações 0..1."""
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class Webcam(Regiao):
    confianca: float | None = Field(None, description="fração das amostras em que o rosto apareceu (detecção)")
    origem: Literal["auto", "manual", "sugerida"] | None = Field(
        None, description="auto = detectada com segurança; manual = marcada por você; sugerida = precisa conferir")


# ------------------------------------------------------------------ editor de vídeo

COR = r"^[0-9A-Fa-f]{6}$"


class TrechoEd(BaseModel):
    """Um pedaço do vídeo, em segundos da live/vídeo original (como corte.inicio/fim)."""
    i: float = Field(ge=0)
    f: float = Field(gt=0)


class LegendaEd(BaseModel):
    fonte: str = Field("Arial Black", max_length=80)
    tamanho: int = Field(74, ge=20, le=220)
    cor: str = Field("FFFFFF", pattern=COR)
    destaque: str = Field("FFE400", pattern=COR, description="cor da palavra que está sendo falada")
    contorno: int = Field(7, ge=0, le=24)
    maiusculas: bool = True
    por_bloco: int = Field(3, ge=1, le=8, description="palavras na tela por vez")
    y: float = Field(0.55, ge=0.03, le=0.97, description="centro da legenda (fração da altura)")
    mostrar: bool = True


class GanchoEd(BaseModel):
    fonte: str = Field("Arial Black", max_length=80)
    tamanho: int = Field(64, ge=20, le=200)
    cor: str = Field("000000", pattern=COR)
    fundo: str = Field("FFFFFF", pattern=COR, description="cor da caixa atrás do texto")
    y: float = Field(0.05, ge=0.0, le=0.9, description="topo do texto (fração da altura)")


class Caixa(BaseModel):
    """Retângulo no vídeo final 1080x1920, em frações (pode sair um pouco da tela)."""
    x: float = Field(ge=-1, le=1)
    y: float = Field(ge=-1, le=1)
    w: float = Field(gt=0.02, le=2)
    h: float = Field(gt=0.02, le=2)


class ZonaEd(BaseModel):
    saida: Caixa = Field(description="onde fica no vídeo final")
    fonte: Regiao | None = Field(None, description="o que recortar do vídeo original (None = do corte)")


class LayoutEd(BaseModel):
    jogo: ZonaEd
    webcam: ZonaEd | None = Field(None, description="None = sem o streamer")
    fundo: Literal["desfocado", "preto", "imagem"] = "desfocado"
    webcam_na_frente: bool = True


class Edicao(BaseModel):
    """Edição livre de um corte (editor de vídeo). Substitui as posições do modelo de corte."""
    segmentos: list[TrechoEd] = Field(min_length=1, max_length=60, description="na ordem em que entram no vídeo")
    sincronizado: bool = Field(True, description="streamer e jogo sempre juntos (os cortes valem para os dois)")
    atraso_streamer: float = Field(0.0, ge=-3, le=3, description="só sem sincronia: + = streamer aparece depois")
    legenda: LegendaEd = LegendaEd()
    gancho: GanchoEd = GanchoEd()
    layout: LayoutEd


class FonteTexto(BaseModel):
    nome: str
    arquivo: str | None = Field(None, description="fonte enviada por você (midia/fontes); None = do sistema")


class EditorOut(BaseModel):
    pronto: bool = Field(description="trecho baixado e transcrito: dá para editar")
    largura: int = 0
    altura: int = 0
    duracao: float = 0.0
    base: float = Field(0.0, description="segundo da live em que o arquivo do trecho começa")
    palavras: list[dict[str, Any]] = Field([], description="legenda {p, i, f} em segundos do arquivo do trecho")
    edicao: Edicao | None = None
    padrao: Edicao | None = Field(None, description="como o modelo de corte deixaria (ponto de partida)")
    fontes: list[FonteTexto] = []
    credito: str = ""
    barra: bool = True
    fundo_imagem: str | None = None


class ModeloParams(BaseModel):
    """Posições do modelo de corte, em frações da altura do vídeo final (0 = topo, 1 = base)."""
    model_config = ConfigDict(extra="allow")
    divisao: float | None = Field(None, ge=0.2, le=0.8, description="fração da altura que fica com a 1ª área")
    legenda_y: float | None = Field(None, ge=0.03, le=0.97, description="centro da legenda")
    gancho_y: float | None = Field(None, ge=0.0, le=0.9, description="topo do texto de gancho")
    topo: float | None = Field(None, ge=0.0, le=0.4, description="(fundo com imagem) onde o vídeo começa")
    fundo: str | None = Field(None, description="(fundo com imagem) imagem padrão do modelo, em midia/fundos")
    barra: bool = True
    credito: bool = True


class ModeloOut(Saida):
    id: int
    nome: str
    layout: str
    estilo_legenda: str
    params: ModeloParams
    padrao: bool


class ModeloIn(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    layout: str
    estilo_legenda: str = "destaque"
    params: ModeloParams = ModeloParams()
    padrao: bool = False


class ModeloPatch(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=100)
    layout: str | None = None
    estilo_legenda: str | None = None
    params: ModeloParams | None = None
    padrao: bool | None = None


class PreviaIn(BaseModel):
    """Prévia de 1 quadro. Sem modelo_id usa os campos soltos (para o editor de modelos)."""
    modelo_id: int | None = None
    layout: str | None = None
    estilo_legenda: str | None = None
    params: ModeloParams | None = None
    corte_id: int | None = Field(None, description="usa o quadro, a webcam e o jogo deste corte")
    streamer_id: int | None = Field(None, description="usa o quadro de referência deste streamer")
    webcam: Regiao | None = None
    jogo: Regiao | None = None
    gancho: str | None = None
    fundo: str | None = Field(None, description="imagem de fundo (nome em midia/fundos)")
    edicao: Edicao | None = Field(None, description="prévia com a edição do editor de vídeo")


PlataformaVideo = Literal["twitch", "youtube", "kick", "outro"]


class StreamerOut(Saida):
    id: int
    nome: str
    plataforma: PlataformaVideo
    canal: str
    idioma: str
    conta_id: str | None
    webcam: Webcam | None
    modelo_id: int | None
    campanha_url: str | None
    notas: str | None
    ativo: bool
    criado_em: datetime
    total_fontes: int = 0
    total_cortes: int = 0


class StreamerIn(BaseModel):
    nome: str
    plataforma: Literal["twitch", "youtube"]
    canal: str
    idioma: Literal["pt", "en", "es"] = "pt"
    conta_id: str | None = None
    modelo_id: int | None = None
    campanha_url: str | None = None
    notas: str | None = None


class StreamerPatch(BaseModel):
    nome: str | None = None
    canal: str | None = None
    idioma: Literal["pt", "en", "es"] | None = None
    conta_id: str | None = None
    modelo_id: int | None = None
    campanha_url: str | None = None
    notas: str | None = None
    ativo: bool | None = None
    webcam: Webcam | None = None


class BuscarFontesIn(BaseModel):
    tipo: Literal["vod", "clipe"] = "vod"
    limite: int = Field(5, ge=1, le=50)
    periodo_dias: int = Field(7, ge=1, le=365)


class FonteOut(Saida):
    id: int
    streamer_id: int
    tipo: Literal["vod", "clipe"]
    url: str
    titulo: str
    duracao: float | None
    views: int | None
    publicado_em: str | None
    miniatura: str | None
    status: str
    criado_em: datetime
    total_cortes: int = 0
    cortes_status: dict[str, int] = {}
    streamer_nome: str = ""
    plataforma: str = ""


class FonteIn(BaseModel):
    streamer_id: int
    url: str


class AnalisarIn(BaseModel):
    max_cortes: int = Field(8, ge=1, le=40)
    duracao: int = Field(45, ge=15, le=180, description="duração alvo de cada corte, em segundos")
    detectores: list[str] | None = None


class CorteOut(Saida):
    id: int
    fonte_id: int
    inicio: float
    fim: float
    score: float
    sinais: dict[str, Any]
    status: str          # candidato | enquadrar | aprovado | renderizando | pronto | na_fila | descartado | erro
    modelo_id: int | None
    estilo_legenda: str | None
    webcam: Webcam | None
    jogo: Regiao | None
    titulo: str
    gancho: str | None
    arquivo: str | None
    erro: str | None
    criado_em: datetime
    atualizado_em: datetime
    n_na_fonte: int = 0  # posição do corte dentro do vídeo original (1 = o trecho mais cedo)
    # dados da fonte/streamer para a tela não precisar de N requisições
    fonte_url: str = ""
    fonte_miniatura: str | None = None
    fonte_publicado_em: str | None = None
    fonte_titulo: str = ""
    fonte_tipo: str = ""
    streamer_id: int = 0
    streamer_nome: str = ""
    plataforma: str = ""
    conta_id: str | None = None
    streamer_modelo_id: int | None = None
    streamer_webcam: Webcam | None = None
    tem_quadro: bool = False
    idioma_legenda: str | None = None
    fundo: str | None = None
    extra: dict[str, Any] = {}
    fonte_idioma: str | None = None
    edicao: Edicao | None = None


class CortePatch(BaseModel):
    inicio: float | None = Field(None, ge=0)
    fim: float | None = Field(None, gt=0)
    titulo: str | None = None
    gancho: str | None = None
    modelo_id: int | None = None
    estilo_legenda: str | None = None
    webcam: Regiao | None = Field(None, description="marcada à mão (vira origem 'manual')")
    jogo: Regiao | None = None
    idioma_legenda: Literal["pt", "en", "es"] | None = None
    fundo: str | None = None
    sem_webcam: bool | None = Field(None, description="true = este corte não tem o streamer (sai sem a webcam)")
    status: Literal["candidato", "descartado"] | None = None
    edicao: Edicao | None = Field(None, description="editor de vídeo; null volta para o modelo de corte")


class AplicarCortesIn(BaseModel):
    """Aplica os mesmos ajustes a todos os cortes de um vídeo (os que não foram descartados)."""
    modelo_id: int | None = None
    idioma_legenda: Literal["pt", "en", "es"] | None = None
    fundo: str | None = None
    estilo_legenda: str | None = None


class IdentificarIn(BaseModel):
    url: str = Field(min_length=8)


class IdentificarOut(BaseModel):
    url: str
    plataforma: PlataformaVideo
    site: str
    tipo: Literal["vod", "clipe"]
    canal: str
    canal_nome: str
    titulo: str
    duracao: float | None
    views: int | None
    publicado_em: str | None
    miniatura: str | None
    idioma: str | None
    largura: int | None
    altura: int | None
    streamer_id: int | None = Field(None, description="streamer já cadastrado (dono do vídeo, se ele já existe)")
    streamer_nome: str | None = None
    streamer_modelo_id: int | None = Field(None, description="modelo de corte do streamer (None = o padrão)")
    fonte_id: int | None = Field(None, description="este vídeo já foi adicionado antes")


class CortarVideoIn(BaseModel):
    url: str = Field(min_length=8)
    quantidade: int = Field(3, ge=1, le=20)
    duracao: int = Field(45, ge=15, le=180)
    modelo_id: int | None = None


class CortarVideoOut(BaseModel):
    job: "JobOut"
    fonte_id: int
    streamer_id: int
    streamer_criado: bool


class FundoOut(BaseModel):
    nome: str
    kb: int


class PublicarCorteIn(BaseModel):
    conta_id: str | None = None      # padrão: conta do streamer


class PluginOut(BaseModel):
    id: str
    nome: str
    descricao: str
    opcoes: dict[str, Any]


class PluginsOut(BaseModel):
    layouts: list[PluginOut]
    estilos: list[PluginOut]
    detectores: list[PluginOut]
    plataformas: list[str]


class SistemaOut(BaseModel):
    versao: str
    agora: datetime
    midia: str
    disco_livre_gb: dict[str, float]
    worker_ativo: bool
    gpu: str | None
    twitch_api: bool
    whisper_modelo: str


class TarefaWindowsOut(BaseModel):
    nome: str
    proxima: str
    estado: str


class Grade(BaseModel):
    semana: list[str]
    fimdesemana: list[str]
