"""YouTube Studio (Shorts) — fluxo mapeado em 13/11/2026 (inclui agendamento nativo)."""
import random
import re
from datetime import datetime
from pathlib import Path

from .agenda import data_yt
from .comum import NaoLogado, log, passo, textos

NOME = "youtube"
LOGIN_URL = "https://studio.youtube.com"
STUDIO_URL = "https://studio.youtube.com"
AGENDA_NATIVA = True
ETAPAS = 6

# Usuario confirmou em 13/11/2026: os videos NAO sao conteudo para criancas.
FEITO_PARA_CRIANCAS = False
# Usuario decidiu em 13/11/2026: publicar mesmo com reivindicacao de Content ID.
PUBLICAR_COM_REIVINDICACAO = True


def _digitar(page, campo, texto):
    campo.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.type(texto, delay=random.randint(20, 45))
    page.wait_for_timeout(600)
    page.keyboard.press("Escape")  # fecha sugestoes de hashtag


def _agendar(page, dlg, quando: datetime):
    dlg.locator("#second-container-expand-button").click()
    page.wait_for_timeout(800)
    dlg.locator("#datepicker-trigger").click()
    campo_data = page.locator("ytcp-date-picker input").first
    campo_data.wait_for(state="visible", timeout=10_000)
    campo_data.click()
    page.keyboard.press("Control+A")
    page.keyboard.type(data_yt(quando))
    page.keyboard.press("Enter")
    page.wait_for_timeout(600)

    hora = dlg.locator("#time-of-day-container input")
    hora.focus()
    hora.select_text()
    page.keyboard.type(f"{quando:%H:%M}")
    page.keyboard.press("Enter")
    page.wait_for_timeout(600)

    cont = dlg.locator("#second-container")
    if "posterior" in cont.inner_text() or hora.input_value() != f"{quando:%H:%M}":
        raise RuntimeError(f"YouTube nao aceitou o horario {quando:%d/%m %H:%M}")


def postar(page, video: Path, revisar=False, quando: datetime | None = None, progresso=None) -> dict:
    titulo, tags = textos(video)
    passo(progresso, "abrindo YouTube Studio")
    page.goto(STUDIO_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=60_000)
    if "accounts.google.com" in page.url:
        raise NaoLogado("YouTube/Google nao esta logado no perfil do script")

    dlg = page.locator("ytcp-uploads-dialog")
    entrada = dlg.locator("input[type=file][name=Filedata]")
    if not entrada.count():
        botao = page.locator("#upload-icon")
        if botao.count() and botao.first.is_visible():
            botao.first.click()
        else:
            page.locator("#create-icon").click()
            page.locator("#text-item-0").click()
    entrada.wait_for(state="attached", timeout=30_000)

    passo(progresso, "enviando video")
    entrada.set_input_files(str(video))
    caixas = dlg.locator("#textbox")
    caixas.first.wait_for(timeout=120_000)
    page.wait_for_timeout(1500)

    passo(progresso, "titulo e descricao")
    titulo_yt = f"{titulo} #gta6 #shorts"
    _digitar(page, caixas.nth(0), titulo_yt if len(titulo_yt) <= 100 else titulo[:100])
    _digitar(page, caixas.nth(1), f"{titulo} {tags}")

    kids = "VIDEO_MADE_FOR_KIDS_MFK" if FEITO_PARA_CRIANCAS else "VIDEO_MADE_FOR_KIDS_NOT_MFK"
    radio = dlg.locator(f"tp-yt-paper-radio-button[name={kids}]")
    radio.scroll_into_view_if_needed()
    radio.click()

    passo(progresso, "avancando etapas")
    for _ in range(3):
        dlg.locator("#next-button").click()
        page.wait_for_timeout(1200)

    passo(progresso, "aguardando upload/verificacoes")
    rodape = dlg.locator("ytcp-video-upload-progress")
    page.wait_for_function(
        "el => !/Enviando|Uploading|%/.test(el.innerText)", arg=rodape.element_handle(), timeout=20 * 60_000
    )
    status_txt = rodape.inner_text().strip()
    reivindicado = bool(re.search(r"reivindicado|claimed", status_txt, re.I))
    log(f"rodape: {status_txt}", NOME)
    if reivindicado and not PUBLICAR_COM_REIVINDICACAO:
        dlg.locator("#done-button").click()
        return {"status": "pulado_reivindicacao", "obs": status_txt}

    if quando:
        passo(progresso, f"agendando {quando:%d/%m %H:%M}")
        _agendar(page, dlg, quando)
    else:
        passo(progresso, "visibilidade: publico")
        dlg.locator("tp-yt-paper-radio-button[name=PUBLIC]").click()

    if revisar:
        return {"status": "revisar", "obs": status_txt}

    dlg.locator("#done-button").click()
    share = page.locator("ytcp-video-share-dialog")
    share.wait_for(state="visible", timeout=120_000)
    link = re.search(r"https://(?:www\.)?youtube\.com/shorts/[\w-]+|https://youtu\.be/[\w-]+", share.inner_text())
    fechar = share.get_by_role("button", name=re.compile("Fechar|Close"))
    if fechar.count():
        fechar.first.click()
    r = {"link": link.group(0) if link else None, "reivindicado": reivindicado}
    if quando:
        return {"status": "agendado", "para": quando.isoformat(timespec="minutes"), **r}
    return {"status": "publicado", **r}
