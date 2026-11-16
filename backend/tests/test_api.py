from fastapi.testclient import TestClient


def test_api_basico(banco):
    from app.api.main import create_app
    with TestClient(create_app()) as cli:
        assert cli.get("/api/contas").json()[0]["id"] == "gta6"
        assert cli.get("/api/sistema").status_code == 200
        plugins = cli.get("/api/plugins").json()
        assert {p["id"] for p in plugins["layouts"]} >= {"jogo_em_cima", "webcam_em_cima", "tela_cheia", "so_gameplay"}
        modelos = cli.get("/api/modelos").json()
        assert modelos[0]["params"]["divisao"] == 0.55
        r = cli.patch(f"/api/modelos/{modelos[0]['id']}", json={"params": {"legenda_y": 0.85}})
        assert r.json()["params"]["legenda_y"] == 0.85 and r.json()["params"]["divisao"] == 0.55
        assert cli.post("/api/modelos", json={"nome": "x", "layout": "nao_existe"}).status_code == 400
        r = cli.post("/api/streamers", json={"nome": "Speed", "plataforma": "youtube", "canal": "IShowSpeed",
                                             "idioma": "en"})
        assert r.status_code == 201 and r.json()["canal"] == "@IShowSpeed"
        r = cli.post("/api/contas", json={"id": "gamer_en", "nome": "Gamer", "idioma": "en"})
        assert r.status_code == 201
        assert cli.get("/api/contas/gamer_en/videos").json() == []
        assert cli.get("/api/contas/x/videos").status_code == 404
        assert cli.get("/api/contas/gta6/videos/..%2F..%2Fsegredo.mp4/arquivo").status_code == 404


def test_api_enquadramento_manual(banco):
    from app.api.main import create_app
    from app.cortes import servico
    st = servico.criar_streamer(nome="A", plataforma="twitch", canal="a")
    fid = servico.salvar_fontes(st.id, [{"url": "https://www.twitch.tv/videos/9", "tipo": "vod", "titulo": "v"}])[0]
    servico.substituir_candidatos(fid, [{"inicio": 0.0, "fim": 30.0, "score": 1, "sinais": {}}])
    cid = servico.listar_cortes(fonte_id=fid)[0]["id"]
    servico.atualizar_corte(cid, status="enquadrar", webcam={"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2,
                                                             "origem": "sugerida"})
    with TestClient(create_app()) as cli:
        assert cli.get(f"/api/cortes/{cid}/quadro").status_code == 404
        r = cli.patch(f"/api/cortes/{cid}", json={"webcam": {"x": 0.7, "y": 0.6, "w": 0.3, "h": 0.4}})
        c = r.json()
        assert c["webcam"]["origem"] == "manual" and c["status"] == "candidato"
        c = cli.patch(f"/api/cortes/{cid}", json={"sem_webcam": True}).json()
        assert c["webcam"] is None and c["extra"]["webcam"] == "nenhuma"
        c = cli.patch(f"/api/cortes/{cid}", json={"webcam": None}).json()   # "detectar de novo"
        assert "webcam" not in c["extra"]
        r = cli.post("/api/previa", json={"corte_id": cid, "params": {"legenda_y": 0.85}})
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
        assert cli.post("/api/previa", json={"layout": "nao_existe"}).status_code == 400


def test_api_fundos_e_aplicar(banco):
    from app.api.main import create_app
    from app.cortes import servico
    st = servico.criar_streamer(nome="B", plataforma="twitch", canal="b")
    fid = servico.salvar_fontes(st.id, [{"url": "https://www.twitch.tv/videos/7", "tipo": "vod", "titulo": "v"}])[0]
    servico.substituir_candidatos(fid, [{"inicio": 0.0, "fim": 30.0, "score": 1, "sinais": {}},
                                        {"inicio": 60.0, "fim": 90.0, "score": 1, "sinais": {}}])
    with TestClient(create_app()) as cli:
        assert cli.post("/api/fundos", content=b"abc", headers={"Content-Type": "text/plain"}).status_code == 415
        r = cli.post("/api/fundos", content=b"\x89PNG fake", headers={"Content-Type": "image/png"})
        nome = r.json()["nome"]
        assert r.status_code == 201 and nome.endswith(".png") and cli.get("/api/fundos").json()[0]["nome"] == nome
        assert cli.get("/api/fundos/..%2F..%2Fdados%2Fjason.db").status_code == 404
        r = cli.post(f"/api/fontes/{fid}/aplicar", json={"idioma_legenda": "pt", "fundo": nome})
        assert all(c["idioma_legenda"] == "pt" and c["fundo"] == nome for c in r.json())
        assert cli.post(f"/api/fontes/{fid}/aplicar", json={"fundo": "nao_existe.png"}).status_code == 400
        assert cli.get(f"/api/fontes/{fid}").json()["total_cortes"] == 2
