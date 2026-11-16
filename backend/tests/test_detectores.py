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
