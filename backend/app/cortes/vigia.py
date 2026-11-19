"""Vigia de clipes da Twitch: acha clipes novos de um streamer e transforma em cortes para revisar.

A cada `intervalo_min` (o worker agenda o job `vigiar_clipes`):
  1. pede à Helix os clipes criados nas últimas OBSERVAR_H horas (um clipe novo tem poucas views: ele fica
     "em observação" até passar de `min_views` ou sair da janela);
  2. junta clipes do MESMO momento da live (mesmo VOD, trechos que se encostam) num corte só;
  3. espera o VOD cobrir o clipe + o contexto depois (a live ainda pode estar no ar) — o `vod_offset` da Helix diz
     em que segundo da live o clipe começa;
  4. cria o corte com `antes` / `depois` segundos de contexto e já prepara (baixa o trecho, acha a webcam);
  5. PARA: o corte fica na Biblioteca esperando você revisar. Nada é renderizado nem postado sozinho.

Só usa a API oficial (Helix). Sem VOD (arquivo da live desligado) usa o próprio clipe. VOD só para inscritos: o
download falha, o corte passa para o clipe (`usar_clipe_se_vod_fechado`) e o streamer fica com `estado.vod_fechado`,
então os próximos já nascem do clipe.
"""
import math
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from ..db import sessao
from ..models import Job, Streamer
from . import edicao, fontes, servico

CONFIG_PADRAO = {
    "ativo": False,
    "intervalo_min": 5,      # de quanto em quanto tempo olha
    "min_views": 30,         # só clipes que chegaram a isso (clipe recém-criado fica em observação)
    "dur_min": 5,
    "dur_max": 90,
    "antes": 20,             # segundos de contexto antes do clipe
    "depois": 10,            # e depois
    "max_por_dia": 10,
    "auto_preparar": True,   # já baixa o trecho e procura a webcam (não renderiza)
}
OBSERVAR_H = 3                       # janela em que um clipe é acompanhado (views sobem com o tempo)
ESPERA_VOD = timedelta(minutes=30)   # clipe sem vod_offset depois disso: usa o próprio clipe
TOLERANCIA = 5.0                     # clipes a menos de 5 s um do outro = mesmo momento
MAX_RECENTES = 40
MAX_VISTOS = 2000


def config_de(st: Streamer | dict) -> dict:
    v = (st.vigia if isinstance(st, Streamer) else st.get("vigia")) or {}
    return {**CONFIG_PADRAO, **(v.get("config") or {})}


def estado_de(st: Streamer | dict) -> dict:
    v = (st.vigia if isinstance(st, Streamer) else st.get("vigia")) or {}
    return {"vistos": [], "recentes": [], "aguardando": {}, "momentos": [], "hoje": 0, "dia": None,
            **(v.get("estado") or {})}


def salvar(streamer_id: int, config: dict | None = None, estado: dict | None = None):
    with sessao() as s:
        st = s.get(Streamer, streamer_id)
        if st is None:
            raise KeyError(f"streamer {streamer_id} não existe")
        atual = dict(st.vigia or {})
        if config is not None:
            atual["config"] = {**CONFIG_PADRAO, **(atual.get("config") or {}), **config}
        if estado is not None:
            atual["estado"] = estado
        st.vigia = atual


def configurar(streamer_id: int, config: dict) -> dict:
    """Salva a configuração; ligar o vigia faz ele olhar logo na próxima volta do worker."""
    st = servico.obter_streamer(streamer_id)
    if config.get("ativo") and st.plataforma != "twitch":
        raise ValueError("o vigia de clipes só funciona com canais da Twitch (API oficial)")
    if config.get("ativo") and not fontes.TwitchAPI.disponivel():
        raise ValueError("configure JASON_TWITCH_CLIENT_ID e JASON_TWITCH_CLIENT_SECRET no .env")
    estado = estado_de(st)
    if config.get("ativo") and not config_de(st)["ativo"]:
        estado["proxima"] = datetime.now().isoformat(timespec="seconds")
    salvar(streamer_id, config=config, estado=estado)
    return resumo(servico.obter_streamer(streamer_id))


def adicionar_canal(canal: str, config: dict | None = None) -> tuple[Streamer, bool]:
    """Cadastra o canal da Twitch (se for novo) e já liga o vigia. Devolve (streamer, criado).

    Confere na Helix que o canal existe e pega o nome de exibição e o idioma da live."""
    if not fontes.TwitchAPI.disponivel():
        raise ValueError("configure JASON_TWITCH_CLIENT_ID e JASON_TWITCH_CLIENT_SECRET no .env")
    login = servico.normalizar_canal("twitch", canal)
    if not login:
        raise ValueError("informe o canal da Twitch (nome ou link)")
    d = fontes.TwitchAPI.get("users", login=login)["data"]
    if not d:
        raise ValueError(f"canal da Twitch não encontrado: {login}")
    nome, idioma = d[0].get("display_name") or login, "pt"
    try:
        ch = fontes.TwitchAPI.get("channels", broadcaster_id=d[0]["id"])["data"]
        idioma = (ch[0].get("broadcaster_language") or "pt")[:2] if ch else "pt"
    except Exception:  # noqa: BLE001 - o idioma é só um palpite
        pass
    st, criado = servico.streamer_por_canal("twitch", login, nome, idioma)
    configurar(st.id, {**(config or {}), "ativo": True})
    return servico.obter_streamer(st.id), criado


def resumo(st: Streamer) -> dict:
    e = estado_de(st)
    return {"config": config_de(st), "ultima": e.get("ultima"), "proxima": e.get("proxima"), "hoje": e["hoje"],
            "recentes": e["recentes"], "aguardando": list(e["aguardando"].values())}


# ------------------------------------------------------------------ um ciclo

def _quando(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _intervalo(c: dict, antes: float = 0, depois: float = 0) -> tuple[float, float] | None:
    if c.get("vod_offset") is None:
        return None
    return max(0.0, c["vod_offset"] - antes), c["vod_offset"] + c["duration"] + depois


def agrupar(clipes: list[dict]) -> list[list[dict]]:
    """Clipes do mesmo momento (mesmo VOD, intervalos que se encostam) viram um grupo; o mais visto primeiro."""
    grupos: list[list[dict]] = []
    for c in sorted(clipes, key=lambda x: -x["view_count"]):
        r = _intervalo(c)
        alvo = None
        if r and c.get("video_id"):
            for g in grupos:
                rg = _intervalo_grupo(g)
                if rg and g[0].get("video_id") == c["video_id"] and r[0] <= rg[1] + TOLERANCIA and rg[0] <= r[1] + TOLERANCIA:
                    alvo = g
                    break
        if alvo is not None:
            alvo.append(c)
        else:
            grupos.append([c])
    return grupos


def _intervalo_grupo(g: list[dict]) -> tuple[float, float] | None:
    rs = [r for c in g if (r := _intervalo(c))]
    return (min(r[0] for r in rs), max(r[1] for r in rs)) if rs else None


def _registro(c: dict, situacao: str, motivo: str = "", corte_id: int | None = None) -> dict:
    return {"id": c["id"], "titulo": c.get("title") or "", "views": c.get("view_count", 0), "url": c.get("url"),
            "criado": c.get("created_at"), "duracao": c.get("duration"), "situacao": situacao, "motivo": motivo,
            "corte_id": corte_id, "em": datetime.now().isoformat(timespec="seconds")}


def _miniatura(url: str | None) -> str | None:
    return url.replace("%{width}", "640").replace("%{height}", "360") if url else None


def adiar(streamer_id: int):
    """Um ciclo falhou (sem internet, Twitch fora): tenta de novo só no próximo intervalo, não a cada 30 s."""
    st = servico.obter_streamer(streamer_id)
    prox = datetime.now() + timedelta(minutes=config_de(st)["intervalo_min"])
    salvar(streamer_id, estado={**estado_de(st), "proxima": prox.isoformat(timespec="seconds")})


def ciclo(streamer_id: int, agora: datetime | None = None, log=print, enfileirar=None) -> dict:
    """Uma olhada nos clipes do streamer. `agora` (UTC) e `enfileirar` existem para os testes."""
    st = servico.obter_streamer(streamer_id)
    cfg, e = config_de(st), estado_de(st)
    agora = agora or datetime.now(UTC)
    hoje = agora.astimezone().date().isoformat()
    if e.get("dia") != hoje:
        e["dia"], e["hoje"] = hoje, 0
    vistos = set(e["vistos"])
    e["aguardando"] = {}

    clipes = fontes.TwitchAPI.clipes_entre(st.canal, agora - timedelta(hours=OBSERVAR_H), agora)
    novos_clipes = [c for c in clipes if c["id"] not in vistos]
    log(f"{len(clipes)} clipe(s) nas últimas {OBSERVAR_H} h; {len(novos_clipes)} ainda não vistos")

    candidatos = []
    for c in novos_clipes:
        if not cfg["dur_min"] <= c["duration"] <= cfg["dur_max"]:
            vistos.add(c["id"])
            e["recentes"].append(_registro(c, "ignorado", f"duração {c['duration']:.0f}s fora de "
                                                          f"{cfg['dur_min']}–{cfg['dur_max']}s"))
        elif c["view_count"] >= cfg["min_views"]:
            candidatos.append(c)
    # clipes abaixo do mínimo continuam em observação (as views sobem) até saírem da janela

    criados, aguardando = [], 0
    for grupo in agrupar(candidatos):
        principal = grupo[0]
        if e["hoje"] >= cfg["max_por_dia"]:
            e["aguardando"][principal["id"]] = _registro(principal, "aguardando", "limite de cortes por dia")
            aguardando += 1
            continue
        intervalo = _intervalo_grupo(grupo)
        # mesmo momento de um corte que o vigia já criou: não duplica
        repetido = next((m for m in e["momentos"] if intervalo and m["video_id"] == principal.get("video_id")
                         and intervalo[0] <= m["f"] + TOLERANCIA and m["i"] <= intervalo[1] + TOLERANCIA), None)
        if repetido:
            for c in grupo:
                vistos.add(c["id"])
            e["recentes"].append(_registro(principal, "ignorado", f"mesmo momento do corte #{repetido['corte_id']}"))
            continue

        fechado = e.get("vod_fechado")  # VOD só para inscritos: não dá para baixar o contexto da live
        video = fontes.TwitchAPI.video(principal["video_id"]) if principal.get("video_id") and not fechado else None
        if intervalo and video:
            precisa = intervalo[1] + cfg["depois"] + edicao.MARGEM
            if video["duracao"] < precisa:
                falta = precisa - video["duracao"]
                e["aguardando"][principal["id"]] = _registro(
                    principal, "aguardando", f"a live ainda não chegou no fim do contexto (faltam ~{falta:.0f}s)")
                aguardando += 1
                continue
            fid = servico.salvar_fontes(st.id, [{
                "url": f"https://www.twitch.tv/videos/{video['id']}", "tipo": "vod", "titulo": video["titulo"],
                "duracao": video["duracao"], "miniatura": _miniatura(video["miniatura"]),
                "publicado_em": (video["criado_em"] or "")[:16].replace("T", " ") or None}])[0]
            inicio, fim = max(0.0, intervalo[0] - cfg["antes"]), intervalo[1] + cfg["depois"]
            origem = "vod"
        elif not fechado and agora - _quando(principal["created_at"]) < ESPERA_VOD and principal.get("video_id"):
            e["aguardando"][principal["id"]] = _registro(principal, "aguardando",
                                                         "esperando a Twitch ligar o clipe ao VOD da live")
            aguardando += 1
            continue
        else:  # sem VOD: o corte é o próprio clipe (sem contexto extra)
            fid = servico.salvar_fontes(st.id, [{
                "url": principal["url"], "tipo": "clipe", "titulo": principal.get("title") or "",
                "duracao": principal["duration"], "miniatura": principal.get("thumbnail_url"),
                "views": principal["view_count"], "publicado_em": principal["created_at"][:16].replace("T", " ")}])[0]
            inicio, fim, origem = 0.0, float(principal["duration"]), "clipe"

        views = sum(c["view_count"] for c in grupo)
        forca = min(1.0, math.log1p(views) / math.log1p(2000))
        cid = servico.criar_corte(
            fid, inicio=round(inicio, 2), fim=round(fim, 2), score=round(forca, 3),
            sinais={"clipes_twitch": round(forca, 3), "views": views}, titulo=principal.get("title") or "",
            extra={"origem": "vigia", "contexto": {"antes": cfg["antes"] if origem == "vod" else 0,
                                                   "depois": cfg["depois"] if origem == "vod" else 0, "fonte": origem},
                   "clipes": [{"id": c["id"], "url": c["url"], "views": c["view_count"], "titulo": c.get("title"),
                               "criador": c.get("creator_name"), "vod_offset": c.get("vod_offset"),
                               "duracao": c["duration"]} for c in grupo]})
        for c in grupo:
            vistos.add(c["id"])
        e["hoje"] += 1
        if intervalo:
            e["momentos"] = (e["momentos"] + [{"video_id": principal["video_id"], "i": intervalo[0],
                                               "f": intervalo[1], "corte_id": cid}])[-200:]
        e["recentes"].append(_registro(principal, "corte", ("VOD só para inscritos: usei o próprio clipe" if fechado else
                                                            "sem VOD: usei o próprio clipe") if origem == "clipe" else
                                       f"+{cfg['antes']}s antes / +{cfg['depois']}s depois", cid))
        criados.append(cid)
        log(f"corte #{cid}: “{principal.get('title')}” ({views} views, {len(grupo)} clipe(s), {origem})")
        if cfg["auto_preparar"] and enfileirar:
            enfileirar("enquadrar_corte", {"corte_id": cid}, f"Preparar clipe · corte #{cid} · {st.nome}")

    e["vistos"] = list(vistos)[-MAX_VISTOS:]
    e["recentes"] = e["recentes"][-MAX_RECENTES:]
    e["ultima"] = datetime.now().isoformat(timespec="seconds")
    e["proxima"] = (datetime.now() + timedelta(minutes=cfg["intervalo_min"])).isoformat(timespec="seconds")
    salvar(st.id, estado=e)
    return {"novos": len(criados), "cortes": criados, "aguardando": aguardando, "clipes": len(clipes)}


# ------------------------------------------------------------------ VOD só para inscritos

def vod_fechado(erro: Exception | str) -> bool:
    t = str(erro).lower()
    return "subscriber-only" in t or "subscriber only" in t or "must be logged into an account" in t


def usar_clipe_se_vod_fechado(c: dict, erro: Exception, log=print) -> dict | None:
    """O VOD de um corte do vigia não baixa (só para inscritos): o corte passa a ser o clipe mais visto do grupo e o
    streamer fica marcado para os próximos cortes já nascerem do clipe. Devolve o corte atualizado (ou None)."""
    extra = c.get("extra") or {}
    clipes = extra.get("clipes") or []
    if not vod_fechado(erro) or c.get("fonte_tipo") != "vod" or extra.get("origem") != "vigia" or not clipes:
        return None
    cl = max(clipes, key=lambda x: x.get("views") or 0)
    fid = servico.salvar_fontes(c["streamer_id"], [{"url": cl["url"], "tipo": "clipe", "titulo": cl.get("titulo") or "",
                                                    "duracao": cl["duracao"], "views": cl.get("views")}])[0]
    novo = servico.atualizar_corte(c["id"], fonte_id=fid, inicio=0.0, fim=float(cl["duracao"]), extra={
        **extra, "contexto": {"antes": 0, "depois": 0, "fonte": "clipe", "motivo": "VOD só para inscritos"}})
    st = servico.obter_streamer(c["streamer_id"])
    salvar(st.id, estado={**estado_de(st), "vod_fechado": True})
    log("o VOD é só para inscritos: usando o próprio clipe (sem o contexto antes/depois)")
    return novo


# ------------------------------------------------------------------ agendamento (chamado pelo worker)

def agendar(enfileirar, agora: datetime | None = None) -> list[int]:
    """Enfileira `vigiar_clipes` para os streamers vigiados cuja hora chegou (sem repetir um que já está na fila)."""
    agora = agora or datetime.now()
    with sessao() as s:
        sts = [(st.id, st.nome, st.vigia) for st in s.scalars(select(Streamer).where(Streamer.vigia.is_not(None)))]
        ativos_fila = {j.params.get("streamer_id") for j in s.scalars(
            select(Job).where(Job.tipo == "vigiar_clipes", Job.status.in_(("fila", "rodando", "cancelando"))))}
        # jobs do vigia que não acharam nada viram ruído na tela Jobs: some depois de 2 h
        limite = datetime.now() - timedelta(hours=2)
        for j in s.scalars(select(Job).where(Job.tipo == "vigiar_clipes", Job.status == "ok",
                                             Job.terminado_em < limite)):
            if not (j.resultado or {}).get("novos"):
                s.delete(j)
    feitos = []
    for sid, nome, vigia in sts:
        cfg, e = config_de({"vigia": vigia}), estado_de({"vigia": vigia})
        if not cfg["ativo"] or sid in ativos_fila:
            continue
        if e.get("proxima") and datetime.fromisoformat(e["proxima"]) > agora:
            continue
        enfileirar("vigiar_clipes", {"streamer_id": sid}, f"Vigia de clipes · {nome}")
        feitos.append(sid)
    return feitos
