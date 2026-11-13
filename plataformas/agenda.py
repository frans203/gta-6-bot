"""Monta o plano de agendamento: proximo horario livre da grade para cada video pendente."""
import json
from datetime import datetime, timedelta

from .comum import LIMPOS, RAIZ, carregar_hist

GRADE = json.loads((RAIZ / "horarios.json").read_text("utf-8"))
ANTECEDENCIA_MIN = 30          # TikTok exige >= 15 min; damos folga para o upload
MESES_PT = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]

FEITO = ("publicado", "agendado", "agendado_pc", "pulado_reivindicacao")


def slots(plataforma, a_partir: datetime, ocupados: set):
    """Gera horarios livres da grade a partir de `a_partir`."""
    dia = a_partir.date()
    while True:
        tipo = "fimdesemana" if dia.weekday() >= 5 else "semana"
        for hhmm in GRADE[plataforma][tipo]:
            h, m = map(int, hhmm.split(":"))
            quando = datetime(dia.year, dia.month, dia.day, h, m)
            if quando >= a_partir and quando not in ocupados:
                yield quando
        dia += timedelta(days=1)


def ocupados(plataforma, hist):
    out = set()
    for info in hist.values():
        p = info.get(plataforma, {})
        if p.get("status") in ("agendado", "agendado_pc") and p.get("para"):
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


def plano(plataformas, agora: datetime | None = None, por_hora: int | None = None, ate: str | None = None):
    """[{plataforma, video(Path), quando(datetime)}] para os pendentes.
    Padrao: grade do horarios.json, todos os pendentes. Com por_hora/ate: lote de N por hora ate o limite
    (o que nao couber fica pendente)."""
    agora = agora or datetime.now()
    inicio = agora + timedelta(minutes=ANTECEDENCIA_MIN)
    fim = limite(ate or "00:00", agora) if (por_hora or ate) else None
    hist = carregar_hist()
    out = []
    for p in plataformas:
        oc = ocupados(p, hist)
        livres = slots_por_hora(por_hora or 5, inicio, fim, oc) if fim else slots(p, inicio, oc)
        for v in sorted(LIMPOS.glob("*.mp4")):
            if hist.get(v.name, {}).get(p, {}).get("status") in FEITO:
                continue
            quando = next(livres, None)
            if quando is None:
                break
            out.append({"plataforma": p, "video": v, "quando": quando})
    return sorted(out, key=lambda x: (x["quando"], x["plataforma"]))


def data_yt(d: datetime) -> str:
    return f"{d.day} de {MESES_PT[d.month - 1]} de {d.year}"
