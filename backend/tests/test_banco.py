import json

from app.jobs import fila
from app.servicos import contas, historico, importar


def test_conta_padrao_e_historico(banco):
    c = contas.obter()
    assert c.id == "gta6" and c.padrao
    historico.registrar("gta6", "gta6_001.mp4", "tiktok", {"status": "agendado", "para": "2026-11-16T12:00", "x": 1})
    h = historico.carregar_hist("gta6")
    assert h["gta6_001.mp4"]["tiktok"]["status"] == "agendado"
    assert h["gta6_001.mp4"]["tiktok"]["x"] == 1  # campos extras são preservados
    historico.registrar("gta6", "gta6_001.mp4", "tiktok", {"status": "publicado", "link": "https://t"})
    assert historico.status_de("gta6", "gta6_001.mp4", "tiktok") == "publicado"
    assert "para" not in historico.carregar_hist("gta6")["gta6_001.mp4"]["tiktok"]


def test_importar_postados_identico(banco, monkeypatch):
    antigo = {"a.mp4": {"tiktok": {"em": "2026-11-13T03:10:00", "status": "publicado", "reivindicado": True},
                        "instagram": {"em": "2026-11-13T03:38:32", "status": "agendado_pc",
                                      "para": "2026-11-13T19:00", "tarefa": "instagram_a"}}}
    arq = banco / "postados.json"
    arq.write_text(json.dumps(antigo), "utf-8")
    monkeypatch.setattr(importar, "POSTADOS", arq)
    assert importar.importar_postados() == 2
    assert historico.carregar_hist("gta6") == antigo
    assert not arq.exists() and (banco / "postados.importado.json").exists()


def test_conta_nova_tem_pasta_e_trava_propria(banco):
    c = contas.criar("gamer_en", "Gamer EN", idioma="en")
    assert contas.pasta_videos(c).exists()
    assert contas.arquivo_trava(c).name == "perfil-gamer_en.lock"
    assert "#clips" in c.tags


def test_fila_de_jobs_recurso_e_cancelamento(banco):
    from app.jobs import jobs_postagem  # noqa: F401  registra os tipos
    j1 = fila.enfileirar("baixar_pack", {"qtd": 1})
    j2 = fila.enfileirar("baixar_pack", {"qtd": 2})
    a = fila.reivindicar(set(), pid=1)
    assert a.id == j1.id and a.recurso == "rede:pack"
    assert fila.reivindicar({"rede:pack"}, pid=1) is None  # mesmo recurso espera
    assert fila.cancelar(j2.id).status == "cancelado"
    assert fila.cancelar(j1.id).status == "cancelando"
    assert fila.Contexto(j1.id).cancelado
