"""Editor de vídeo: linha do tempo, layout livre (rodando o ffmpeg de verdade) e API."""
import subprocess

from fastapi.testclient import TestClient

from app.cortes import edicao as ed
from app.cortes import legendas, midia
from app.cortes.layouts import A

ZONAS = {"jogo": {"saida": {"x": 0, "y": 0, "w": 1, "h": 0.55}},
         "webcam": {"saida": {"x": 0.1, "y": 0.6, "w": 0.8, "h": 0.35}}, "fundo": "preto"}


def _edicao(**extra):
    return {"segmentos": [{"i": 100.0, "f": 101.0}, {"i": 103.0, "f": 103.5}], "sincronizado": True,
            "atraso_streamer": 0.0, "legenda": {"fonte": "Impact", "tamanho": 80, "cor": "FF00FF", "destaque": "00FF00",
                                                 "contorno": 5, "maiusculas": False, "por_bloco": 2, "y": 0.7,
                                                 "mostrar": True},
            "gancho": {"fonte": "Arial", "tamanho": 50, "cor": "FFFFFF", "fundo": "FF3D9A", "y": 0.1},
            "layout": ZONAS, **extra}


def test_remapear_e_segmentos():
    segs = ed.segmentos_arquivo(_edicao(), base=95.0, duracao_arquivo=30)
    assert segs == [(5.0, 6.0), (8.0, 8.5)] and ed.duracao(segs) == 1.5
    palavras = [{"p": "a", "i": 5.2, "f": 5.5}, {"p": "cortada", "i": 7.0, "f": 7.4}, {"p": "b", "i": 8.1, "f": 9.0}]
    out = ed.remapear(palavras, segs)
    assert [(w["p"], w["i"], w["f"]) for w in out] == [("a", 0.2, 0.5), ("b", 1.1, 1.5)]
    # trecho fora do arquivo baixado é descartado; nenhum dentro = erro
    assert ed.segmentos_arquivo({"segmentos": [{"i": 0, "f": 2}, {"i": 96, "f": 97}]}, 95.0, 30) == [(1.0, 2.0)]
    try:
        ed.segmentos_arquivo({"segmentos": [{"i": 0, "f": 2}]}, 95.0, 30)
        raise AssertionError("devia falhar")
    except ValueError:
        pass


def test_ass_com_estilo_do_editor():
    e = _edicao()
    txt = legendas.gerar_ass([{"p": "oi", "i": 0, "f": 0.5}], "destaque", int(A * 0.7), int(A * 0.1), 2.0,
                             gancho="GANCHO", ajustes=e["legenda"], gancho_ajustes=e["gancho"])
    assert "Style: Legenda,Impact,80,&H00FF00FF&" in txt and "Style: Gancho,Arial,50,&H00FFFFFF&" in txt
    assert "{\\c&H0000FF00&" in txt and "\\pos(540,1344)" in txt
    sem = legendas.gerar_ass([{"p": "oi", "i": 0, "f": 0.5}], "destaque", 100, 100, 2.0,
                             ajustes={**e["legenda"], "mostrar": False})
    assert "Dialogue: 0" not in sem


def test_ffmpeg_trechos_e_layout_livre(tmp_path):
    """Monta um vídeo com 2 trechos, jogo + webcam + atraso, e confere a duração final."""
    fonte = tmp_path / "trecho.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:d=4:r=30", "-f", "lavfi",
                    "-i", "sine=f=440:d=4", "-shortest", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                    str(fonte)], check=True, creationflags=midia.SEM_JANELA)
    e = _edicao(sincronizado=False, atraso_streamer=0.4)
    segs = [(1.0, 2.0), (2.5, 3.0)]
    m = ed.montar_livre(640, 360, e, {"x": 0.7, "y": 0.6, "w": 0.3, "h": 0.4}, None, None)
    assert m.legenda_y == int(A * 0.7) and not m.sem_webcam
    filtro = ed.filtro_segmentos(segs, True) + ";" + m.filtro.replace("[0:v]", "[vc]")
    saida = tmp_path / "saida.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(fonte), "-filter_complex", filtro, "-map", "[base]",
                    "-map", "[ac]", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-t", "1.5",
                    str(saida)], check=True, creationflags=midia.SEM_JANELA)
    info = midia.ffprobe(saida)
    assert (info["largura"], info["altura"]) == (1080, 1920) and abs(info["duracao"] - 1.5) < 0.15


def test_layout_do_modelo():
    modelo = {"layout": "jogo_em_cima", "params": {"divisao": 0.5}, "estilo_legenda": "destaque"}
    lay = ed.layout_do_modelo(modelo, 1920, 1080, {"x": 0.7, "y": 0.6, "w": 0.3, "h": 0.4}, None, False)
    assert lay["jogo"]["saida"] == {"x": 0, "y": 0, "w": 1, "h": 0.5} and lay["webcam"]["saida"]["y"] == 0.5
    sem = ed.layout_do_modelo(modelo, 1920, 1080, None, None, False)  # sem webcam: jogo inteiro no meio
    assert sem["webcam"] is None and 0.3 < sem["jogo"]["saida"]["h"] < 0.33
    so = ed.layout_do_modelo({"layout": "so_gameplay", "params": {}}, 1920, 1080, None, None, False)
    assert so["jogo"]["saida"]["h"] == 1


def test_api_editor(banco):
    from app.api.main import create_app
    from app.cortes import servico
    st = servico.criar_streamer(nome="E", plataforma="twitch", canal="e")
    fid = servico.salvar_fontes(st.id, [{"url": "https://www.twitch.tv/videos/3", "tipo": "vod", "titulo": "v"}])[0]
    servico.substituir_candidatos(fid, [{"inicio": 100.0, "fim": 130.0, "score": 1, "sinais": {}}])
    cid = servico.listar_cortes(fonte_id=fid)[0]["id"]
    with TestClient(create_app()) as cli:
        r = cli.get(f"/api/cortes/{cid}/editor").json()
        assert r["pronto"] is False and any(f["nome"] == "Arial Black" for f in r["fontes"])
        assert cli.get(f"/api/cortes/{cid}/bruto").status_code == 404
        e = _edicao()
        c = cli.patch(f"/api/cortes/{cid}", json={"edicao": e}).json()
        assert c["edicao"]["segmentos"][1] == {"i": 103.0, "f": 103.5} and c["edicao"]["legenda"]["fonte"] == "Impact"
        ruim = {**e, "segmentos": [{"i": 1, "f": 1.1}]}
        assert cli.patch(f"/api/cortes/{cid}", json={"edicao": ruim}).status_code == 400
        assert cli.patch(f"/api/cortes/{cid}", json={"edicao": {**e, "segmentos": []}}).status_code == 422
        r = cli.post("/api/previa", json={"corte_id": cid, "edicao": e})
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
        assert cli.patch(f"/api/cortes/{cid}", json={"edicao": None}).json()["edicao"] is None
        job = cli.post(f"/api/cortes/{cid}/editor/preparar").json()
        assert job["tipo"] == "preparar_editor"
        assert cli.post("/api/fontes-texto", params={"nome": "x.exe"}, content=b"1").status_code == 415
