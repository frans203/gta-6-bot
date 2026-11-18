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


def test_sugestoes_por_rede_marcam_ocupado_destaque_e_antecedencia():
    g = {**GRADE, "_destaques": {"tiktok": ["18:00"]}}
    hist = {"gta6_002.mp4": {"tiktok": {"status": "agendado", "para": "2026-11-16T18:00"}}}
    s = agenda.sugestoes(hist, ["tiktok", "instagram"], dias=2, agora=datetime(2026, 11, 16, 11, 45), g=g)
    tk = {x["quando"]: x for x in s["tiktok"]}
    hoje12, hoje18 = datetime(2026, 11, 16, 12, 0), datetime(2026, 11, 16, 18, 0)
    assert tk[hoje12]["disponivel"] is False                    # a 15 min de agora: menos que a antecedência
    assert tk[hoje18]["destaque"] and tk[hoje18]["ocupado_por"] == "gta6_002.mp4"
    assert datetime(2026, 11, 17, 12, 0) in tk                  # amanhã também
    assert [x["quando"] for x in s["instagram"]] == [datetime(2026, 11, 17, 9, 0)]  # hoje 09:00 já passou


def test_validar_itens_de_um_video():
    agora = SEG
    ok = [{"plataforma": "tiktok", "quando": datetime(2026, 11, 16, 20, 30)},
          {"plataforma": "youtube", "quando": datetime(2026, 11, 17, 18, 0)}]
    assert agenda.validar_itens(ok, {}, agora) == []
    ruins = [{"plataforma": "tiktok", "quando": datetime(2026, 11, 16, 8, 10)},       # perto demais
             {"plataforma": "youtube", "quando": datetime(2026, 11, 16, 20, 33)},     # minuto quebrado
             {"plataforma": "instagram", "quando": datetime(2026, 11, 16, 21, 0)}]    # já publicado
    erros = agenda.validar_itens(ruins, {"instagram": {"status": "publicado"}}, agora)
    assert len(erros) == 3 and any("instagram" in e for e in erros)
