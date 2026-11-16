"""Jobs de postagem e do pack."""
from datetime import datetime
from pathlib import Path

from ..servicos import agenda, contas, pack, postagem
from .fila import Cancelado, tarefa


def _navegador(p: dict) -> str:
    return f"navegador:{p.get('conta') or contas.PADRAO}"


def _rodar(ctx, conta, tarefas, revisar=False) -> dict:
    total = max(len(tarefas), 1)
    feitos = [0]

    def inicio(t):
        ctx.progresso(feitos[0] / total, f"{t['plataforma']} · {t['video'].name}")

    def passo(t, msg):
        ctx.progresso(None, f"{t['plataforma']} · {t['video'].name} · {msg}")

    def fim(t, r):
        feitos[0] += 1
        extra = r.get("para") or r.get("link") or r.get("erro") or ""
        ctx.progresso(feitos[0] / total, f"{t['plataforma']} · {t['video'].name}: {r['status']} {extra}")

    try:
        res = postagem.executar(conta, tarefas, revisar=revisar, ao_inicio=inicio, ao_passo=passo, ao_fim=fim,
                                cancelado=lambda: ctx.cancelado)
    except postagem.Cancelado as e:
        raise Cancelado(str(e)) from e
    ok = sum(r["status"] in postagem.OK for r in res)
    return {"ok": ok, "total": len(res), "resultados": res}


@tarefa("enviar", recurso=_navegador)
def enviar(ctx, p):
    """Posta agora: {conta, plataformas, video?, revisar?}"""
    conta = contas.obter(p.get("conta"))
    tarefas = postagem.tarefas_envio(conta, p.get("plataformas") or conta.plataformas, p.get("video"))
    if not tarefas:
        return {"ok": 0, "total": 0, "resultados": [], "mensagem": "nada a enviar"}
    return _rodar(ctx, conta, tarefas, revisar=bool(p.get("revisar")))


@tarefa("agendar", recurso=_navegador)
def agendar(ctx, p):
    """Agenda pendentes: {conta, plataformas, por_hora?, ate?}"""
    conta = contas.obter(p.get("conta"))
    plano = agenda.plano(conta, p.get("plataformas") or conta.plataformas, por_hora=p.get("por_hora"), ate=p.get("ate"))
    if not plano:
        return {"ok": 0, "total": 0, "resultados": [], "mensagem": "nada pendente"}
    ctx.log(f"{len(plano)} posts no plano")
    return _rodar(ctx, conta, plano)


@tarefa("enviar_agendado", recurso=_navegador)
def enviar_agendado(ctx, p):
    """Agenda tarefas exatas vindas da interface: {conta, tarefas: [{plataforma, video, quando}]}"""
    conta = contas.obter(p.get("conta"))
    pasta = contas.pasta_videos(conta)
    tarefas = [{"plataforma": t["plataforma"], "video": pasta / Path(t["video"]).name,
                "quando": datetime.fromisoformat(t["quando"]) if t.get("quando") else None} for t in p["tarefas"]]
    return _rodar(ctx, conta, tarefas)


@tarefa("baixar_pack", recurso="rede:pack")
def baixar_pack(ctx, p):
    """Baixa vídeos do pack de GTA 6: {qtd?, ids?}"""
    novos = pack.baixar_lote(p.get("qtd"), p.get("ids"), ao_progresso=ctx.progresso, log=ctx.log)
    return {"novos": [v.name for v in novos]}
