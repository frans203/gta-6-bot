"""Roda o fluxo de cada rede numa página falsa (sem navegador) e confere o que o robô digitaria.
Pega erros bobos de código (ex.: digitar um objeto em vez do texto) antes de um envio de verdade."""
from app.plataformas import instagram, tiktok, youtube
from app.plataformas.comum import escrever_meta
from app.servicos import historico, postagem


class Falso:
    """Aceita qualquer chamada do Playwright e devolve a si mesmo; textos vazios e nada visível."""

    def __init__(self, url="https://www.instagram.com/", digitado=None):
        self.url = url
        self.digitado = digitado if digitado is not None else []

    def __getattr__(self, nome):
        return lambda *a, **k: self

    def __getitem__(self, i):
        return self

    @property
    def first(self):
        return self

    @property
    def last(self):
        return self

    @property
    def keyboard(self):
        return Teclado(self.digitado)

    def count(self):
        return 0

    def is_visible(self):
        return False

    def inner_text(self, *a, **k):
        return ""

    def input_value(self, *a, **k):
        return ""


class Teclado:
    def __init__(self, digitado):
        self.digitado = digitado

    def type(self, texto, **k):
        assert isinstance(texto, str), f"o robô ia digitar {type(texto).__name__}, não texto"
        self.digitado.append(texto)

    def press(self, *a, **k):
        pass


def _video(tmp_path):
    v = tmp_path / "corte_001.mp4"
    v.write_bytes(b"x")
    escrever_meta(v, {"titulo": "Olha isso", "descricao": "", "tags": "#alanzoka #fyp",
                      "redes": {"instagram": {"legenda": "texto do insta #reels"}}})
    return v


def test_instagram_digita_a_legenda(tmp_path, monkeypatch):
    monkeypatch.setattr(instagram, "LOGS", tmp_path)
    page = Falso()
    assert instagram.postar(page, _video(tmp_path))["status"] == "publicado"
    assert page.digitado[0] == "texto do insta #reels"


def test_tiktok_digita_a_legenda(tmp_path):
    page = Falso(url="https://www.tiktok.com/tiktokstudio/upload")
    assert tiktok.postar(page, _video(tmp_path))["status"] == "publicado"
    assert page.digitado == ["Olha isso #alanzoka #fyp "]


def test_youtube_digita_titulo_e_descricao(tmp_path):
    page = Falso(url="https://studio.youtube.com")
    assert youtube.postar(page, _video(tmp_path))["status"] == "publicado"
    assert page.digitado == ["Olha isso #shorts ", "Olha isso #alanzoka #fyp "]


def test_falha_vai_para_o_historico_sem_apagar_status_bom(banco, tmp_path):
    from types import SimpleNamespace
    conta = SimpleNamespace(id="gta6")
    v = tmp_path / "a.mp4"
    postagem._registrar_falha(conta, v, "tiktok", {"status": "erro", "erro": "timeout"})
    assert historico.status_de("gta6", v, "tiktok") == "erro"
    historico.registrar("gta6", v, "youtube", {"status": "agendado", "para": "2026-12-01T10:00"})
    postagem._registrar_falha(conta, v, "youtube", {"status": "erro", "erro": "timeout"})
    assert historico.status_de("gta6", v, "youtube") == "agendado"
