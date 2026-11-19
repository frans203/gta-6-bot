"""Vigia de clipes com a Helix simulada (sem rede)."""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

AGORA = datetime(2026, 11, 18, 22, 0, tzinfo=UTC)


def clipe(id, views, offset, dur=30.0, video="111", minutos_atras=60, titulo=None):
    return {"id": id, "url": f"https://clips.twitch.tv/{id}", "title": titulo or f"clipe {id}", "view_count": views,
            "duration": dur, "vod_offset": offset, "video_id": video, "creator_name": "fã",
            "created_at": (AGORA - timedelta(minutes=minutos_atras)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "thumbnail_url": "https://x/thumb.jpg"}


@pytest.fixture
def helix(monkeypatch):
    from app.cortes import fontes
    estado = {"clipes": [], "videos": {"111": 10_000}}
    monkeypatch.setattr(fontes.TwitchAPI, "disponivel", classmethod(lambda cls: True))
    monkeypatch.setattr(fontes.TwitchAPI, "clipes_entre", classmethod(lambda cls, login, i, f, limite=100: estado["clipes"]))
    monkeypatch.setattr(fontes.TwitchAPI, "video", classmethod(
        lambda cls, vid: {"id": vid, "titulo": "live de hoje", "duracao": estado["videos"][vid], "miniatura": None,
                          "criado_em": "2026-11-18T18:00:00Z", "url": None} if vid in estado["videos"] else None))
    return estado


def _streamer(**cfg):
    from app.cortes import servico, vigia
    st = servico.criar_streamer(nome="alanzoka", plataforma="twitch", canal="alanzoka")
    vigia.configurar(st.id, {"ativo": True, **cfg})
    return st.id


def test_ciclo_cria_corte_com_contexto_e_junta_mesmo_momento(banco, helix):
    from app.cortes import servico, vigia
    sid = _streamer(min_views=30, antes=20, depois=10)
    helix["clipes"] = [clipe("a", 500, 1000), clipe("b", 80, 1010),          # mesmo momento -> 1 corte
                       clipe("c", 10, 3000),                                   # poucas views: em observação
                       clipe("d", 300, 5000, dur=200)]                         # longo demais: ignorado
    fila = []
    r = vigia.ciclo(sid, agora=AGORA, log=lambda m: None, enfileirar=lambda *a: fila.append(a))
    assert r["novos"] == 1 and r["aguardando"] == 0
    c = servico.obter_corte(r["cortes"][0])
    assert (c["inicio"], c["fim"]) == (980.0, 1050.0)          # 1000-20 .. 1040+10
    assert c["fonte_url"] == "https://www.twitch.tv/videos/111" and c["extra"]["origem"] == "vigia"
    assert {x["id"] for x in c["extra"]["clipes"]} == {"a", "b"} and c["sinais"]["views"] == 580
    assert fila and fila[0][0] == "enquadrar_corte"
    res = vigia.resumo(servico.obter_streamer(sid))
    assert [x["situacao"] for x in res["recentes"]] == ["ignorado", "corte"] and res["hoje"] == 1
    # outra olhada: nada de novo; o "c" passou do mínimo e vira corte; um clipe novo do mesmo momento não duplica
    helix["clipes"] = [clipe("a", 600, 1000), clipe("c", 40, 3000), clipe("e", 90, 1020)]
    r2 = vigia.ciclo(sid, agora=AGORA, log=lambda m: None)
    assert r2["novos"] == 1
    recentes = {x["id"]: x for x in vigia.resumo(servico.obter_streamer(sid))["recentes"]}
    assert recentes["c"]["situacao"] == "corte"
    assert recentes["e"]["situacao"] == "ignorado" and "mesmo momento do corte" in recentes["e"]["motivo"]


def test_espera_a_live_e_o_vod(banco, helix):
    from app.cortes import servico, vigia
    sid = _streamer(min_views=1, antes=20, depois=30)
    helix["videos"]["111"] = 1050          # a live ainda não gravou 1030+30+folga
    helix["clipes"] = [clipe("a", 50, 1000)]
    r = vigia.ciclo(sid, agora=AGORA, log=lambda m: None)
    assert r["novos"] == 0 and r["aguardando"] == 1
    assert "live ainda não chegou" in vigia.resumo(servico.obter_streamer(sid))["aguardando"][0]["motivo"]
    helix["videos"]["111"] = 2000          # a live andou
    assert vigia.ciclo(sid, agora=AGORA, log=lambda m: None)["novos"] == 1
    # clipe recente sem vod_offset: espera; depois de 30 min sem VOD usa o próprio clipe
    helix["clipes"] = [clipe("x", 50, None, minutos_atras=5, video="999")]
    assert vigia.ciclo(sid, agora=AGORA, log=lambda m: None)["aguardando"] == 1
    helix["clipes"] = [clipe("x", 50, None, minutos_atras=40, video="999")]
    r = vigia.ciclo(sid, agora=AGORA, log=lambda m: None)
    c = servico.obter_corte(r["cortes"][0])
    assert c["fonte_tipo"] == "clipe" and (c["inicio"], c["fim"]) == (0.0, 30.0)


def test_limite_por_dia_e_agendamento(banco, helix):
    from app.cortes import servico, vigia
    sid = _streamer(min_views=1, max_por_dia=1)
    helix["clipes"] = [clipe("a", 50, 1000), clipe("b", 40, 4000)]
    r = vigia.ciclo(sid, agora=AGORA, log=lambda m: None)
    assert r["novos"] == 1 and r["aguardando"] == 1
    # o worker enfileira quando a hora chega (e não repete quem já está na fila)
    vigia.salvar(sid, estado={**vigia.estado_de(servico.obter_streamer(sid)), "proxima": "2000-01-01T00:00:00"})
    fila = []
    from app.jobs.fila import enfileirar
    assert vigia.agendar(lambda *a: (fila.append(a), enfileirar(*a))) == [sid]
    assert vigia.agendar(lambda *a: fila.append(a)) == []      # já tem um na fila


def test_api_vigia(banco, helix):
    from app.api.main import create_app
    from app.cortes import servico
    st = servico.criar_streamer(nome="Kai", plataforma="twitch", canal="kaicenat")
    yt = servico.criar_streamer(nome="Speed", plataforma="youtube", canal="IShowSpeed")
    with TestClient(create_app()) as cli:
        r = cli.put(f"/api/streamers/{st.id}/vigia", json={"ativo": True, "min_views": 50, "antes": 15}).json()
        assert r["config"]["ativo"] and r["config"]["antes"] == 15 and r["proxima"]
        assert cli.put(f"/api/streamers/{yt.id}/vigia", json={"ativo": True}).status_code == 400
        assert cli.put(f"/api/streamers/{st.id}/vigia", json={"dur_min": 50, "dur_max": 10}).status_code == 400
        assert cli.post(f"/api/streamers/{st.id}/vigia/agora").json()["tipo"] == "vigiar_clipes"
        painel = cli.get("/api/vigia").json()
        assert [p["nome"] for p in painel] == ["Kai"] and painel[0]["config"]["min_views"] == 50


def test_vod_so_para_inscritos_vira_o_clipe(banco, helix):
    from app.cortes import servico, vigia
    sid = _streamer(min_views=10)
    helix["clipes"] = [clipe("a", 100, offset=3000)]
    cid = vigia.ciclo(sid, agora=AGORA, log=lambda m: None)["cortes"][0]
    c = servico.obter_corte(cid)
    assert c["fonte_tipo"] == "vod"
    assert vigia.usar_clipe_se_vod_fechado(c, Exception("outro erro")) is None
    erro = Exception("[twitch:vod] 1: You must be logged into an account that has access to this subscriber-only content")
    novo = vigia.usar_clipe_se_vod_fechado(c, erro, log=lambda m: None)
    assert novo["fonte_tipo"] == "clipe" and novo["fonte_url"] == "https://clips.twitch.tv/a"
    assert (novo["inicio"], novo["fim"]) == (0.0, 30.0) and novo["extra"]["contexto"]["fonte"] == "clipe"
    # o próximo clipe já nasce do clipe, sem esperar o VOD
    helix["clipes"] = [clipe("b", 100, offset=6000, minutos_atras=5)]
    cid2 = vigia.ciclo(sid, agora=AGORA, log=lambda m: None)["cortes"][0]
    assert servico.obter_corte(cid2)["fonte_tipo"] == "clipe"


def test_ciclo_que_falha_espera_o_intervalo(banco, helix):
    from app.cortes import servico, vigia
    sid = _streamer(intervalo_min=5)
    vigia.salvar(sid, estado={**vigia.estado_de(servico.obter_streamer(sid)), "proxima": "2000-01-01T00:00:00"})
    vigia.adiar(sid)
    assert vigia.agendar(lambda *a: None) == []  # sem internet: não fica tentando a cada 30 s


def test_adicionar_canal_ao_vigia(banco, helix, monkeypatch):
    from app.api.main import create_app
    from app.cortes import fontes, servico

    def get(cls, caminho, **p):
        if caminho == "users":
            return {"data": [{"id": "9", "display_name": "Cellbit"}] if p["login"] == "cellbit" else []}
        return {"data": [{"broadcaster_language": "pt"}]}
    monkeypatch.setattr(fontes.TwitchAPI, "get", classmethod(get))
    with TestClient(create_app()) as cli:
        r = cli.post("/api/vigia", json={"canal": "https://www.twitch.tv/Cellbit/"})
        assert r.status_code == 201, r.text
        r = r.json()
        assert r["nome"] == "Cellbit" and r["canal"] == "cellbit" and r["config"]["ativo"] and r["proxima"]
        # de novo: não duplica, só mantém ligado
        assert cli.post("/api/vigia", json={"canal": "cellbit", "config": {"min_views": 80}}).json()["config"]["min_views"] == 80
        assert len(servico.listar_streamers()) == 1
        assert cli.post("/api/vigia", json={"canal": "naoexiste"}).status_code == 400
