"""TikTok Studio — fluxo mapeado em 13/11/2026 (inclui agendamento nativo)."""
import random
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout

from .comum import NaoLogado, log, passo, textos

NOME = "tiktok"
LOGIN_URL = "https://www.tiktok.com/login"
UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"
AGENDA_NATIVA = True
ETAPAS = 5
MESES_TT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
            "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _fechar_popups(page):
    """Fecha os avisos do TikTok Studio sem ativar nada."""
    for _ in range(3):
        fechou = False
        cancelar = page.locator("div:has-text('Ativar verificações automáticas') >> button:has-text('Cancelar')")
        if cancelar.count() and cancelar.first.is_visible():
            cancelar.first.click(); fechou = True
        entendi = page.get_by_role("button", name="Entendi")
        if entendi.count() and entendi.first.is_visible():
            entendi.first.click(); fechou = True
        if not fechou:
            return
        page.wait_for_timeout(500)


def _agendar(page, quando: datetime):
    """Quando publicar > Programar: aceita o aviso, escolhe hora (min. de 5 em 5) e dia."""
    if quando.minute % 5:
        raise ValueError("TikTok so aceita minutos multiplos de 5")
    cont = page.locator("[data-e2e=schedule_container]")
    cont.scroll_into_view_if_needed()
    page.locator("input[name=postSchedule][value=schedule]").check(force=True)

    permitir = page.get_by_role("button", name="Permitir")
    try:
        permitir.wait_for(timeout=4000)
        permitir.click()  # aviso obrigatorio do TikTok para agendar (usuario pediu posts agendados)
    except PWTimeout:
        pass

    campos = cont.locator("input.TUXTextInputCore-input")
    campos.first.wait_for(timeout=10_000)

    campos.nth(0).click()
    page.locator(".tiktok-timepicker-left").filter(has_text=re.compile(rf"^{quando.hour:02d}$")).first.click()
    page.locator(".tiktok-timepicker-right").filter(has_text=re.compile(rf"^{quando.minute:02d}$")).first.click()
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)

    campos.nth(1).click()
    for _ in range(3):
        if page.locator(".month-title").first.inner_text().strip() == MESES_TT[quando.month - 1]:
            break
        page.locator(".month-header-wrapper .arrow").last.click()
        page.wait_for_timeout(300)
    page.locator("span.day.valid").filter(has_text=re.compile(rf"^{quando.day}$")).first.click()
    page.wait_for_timeout(400)

    hora, data = campos.nth(0).input_value(), campos.nth(1).input_value()
    if (hora, data) != (f"{quando:%H:%M}", f"{quando:%Y-%m-%d}"):
        raise RuntimeError(f"Agendamento ficou {data} {hora}, esperado {quando:%Y-%m-%d %H:%M}")


def postar(page, video: Path, revisar=False, quando: datetime | None = None, progresso=None) -> dict:
    titulo, tags = textos(video)
    passo(progresso, "abrindo TikTok Studio")
    page.goto(UPLOAD_URL, wait_until="domcontentloaded")
    if "login" in page.url:
        raise NaoLogado("TikTok nao esta logado no perfil do script")

    passo(progresso, "enviando video")
    page.locator("input[type=file][accept*='video']").set_input_files(str(video), timeout=60_000)
    page.locator("[data-e2e=upload_status_container]").get_by_text("Enviado").wait_for(timeout=15 * 60_000)
    page.wait_for_timeout(1500)
    _fechar_popups(page)

    passo(progresso, "escrevendo legenda")
    page.locator(".public-DraftEditor-content").click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.type(f"{titulo} {tags} ", delay=random.randint(25, 60))
    page.wait_for_timeout(800)
    page.keyboard.press("Escape")
    _fechar_popups(page)

    if quando:
        passo(progresso, f"agendando {quando:%d/%m %H:%M}")
        _agendar(page, quando)
    else:
        passo(progresso, "modo: agora")
        page.locator("input[name=postSchedule][value=post_now]").check(force=True)

    if revisar:
        return {"status": "revisar"}

    passo(progresso, "publicando" if not quando else "confirmando agendamento")
    page.locator("[data-e2e=post_video_button]").click()
    try:
        page.wait_for_url("**/tiktokstudio/content**", timeout=20_000)
    except PWTimeout:
        agora = page.get_by_role("button", name=re.compile("Publicar agora|Agendar"))
        if agora.count() and agora.first.is_visible():
            agora.first.click()
        page.wait_for_url("**/tiktokstudio/content**", timeout=120_000)
    if quando:
        return {"status": "agendado", "para": quando.isoformat(timespec="minutes")}
    return {"status": "publicado"}
