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


def plano(plataformas, agora: datetime | None = None):
    """[{plataforma, video(Path), quando(datetime)}] para todos os pendentes."""
    agora = agora or datetime.now()
    inicio = agora + timedelta(minutes=ANTECEDENCIA_MIN)
    hist = carregar_hist()
    out = []
    for p in plataformas:
        livres = slots(p, inicio, ocupados(p, hist))
        for v in sorted(LIMPOS.glob("*.mp4")):
            if hist.get(v.name, {}).get(p, {}).get("status") in FEITO:
                continue
            out.append({"plataforma": p, "video": v, "quando": next(livres)})
    return sorted(out, key=lambda x: (x["quando"], x["plataforma"]))


def data_yt(d: datetime) -> str:
    return f"{d.day} de {MESES_PT[d.month - 1]} de {d.year}"
