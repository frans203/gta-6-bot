"""Instagram Reels (web) — fluxo mapeado em 13/11/2026."""
import random
from datetime import datetime
from pathlib import Path

from .comum import LOGS, NaoLogado, passo, textos

NOME = "instagram"
AGENDA_NATIVA = False
ETAPAS = 5
LOGIN_URL = "https://www.instagram.com/accounts/login/"
HOME_URL = "https://www.instagram.com/"


def _dialogo(page, rotulo):
    return page.locator(f"[role=dialog][aria-label='{rotulo}']")


def _avancar(page):
    page.locator("[role=dialog] [role=button]:text-is('Avançar'), [role=dialog] button:text-is('Avançar')").first.click()
    page.wait_for_timeout(1500)


def postar(page, video: Path, revisar=False, quando: datetime | None = None, progresso=None) -> dict:
    """Instagram web nao agenda: `quando` e ignorado aqui (o agendamento e feito pelo Agendador do Windows)."""
    titulo, tags = textos(video)
    passo(progresso, "abrindo Instagram")
    page.goto(HOME_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    if "accounts/login" in page.url or page.locator("input[name=username]").count():
        raise NaoLogado("Instagram nao esta logado no perfil do script")

    # Criar (+) > Postar
    page.locator("svg[aria-label='Novo post']").first.click()
    postar_item = page.get_by_text("Postar", exact=True)
    postar_item.first.wait_for(timeout=10_000)
    postar_item.first.click()

    entrada = page.locator("[role=dialog] input[type=file]")
    entrada.wait_for(state="attached", timeout=20_000)
    passo(progresso, "enviando video")
    entrada.set_input_files(str(video))

    # Pode aparecer "Agora os posts de video sao compartilhados como reels" -> OK
    ok = page.locator("[role=dialog] button:text-is('OK')")
    try:
        ok.wait_for(timeout=4000)
        ok.click()
    except Exception:
        pass

    # Cortar: proporcao Original (vertical inteiro)
    _dialogo(page, "Cortar").wait_for(timeout=120_000)
    passo(progresso, "corte original 9:16")
    page.locator("[role=dialog] svg[aria-label='Selecionar corte']").first.click()
    page.locator("[role=dialog] [role=button]:has(span:text-is('Original'))").first.click()
    _avancar(page)

    # Editar (capa/encurtar) -> Avancar
    _dialogo(page, "Editar").wait_for(timeout=60_000)
    _avancar(page)

    # Legenda
    legenda = page.locator("[role=dialog] [contenteditable=true][aria-label^='Adicione uma legenda']")
    legenda.wait_for(timeout=30_000)
    passo(progresso, "escrevendo legenda")
    legenda.click()
    page.keyboard.type(f"{titulo} {tags}", delay=random.randint(20, 45))
    page.keyboard.type(" ")  # fecha sugestoes de hashtag (Escape fecharia o modal!)
    page.wait_for_timeout(800)

    if revisar:
        return {"status": "revisar"}

    passo(progresso, "compartilhando")
    page.locator("[role=dialog] [role=button]:text-is('Compartilhar'), [role=dialog] button:text-is('Compartilhar')").first.click()

    feito = page.locator("[role=dialog]:has-text('foi compartilhado')")
    feito.wait_for(timeout=10 * 60_000)
    try:  # prova do sucesso para conferir depois sem abrir o navegador
        page.screenshot(path=str(LOGS / f"ok_instagram_{video.stem}_{datetime.now():%Y%m%d_%H%M}.png"))
    except Exception:
        pass
    fechar = feito.locator("[role=button]:text-is('Concluir'), button:text-is('Concluir')")
    if fechar.count():
        fechar.first.click()
    else:
        page.keyboard.press("Escape")
    return {"status": "publicado"}
