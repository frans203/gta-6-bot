"""Monta o plano de agendamento: proximo horario livre da grade para cada video pendente de uma conta."""
import json
from datetime import datetime, timedelta
from pathlib import Path

from ..config import config

HORARIOS = config.raiz / "horarios.json"
ANTECEDENCIA_MIN = 30          # TikTok exige >= 15 min; damos folga para o upload
MESES_PT = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]

FEITO = ("publicado", "agendado", "agendado_pc", "pulado_reivindicacao", "removido")  # removido = não postar
ATRASO_PC = timedelta(hours=1)  # agendado_pc vencido ha mais que isso = tarefa do Windows nao rodou


def grade() -> dict:
    return json.loads(HORARIOS.read_text("utf-8"))


def salvar_grade(g: dict):
    HORARIOS.write_text(json.dumps(g, indent=2, ensure_ascii=False), "utf-8")


def feito(info: dict, agora: datetime | None = None) -> bool:
    """Ja foi (ou vai ser) postado nessa plataforma? agendado_pc vencido conta como pendente de novo."""
    st = info.get("status")
    if st == "agendado_pc" and info.get("para"):
        return datetime.fromisoformat(info["para"]) > (agora or datetime.now()) - ATRASO_PC
    return st in FEITO


def slots(plataforma, a_partir: datetime, ocupados: set, g: dict | None = None):
    """Gera horarios livres da grade a partir de `a_partir`."""
    g = g or grade()
    dia = a_partir.date()
    while True:
        tipo = "fimdesemana" if dia.weekday() >= 5 else "semana"
        for hhmm in g[plataforma][tipo]:
            h, m = map(int, hhmm.split(":"))
            quando = datetime(dia.year, dia.month, dia.day, h, m)
            if quando >= a_partir and quando not in ocupados:
                yield quando
        dia += timedelta(days=1)


def ocupados(plataforma, hist):
    out = set()
    for info in hist.values():
        p = info.get(plataforma, {})
        if p.get("status") in ("agendado", "agendado_pc") and p.get("para") and feito(p):
            out.add(datetime.fromisoformat(p["para"]))
    return out


def slots_por_hora(por_hora: int, a_partir: datetime, ate: datetime, ocupados: set):
    """Modo lote: `por_hora` horarios espalhados em cada hora (minutos multiplos de 5, exigencia do TikTok)
    de `a_partir` ate `ate` (exclusivo). Ex.: 5/h -> :00 :10 :25 :35 :50."""
    minutos = sorted({min(int(5 * round(i * 60 / por_hora / 5)), 55) for i in range(por_hora)})
    hora = a_partir.replace(minute=0, second=0, microsecond=0)
    while hora < ate:
        for m in minutos:
            quando = hora + timedelta(minutes=m)
            if a_partir <= quando < ate and quando not in ocupados:
                yield quando
        hora += timedelta(hours=1)


def limite(hhmm: str, agora: datetime) -> datetime:
    """'00:00' -> proxima meia-noite; '23:00' -> hoje 23h (ou amanha, se ja passou)."""
    h, m = map(int, hhmm.split(":"))
    d = agora.replace(hour=h, minute=m, second=0, microsecond=0)
    return d if d > agora else d + timedelta(days=1)


def montar_plano(videos: list[Path], hist: dict, plataformas, agora: datetime | None = None,
                 por_hora: int | None = None, ate: str | None = None, g: dict | None = None):
    """Função pura (testável): [{plataforma, video(Path), quando(datetime)}] para os pendentes.
    Padrao: grade do horarios.json, todos os pendentes. Com por_hora/ate: lote de N por hora ate o limite
    (o que nao couber fica pendente)."""
    agora = agora or datetime.now()
    inicio = agora + timedelta(minutes=ANTECEDENCIA_MIN)
    fim = limite(ate or "00:00", agora) if (por_hora or ate) else None
    out = []
    for p in plataformas:
        oc = ocupados(p, hist)
        livres = slots_por_hora(por_hora or 5, inicio, fim, oc) if fim else slots(p, inicio, oc, g)
        for v in videos:
            if feito(hist.get(v.name, {}).get(p, {}), agora):
                continue
            quando = next(livres, None)
            if quando is None:
                break
            out.append({"plataforma": p, "video": v, "quando": quando})
    return sorted(out, key=lambda x: (x["quando"], x["plataforma"]))


def plano(conta, plataformas, agora: datetime | None = None, por_hora: int | None = None, ate: str | None = None):
    from . import contas, historico
    return montar_plano(contas.videos(conta), historico.carregar_hist(conta.id), plataformas, agora, por_hora, ate)


def data_yt(d: datetime) -> str:
    return f"{d.day} de {MESES_PT[d.month - 1]} de {d.year}"


# ------------------------------------------------------------------ agendar um vídeo pela interface

def _ocupados_por(plataforma, hist, agora: datetime) -> dict[datetime, str]:
    """{horário: vídeo} já agendados nessa rede (para avisar conflito)."""
    out = {}
    for video, redes in hist.items():
        p = redes.get(plataforma, {})
        if p.get("status") in ("agendado", "agendado_pc") and p.get("para") and feito(p, agora):
            out[datetime.fromisoformat(p["para"])] = video
    return out


def sugestoes(hist: dict, plataformas, dias: int = 3, agora: datetime | None = None, g: dict | None = None) -> dict:
    """Melhores horários (grade do horarios.json) dos próximos `dias` dias, por rede.
    {rede: [{quando, destaque, ocupado_por, disponivel}]}. `disponivel` = respeita a antecedência mínima."""
    agora = agora or datetime.now()
    g = g or grade()
    destaques = g.get("_destaques", {})
    minimo = agora + timedelta(minutes=ANTECEDENCIA_MIN)
    out = {}
    for p in plataformas:
        oc = _ocupados_por(p, hist, agora)
        lista = []
        for d in range(dias):
            dia = (agora + timedelta(days=d)).date()
            tipo = "fimdesemana" if dia.weekday() >= 5 else "semana"
            for hhmm in g[p][tipo]:
                h, m = map(int, hhmm.split(":"))
                quando = datetime(dia.year, dia.month, dia.day, h, m)
                if quando < agora:
                    continue
                lista.append({"quando": quando, "destaque": hhmm in destaques.get(p, []),
                              "ocupado_por": oc.get(quando), "disponivel": quando >= minimo})
        out[p] = lista
    return out


def validar_itens(itens: list[dict], estado_video: dict, agora: datetime | None = None) -> list[str]:
    """Erros de um agendamento [{plataforma, quando}] de UM vídeo. Lista vazia = pode agendar."""
    agora = agora or datetime.now()
    erros, vistas = [], set()
    for it in itens:
        p, q = it["plataforma"], it["quando"]
        if p in vistas:
            erros.append(f"{p}: só um horário por rede")
        vistas.add(p)
        if feito(estado_video.get(p, {}), agora):
            erros.append(f"{p}: este vídeo já está {estado_video[p].get('status')} nessa rede")
        if q < agora + timedelta(minutes=ANTECEDENCIA_MIN):
            erros.append(f"{p}: escolha um horário a pelo menos {ANTECEDENCIA_MIN} min de agora")
        if q.minute % 5 or q.second:
            erros.append(f"{p}: o minuto precisa ser múltiplo de 5 (exigência do TikTok)")
    return erros
