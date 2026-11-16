from datetime import datetime
from pathlib import Path

from app.servicos import agenda

GRADE = {"tiktok": {"semana": ["12:00", "18:00"], "fimdesemana": ["10:00"]},
         "instagram": {"semana": ["09:00"], "fimdesemana": ["10:00"]}}
VIDEOS = [Path(f"gta6_{i:03d}.mp4") for i in range(1, 6)]
SEG = datetime(2026, 11, 16, 8, 0)  # segunda-feira 08:00


def test_plano_grade_pula_feitos_e_ocupados():
    hist = {"gta6_001.mp4": {"tiktok": {"status": "publicado"}},
            "gta6_002.mp4": {"tiktok": {"status": "agendado", "para": "2026-11-16T12:00"}}}
    p = agenda.montar_plano(VIDEOS, hist, ["tiktok"], agora=SEG, g=GRADE)
    assert [x["video"].name for x in p][:2] == ["gta6_003.mp4", "gta6_004.mp4"]
    assert p[0]["quando"] == datetime(2026, 11, 16, 18, 0)  # 12:00 já ocupado pelo 002


def test_lote_por_hora_minutos_multiplos_de_5():
    p = agenda.montar_plano(VIDEOS, {}, ["tiktok"], agora=SEG, por_hora=3, ate="10:00")
    assert all(x["quando"].minute % 5 == 0 for x in p)
    assert all(x["quando"] < datetime(2026, 11, 16, 10, 0) for x in p)
    assert len(p) == 4  # a partir de 08:30 até 10:00 (exclusivo): 08:40 09:00 09:20 09:40


def test_agendado_pc_vencido_volta_a_pendente():
    info = {"status": "agendado_pc", "para": "2026-11-16T06:00"}
    assert not agenda.feito(info, agora=SEG)
    assert agenda.feito({"status": "agendado_pc", "para": "2026-11-16T07:30"}, agora=SEG)
