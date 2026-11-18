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


def test_api_biblioteca(banco, tmp_path):
    """Biblioteca: vídeos com cortes a revisar, número do corte no vídeo e re-render ao mudar a webcam."""
    from app.api.main import create_app
    from app.cortes import servico
    st = servico.criar_streamer(nome="C", plataforma="twitch", canal="c")
    fid = servico.salvar_fontes(st.id, [{"url": "https://www.twitch.tv/videos/5", "tipo": "vod", "titulo": "live"}])[0]
    outra = servico.salvar_fontes(st.id, [{"url": "https://www.twitch.tv/videos/6", "tipo": "vod", "titulo": "x"}])[0]
    servico.substituir_candidatos(fid, [{"inicio": 120.0, "fim": 150.0, "score": 2, "sinais": {}},
                                        {"inicio": 10.0, "fim": 40.0, "score": 1, "sinais": {}}])
    servico.substituir_candidatos(outra, [{"inicio": 0.0, "fim": 30.0, "score": 1, "sinais": {}}])
    cortes = {c["inicio"]: c for c in servico.listar_cortes(fonte_id=fid)}
    cedo, tarde = cortes[10.0], cortes[120.0]
    assert (cedo["n_na_fonte"], tarde["n_na_fonte"]) == (1, 2)
    mp4 = tmp_path / "x.mp4"
    mp4.write_bytes(b"fake")
    servico.atualizar_corte(tarde["id"], status="pronto", arquivo=str(mp4))
    servico.atualizar_corte(servico.listar_cortes(fonte_id=outra)[0]["id"], status="descartado")
    with TestClient(create_app()) as cli:
        fontes = cli.get("/api/fontes", params={"com_cortes": ["candidato", "enquadrar"]}).json()
        assert [f["id"] for f in fontes] == [fid]
        assert fontes[0]["cortes_status"] == {"candidato": 1, "pronto": 1} and fontes[0]["streamer_nome"] == "C"
        assert cli.get(f"/api/fontes/{fid}").json()["total_cortes"] == 2
        assert cli.get(f"/api/cortes/{cedo['id']}/miniatura").status_code == 404   # ainda não renderizado
        # região nova num corte pronto: gera de novo sozinho
        c = cli.patch(f"/api/cortes/{tarde['id']}", json={"webcam": {"x": 0.7, "y": 0.6, "w": 0.3, "h": 0.4}}).json()
        assert c["status"] == "aprovado" and c["n_na_fonte"] == 2
        jobs = cli.get("/api/jobs", params={"tipo": "renderizar_corte"}).json()
        assert [j["params"]["corte_id"] for j in jobs] == [tarde["id"]]
        # num candidato, só salva
        assert cli.patch(f"/api/cortes/{cedo['id']}", json={"sem_webcam": True}).json()["status"] == "candidato"


def test_textos_por_rede_e_removido(banco, tmp_path):
    """Título/descrição/hashtags com personalização por rede; hashtags em lote; 'não postar nesta rede'."""
    from app.api.main import create_app
    from app.plataformas.comum import caminho_meta, ler_txt, textos_rede
    from app.servicos import agenda, contas, historico
    conta = contas.criar("teste_txt", "Teste", pasta=str(tmp_path))
    for n in ("a", "b"):
        (tmp_path / f"{n}.mp4").write_bytes(b"x")
    (tmp_path / "b.txt").write_text("Antigo\n\n#velha\n", "utf-8")
    with TestClient(create_app()) as cli:
        base = f"/api/contas/{conta.id}/videos"
        r = cli.put(f"{base}/a.mp4/textos", json={"titulo": "Olha isso", "descricao": "linha 1\nlinha 2",
                                                    "tags": "#gta6 #fyp",
                                                    "redes": {"instagram": {"legenda": "só no insta #reels"}}}).json()
        assert r["finais"]["tiktok"]["legenda"] == "Olha isso linha 1 linha 2 #gta6 #fyp"
        assert r["finais"]["instagram"]["legenda"] == "só no insta #reels"
        assert r["finais"]["youtube"] == {"titulo": "Olha isso #gta6 #shorts", "descricao": "linha 1 linha 2 #gta6 #fyp"}
        assert ler_txt(tmp_path / "a.mp4") == ("Olha isso", "#gta6 #fyp") and caminho_meta(tmp_path / "a.mp4").exists()
        # sem descrição nem personalização: não deixa .meta.json e o YouTube fica como antes
        cli.put(f"{base}/a.mp4/textos", json={"titulo": "Só título", "tags": "#x"})
        assert not caminho_meta(tmp_path / "a.mp4").exists()
        assert textos_rede(tmp_path / "a.mp4", "youtube") == {"titulo": "Só título #shorts", "descricao": "Só título #x"}
        v = {x["video"]: x for x in cli.get(base).json()}
        assert v["b.mp4"]["titulo"] == "Antigo" and v["b.mp4"]["descricao"] == ""
        # hashtags em lote: acrescenta sem repetir
        assert cli.post(f"{base}/hashtags", json={"tags": "#nova #x", "modo": "adicionar"}).json()["videos"] == 2
        assert ler_txt(tmp_path / "b.mp4")[1] == "#velha #nova #x" and ler_txt(tmp_path / "a.mp4")[1] == "#x #nova"
        # não postar nesta rede
        assert cli.put(f"{base}/b.mp4/redes/instagram", json={"status": "removido"}).json()["ok"]
        h = historico.carregar_hist(conta.id)
        assert h["b.mp4"]["instagram"]["status"] == "removido" and agenda.feito(h["b.mp4"]["instagram"])
        assert cli.get(base).json()[1]["plataformas"]["instagram"]["status"] == "removido"
        cli.put(f"{base}/b.mp4/redes/instagram", json={"status": "pendente"})
        assert "instagram" not in historico.carregar_hist(conta.id).get("b.mp4", {})
        assert cli.put(f"{base}/b.mp4/redes/orkut", json={"status": "removido"}).status_code == 404
