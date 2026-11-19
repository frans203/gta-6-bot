import numpy as np

from app.cortes import detectores


def test_suavizar_mantem_tamanho_e_borda():
    x = np.ones(100)
    y = detectores._suavizar(x, 9)
    assert len(y) == 100
    assert np.allclose(y, 1.0)  # borda não cai (antes virava pico falso no início/fim)


def test_escolher_picos_sem_sobreposicao():
    score = np.zeros(1000)
    score[100], score[130], score[600] = 1.0, 0.9, 0.8
    picos = detectores.escolher_picos(score, {"audio": score}, n=5, duracao=40)
    inicios = sorted(p["inicio"] for p in picos)
    assert all(b - a >= 40 for a, b in zip(inicios, inicios[1:]))
    assert all(p["fim"] - p["inicio"] == 40 for p in picos)
    assert picos[0]["sinais"]["pico"] in (99, 100, 101)


def test_combinar_pesos():
    a, b = np.array([1.0, 0.0]), np.array([0.0, 1.0])
    r = detectores.combinar({"a": a, "b": b}, {"a": 3.0, "b": 1.0})
    assert r[0] == 0.75 and r[1] == 0.25


# ------------------------------------------------------------------ trecho escolhido

def test_escolher_picos_respeita_o_trecho():
    score = np.zeros(10_000)
    score[500], score[5000] = 1.0, 0.6
    picos = detectores.escolher_picos(score, {"audio": score}, n=3, duracao=45, faixa=(4000, 6000))
    assert len(picos) == 1 and 4000 <= picos[0]["inicio"] and picos[0]["fim"] <= 6000
    # pico colado na borda do trecho: o corte não sai dele
    score[4005] = 2.0
    p = detectores.escolher_picos(score, {"audio": score}, n=1, duracao=45, faixa=(4000, 6000))[0]
    assert p["inicio"] >= 4000


def test_mascarar_zera_fora_e_renormaliza():
    x = np.zeros(100)
    x[10], x[50] = 1.0, 0.5
    m = detectores.mascarar(x, (40, 60))
    assert m[10] == 0 and m[50] == 1.0


def test_trecho_da_analise():
    from types import SimpleNamespace

    from app.cortes.jobs import trecho_da_analise
    f = SimpleNamespace(extra={"trecho": {"inicio": 100, "fim": 900}})
    assert trecho_da_analise({"inicio": 3600, "fim": 7200}, f, 50_000) == (3600, 7200)
    assert trecho_da_analise({}, f, 50_000) == (100, 900)          # o último usado nesta fonte
    assert trecho_da_analise({}, SimpleNamespace(extra={}), 500) == (0, 500)
    assert trecho_da_analise({"inicio": 10, "fim": 20}, f, 500) == (0, 500)  # trecho curto demais: vídeo todo


# ------------------------------------------------------------------ fala

SEGS = [
    {"texto": "então pessoal vamos ver aqui o mapa", "i": 1000.0, "f": 1004.0},
    {"texto": "beleza", "i": 1010.0, "f": 1011.0},
    {"texto": "NÃO NÃO NÃO caralho meu deus!", "i": 1015.0, "f": 1016.5},
    {"texto": "kkkkkkkk que isso mano", "i": 1017.0, "f": 1019.0},
    {"texto": "bom continuando", "i": 1040.0, "f": 1042.0},
]


def test_nota_texto_gatilho_e_risada():
    from app.cortes import fala
    g, r = fala.nota_texto("NÃO NÃO NÃO caralho meu deus!", "pt")
    assert g >= 3 and r == 0
    g, r = fala.nota_texto("kkkkkk hahaha", "pt")
    assert r >= 2
    assert fala.nota_texto("bom continuando", "pt") == (0.0, 0.0)


def test_curvas_da_fala_apontam_o_grito():
    from app.cortes import fala
    cs = fala.curvas(SEGS, 2000, (900, 1100), "pt")
    assert set(cs) >= {"fala", "fala_ritmo", "fala_explosao", "fala_gatilho", "fala_risada"}
    assert 1013 <= int(np.argmax(cs["fala"])) <= 1021
    assert cs["fala"][:900].sum() == 0 and cs["fala"][1100:].sum() == 0
    assert cs["fala_explosao"][1015] > 0  # 4 s de silêncio e depois o grito


def test_ajustar_as_frases():
    from app.cortes import fala
    frases = [(s["i"], s["f"]) for s in SEGS]
    ini, fim, ok = fala.ajustar_as_frases(1012.0, 1042.0, 1016, frases, 30, (0, 2000))
    assert ok and abs(ini - 1010.0) < 0.5 and abs(fim - 1042.3) < 0.5
    # nenhuma frase perto: fica como estava
    assert fala.ajustar_as_frases(500.0, 530.0, 515, frases, 30, (0, 2000)) == (500.0, 530.0, False)


def test_sugerir_gancho():
    from app.cortes import fala
    cs = fala.curvas(SEGS, 2000, (900, 1100), "pt")
    g = fala.sugerir_gancho(SEGS, 1005, 1035, cs["fala"], "pt")
    assert g and "caralho" in g.lower()


def test_escolher_picos_com_frases_marca_o_ajuste():
    from app.cortes import fala
    cs = fala.curvas(SEGS, 2000, (900, 1100), "pt")
    p = detectores.escolher_picos(cs["fala"], cs, n=1, duracao=30, faixa=(900, 1100),
                                  frases=[(s["i"], s["f"]) for s in SEGS])[0]
    assert p["sinais"].get("frase") == 1 and p["inicio"] <= 1015 <= p["fim"]


# ------------------------------------------------------------------ chat do YouTube

def _linha(ms, texto=None, emoji=None, pago=False):
    runs = []
    if texto:
        runs.append({"text": texto})
    if emoji:
        runs.append({"emoji": {"emojiId": emoji, "shortcuts": [":face-with-tears-of-joy:"]}})
    chave = "liveChatPaidMessageRenderer" if pago else "liveChatTextMessageRenderer"
    import json
    return json.dumps({"replayChatItemAction": {"videoOffsetTimeMsec": str(ms), "actions": [
        {"addChatItemAction": {"item": {chave: {"message": {"runs": runs}}}}}]}})


def test_chat_youtube_conta_e_puxa_o_atraso(tmp_path):
    from app.cortes import chat
    linhas = [_linha(s * 1000 + 100, "oi") for s in range(0, 600, 3)]          # chat normal
    linhas += [_linha(308_000 + k * 50, "KKKKKKK") for k in range(80)]          # explosão em ~308 s
    linhas += [_linha(309_000, emoji="😂"), _linha(310_000, "valeu", pago=True), "lixo que não é json"]
    arq = tmp_path / "x.live_chat.json"
    arq.write_text("\n".join(linhas), "utf-8")
    c = chat.contar(arq, 600)
    assert c["mensagens"].sum() == 200 + 80 + 2 and c["super"][310] == 1 and c["reacoes"][309] >= 1
    chat.salvar_cache(tmp_path / "c.npz", c)
    c2 = chat.ler_cache(tmp_path / "c.npz", 600)
    assert np.array_equal(c2["reacoes"], c["reacoes"])
    cs = chat.curvas(c2, (0, 600))
    pico = int(np.argmax(cs["chat"]))
    assert 296 <= pico <= 306  # o chat reage ~8 s depois: o pico volta para o momento


# ------------------------------------------------------------------ aprendizado

def test_aprendizado_reordena_pelo_que_foi_aprovado(banco):
    from app.cortes import aprendizado, servico
    st, _ = servico.streamer_por_canal("twitch", "fulano", "Fulano", "pt")
    fid = servico.salvar_fontes(st.id, [{"url": "https://twitch.tv/videos/1", "tipo": "vod", "titulo": "x"}])[0]
    rng = np.random.default_rng(1)
    # o usuário aprova o que tem fala forte e descarta o que só tem áudio alto
    for k in range(40):
        bom = k % 2 == 0
        sinais = {"audio": float(rng.uniform(0.3, 1)), "fala": float(rng.uniform(0.6, 1) if bom else rng.uniform(0, 0.3))}
        status = "pronto" if bom else "descartado"
        servico.criar_corte(fid, inicio=k * 100, fim=k * 100 + 30, sinais=sinais, status=status,
                            extra={"descartado_de": "candidato"} if not bom else {})
    # descarte depois de pronto (webcam etc.) não conta
    servico.criar_corte(fid, inicio=9000, fim=9030, sinais={"fala": 1.0}, status="descartado",
                        extra={"descartado_de": "pronto"})
    e = aprendizado.treinar()
    assert e["pronto"] and e["exemplos"] == 40 and e["pesos"]["fala"] > e["pesos"]["audio"]
    m = aprendizado.modelo_ativo()
    cands = [{"score": 1.0, "sinais": {"audio": 1.0, "fala": 0.1}}, {"score": 0.7, "sinais": {"audio": 0.5, "fala": 0.9}}]
    assert aprendizado.reordenar(cands, 1, m)[0]["sinais"]["fala"] == 0.9
    aprendizado.ligar(False)
    assert aprendizado.modelo_ativo() is None
    assert aprendizado.reordenar(cands, 1, None)[0]["score"] == 1.0


def test_aprendizado_sem_exemplos_nao_liga(banco):
    from app.cortes import aprendizado
    e = aprendizado.treinar()
    assert not e["pronto"] and aprendizado.modelo_ativo() is None
