import pytest

from app.cortes import layouts, legendas, servico
from app.cortes.plugins import carregar

carregar()


CAM = {"x": 0.01, "y": 0.02, "w": 0.27, "h": 0.27}


def test_layouts_dimensoes_pares_e_divisao():
    import re
    for fn in (layouts.webcam_em_cima, layouts.jogo_em_cima):
        m = fn(1920, 1080, CAM, {"x": 0.2, "y": 0, "w": 0.6, "h": 1}, {"divisao": 0.5})
        assert "vstack" in m.filtro and m.filtro.endswith("[base]")
        for w, h in re.findall(r"crop=(\d+):(\d+)", m.filtro):
            assert int(w) % 2 == 0 and int(h) % 2 == 0
    m = layouts.jogo_em_cima(1920, 1080, CAM, None, {"divisao": 0.5})
    assert m.legenda_y == 960 and "crop=1080:960[jogo]" in m.filtro and "crop=1080:960[cam]" in m.filtro


def test_layout_sem_webcam_segue_sem_o_streamer():
    for fn in (layouts.jogo_em_cima, layouts.webcam_em_cima, layouts.fundo_imagem):
        m = fn(1920, 1080, None, None, {"divisao": 0.5})
        assert m.sem_webcam and "cam" not in m.filtro and m.filtro.endswith("[base]")
    from app.cortes import render
    m = render.montar(1920, 1080, {"layout": "jogo_em_cima", "params": {"legenda_y": 0.55}}, None, None)
    assert m.legenda_y != int(1920 * 0.55)  # sem webcam, a posição do modelo não vale (legenda sob o vídeo)


def test_classificar_webcam():
    from app.cortes import webcam
    assert webcam.classificar(None) == "nenhuma"
    assert webcam.classificar({"confianca": 0.8, "amostras": 29}) == "auto"
    assert webcam.classificar({"confianca": 0.25, "amostras": 9}) == "duvida"
    assert webcam.classificar({"confianca": 0.06, "amostras": 2}) == "nenhuma"


def test_montar_aplica_posicoes_do_modelo():
    from app.cortes import render
    modelo = {"layout": "jogo_em_cima", "params": {"divisao": 0.55, "legenda_y": 0.85, "gancho_y": 0.1}}
    m = render.montar(1920, 1080, modelo, CAM, None)
    assert m.legenda_y == int(1920 * 0.85) and m.gancho_y == 192


def test_previa_gera_jpeg(tmp_path, monkeypatch):
    import shutil
    if not shutil.which("ffmpeg"):
        pytest.skip("sem ffmpeg")
    from app.config import config
    from app.cortes import render
    monkeypatch.setattr(config, "midia", tmp_path)
    jpg = render.previa({"layout": "jogo_em_cima", "estilo_legenda": "destaque", "params": {"legenda_y": 0.5}},
                        None, None, None, gancho="TESTE")
    assert jpg[:2] == bytes([0xFF, 0xD8])


def test_blocos_e_ass():
    p = [{"p": "olha", "i": 0.0, "f": 0.3}, {"p": "isso", "i": 0.35, "f": 0.6}, {"p": "mano!", "i": 0.65, "f": 0.9},
         {"p": "depois", "i": 3.0, "f": 3.4}]
    b = legendas.blocos(p, 3)
    assert [len(x) for x in b] == [3, 1]
    ass = legendas.gerar_ass(p, "destaque", 700, 90, 5.0, gancho="ELE {NÃO} SABIA", credito="twitch.tv/x")
    assert ass.count("Dialogue:") == 4 + 2
    assert "OLHA" in ass and "{NÃO}" not in ass  # chaves escapadas (senão viram comando do .ass)


def test_normalizar_canal():
    assert servico.normalizar_canal("twitch", "https://www.twitch.tv/Alanzoka/") == "alanzoka"
    assert servico.normalizar_canal("youtube", "https://www.youtube.com/@IShowSpeed/streams") == "@IShowSpeed"
    assert servico.normalizar_canal("youtube", "IShowSpeed") == "@IShowSpeed"


def test_streamer_fonte_corte(banco):
    st = servico.criar_streamer(nome="Kai Cenat", plataforma="twitch", canal="kaicenat", idioma="en")
    fid = servico.salvar_fontes(st.id, [{"url": "https://www.twitch.tv/videos/1", "tipo": "vod", "titulo": "live"}])[0]
    servico.substituir_candidatos(fid, [{"inicio": 10.0, "fim": 55.0, "score": 0.9, "sinais": {}}])
    c = servico.listar_cortes(fonte_id=fid)[0]
    assert c["streamer_nome"] == "Kai Cenat" and c["status"] == "candidato"
    servico.atualizar_corte(c["id"], status="descartado")
    servico.substituir_candidatos(fid, [])  # nova análise não apaga o que já foi revisado
    assert servico.listar_cortes(fonte_id=fid)[0]["status"] == "descartado"


def test_modelos(banco):
    ms = servico.listar_modelos()
    assert ms[0]["padrao"] and ms[0]["layout"] == "jogo_em_cima"   # semente da migração 0002
    novo = servico.criar_modelo(nome="Teste", layout="tela_cheia", estilo_legenda="classico",
                                params={"legenda_y": 0.8}, padrao=True)
    assert servico.obter_modelo()["id"] == novo["id"]               # só um padrão
    assert sum(m["padrao"] for m in servico.listar_modelos()) == 1
    st = servico.criar_streamer(nome="X", plataforma="twitch", canal="x", modelo_id=novo["id"])
    with pytest.raises(ValueError):
        servico.remover_modelo(novo["id"])                          # é o padrão
    servico.atualizar_modelo(ms[0]["id"], {"padrao": True})
    servico.remover_modelo(novo["id"])
    assert servico.obter_streamer(st.id).modelo_id is None


def test_layout_fundo_imagem(tmp_path):
    from app.cortes import layouts as L
    img = tmp_path / "f.jpg"
    img.write_bytes(b"x")
    m = L.fundo_imagem(1920, 1080, CAM, {"x": 0.125, "y": 0, "w": 0.75, "h": 1}, {"fundo_arquivo": str(img)})
    assert m.entradas == [str(img)] and "[1:v]" in m.filtro and m.filtro.endswith("[base]")
    sem = L.fundo_imagem(1920, 1080, CAM, None, {})
    assert sem.entradas == [] and "boxblur" in sem.filtro       # sem imagem: vídeo desfocado de fundo
    assert sem.legenda_y < int(1920 * 0.62)                    # legenda entre o vídeo e a webcam


def test_previa_com_fundo(tmp_path, monkeypatch):
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        pytest.skip("sem ffmpeg")
    from app.config import config
    from app.cortes import render
    monkeypatch.setattr(config, "midia", tmp_path)
    (tmp_path / "fundos").mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=purple:s=640x480", "-frames:v", "1",
                    str(tmp_path / "fundos" / "f.png")], check=True)
    jpg = render.previa({"layout": "fundo_imagem", "estilo_legenda": "destaque", "params": {}}, None, CAM, None,
                        fundo="f.png")
    assert jpg[:2] == bytes([0xFF, 0xD8])


def test_traduzir_palavras_reparte_o_tempo(monkeypatch):
    from app.cortes import traducao
    monkeypatch.setattr(traducao, "traduzir", lambda textos, de, para: ["olha só isso", ""])
    p = traducao.traduzir_palavras([{"texto": "look at this", "i": 1.0, "f": 2.0},
                                    {"texto": "hm", "i": 3.0, "f": 3.2}], "en", "pt")
    assert [w["p"] for w in p] == ["olha", "só", "isso"]
    assert p[0]["i"] == 1.0 and p[-1]["f"] <= 2.0 and all(a["f"] <= b["i"] for a, b in zip(p, p[1:]))


def test_streamer_por_canal(banco):
    a, criado = servico.streamer_por_canal("kick", "Xqc", "xQc", "en")
    b, criado2 = servico.streamer_por_canal("kick", "xqc", "xQc")
    assert criado and not criado2 and a.id == b.id and a.idioma == "en"


def test_traducao_quebra_frases(monkeypatch):
    from app.cortes import traducao
    visto = []
    monkeypatch.setattr(traducao, "traduzir", lambda t, de, para: visto.extend(t) or ["a b" for _ in t])
    p = traducao.traduzir_palavras([{"texto": "What is wrong? What's wrong with bro?", "i": 0.0, "f": 4.0}], "en", "pt")
    assert visto == ["What is wrong?", "What's wrong with bro?"] and len(p) == 4 and p[-1]["f"] <= 4.0


def test_sugerir_pela_mesma_live(banco):
    from app.cortes import jobs
    st = servico.criar_streamer(nome="C", plataforma="twitch", canal="c")
    fid = servico.salvar_fontes(st.id, [{"url": "https://www.twitch.tv/videos/5", "tipo": "vod", "titulo": "v"}])[0]
    servico.substituir_candidatos(fid, [{"inicio": float(i * 60), "fim": float(i * 60 + 30), "score": 1, "sinais": {}}
                                        for i in range(3)])
    a, b, c = sorted(servico.listar_cortes(fonte_id=fid), key=lambda x: x["inicio"])
    cam = {"x": 0.0, "y": 0.37, "w": 0.24, "h": 0.24, "origem": "auto", "confianca": 0.8}
    servico.atualizar_corte(a["id"], webcam=cam)
    servico.atualizar_corte(b["id"], extra={"webcam": "nenhuma"})
    servico.atualizar_corte(c["id"], status="enquadrar", webcam={"x": 0.3, "y": 0.3, "w": 0.5, "h": 0.5,
                                                                 "origem": "sugerida"})
    assert jobs._sugerir_pela_mesma_live(fid, print) == 1
    for x in (b, c):
        y = servico.obter_corte(x["id"])
        assert y["status"] == "enquadrar" and y["webcam"]["x"] == 0.0 and "webcam" not in y["extra"]


def test_fonte_por_url(banco):
    st = servico.criar_streamer(nome="D", plataforma="youtube", canal="@d")
    fid = servico.salvar_fontes(st.id, [{"url": "https://www.youtube.com/watch?v=abc", "tipo": "vod", "titulo": "v"}])[0]
    assert servico.fonte_por_url("https://www.youtube.com/watch?v=abc ").id == fid
    assert servico.fonte_por_url("https://www.youtube.com/watch?v=zzz") is None


def test_jogo_desvia_da_webcam():
    cam = {"x": 0.0, "y": 0.38, "w": 0.29, "h": 0.28}
    j = layouts._jogo_sem_a_webcam(None, cam, 1920, 1080, 1080, 1056)
    assert j["x"] >= 0.29 - 1e-6 and j["x"] + j["w"] <= 1.0001     # começa depois da webcam
    assert layouts._jogo_sem_a_webcam({"x": 0.1, "y": 0, "w": 0.5, "h": 1}, cam, 1920, 1080, 1080, 1056)["x"] == 0.1
    assert layouts._jogo_sem_a_webcam(None, {"x": 0.45, "y": 0.0, "w": 0.1, "h": 0.1}, 1920, 1080, 1080, 1056)         is not None  # no meio, mas invadindo: desvia também
