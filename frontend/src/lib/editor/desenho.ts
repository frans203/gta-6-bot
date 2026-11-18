/**
 * Desenha um quadro do vídeo editado num canvas 9:16 (coordenadas lógicas 1080x1920), imitando o render:
 * fundo (desfocado/preto/imagem) -> jogo -> webcam -> legenda (.ass) -> gancho -> crédito -> barra.
 */
import type { Regiao } from '@/api/tipos'

import {
  A,
  type Edicao,
  caixaPx,
  fontesDasZonas,
  hexParaCss,
  L,
  legendaNoTempo,
  type Palavra,
  recorteCobrir,
} from './modelo'

export interface Cena {
  ed: Edicao
  sw: number
  sh: number
  /** vídeo principal (jogo, fundo e áudio) */
  video: HTMLVideoElement
  /** vídeo da webcam quando há atraso (sem sincronia); senão o principal */
  videoCam: HTMLVideoElement
  fundoImg: HTMLImageElement | null
  corteJogo?: Regiao | null
  corteWebcam?: Regiao | null
  grupos: Palavra[][]
  t: number
  duracao: number
  gancho: string | null
  credito: string
  barra: boolean
}

function quebrar(ctx: CanvasRenderingContext2D, palavras: string[], larguraMax: number): number[][] {
  const linhas: number[][] = [[]]
  let largura = 0
  const espaco = ctx.measureText(' ').width
  palavras.forEach((p, i) => {
    const w = ctx.measureText(p).width
    const atual = linhas[linhas.length - 1]
    if (atual.length && largura + espaco + w > larguraMax) {
      linhas.push([i])
      largura = w
    } else {
      atual.push(i)
      largura += (atual.length > 1 ? espaco : 0) + w
    }
  })
  return linhas
}

function desenharLegenda(ctx: CanvasRenderingContext2D, c: Cena) {
  const leg = c.ed.legenda
  if (!leg.mostrar) return
  const atual = legendaNoTempo(c.grupos, c.t)
  if (!atual) return
  const caixa = (s: string) => (leg.maiusculas ? s.toUpperCase() : s)
  const palavras = atual.bloco.map((w) => caixa(w.p))
  const fonte = `bold ${leg.tamanho}px "${leg.fonte}"`
  ctx.font = fonte
  ctx.textBaseline = 'middle'
  ctx.lineJoin = 'round'
  const linhas = quebrar(ctx, palavras, L - 120)
  const alturaLinha = leg.tamanho * 1.15
  const espaco = ctx.measureText(' ').width
  let y = leg.y * A - ((linhas.length - 1) * alturaLinha) / 2
  for (const linha of linhas) {
    const larguras = linha.map((i) => ctx.measureText(palavras[i]).width * (i === atual.ativa ? 1.08 : 1))
    const total = larguras.reduce((a, b) => a + b, 0) + espaco * (linha.length - 1)
    let x = L / 2 - total / 2
    linha.forEach((i, j) => {
      const ativa = i === atual.ativa
      ctx.save()
      ctx.translate(x + larguras[j] / 2, y)
      if (ativa) ctx.scale(1.08, 1.08)
      ctx.textAlign = 'center'
      ctx.font = fonte
      if (leg.contorno > 0) {
        ctx.strokeStyle = '#000'
        ctx.lineWidth = leg.contorno * 2
        ctx.strokeText(palavras[i], 0, 0)
      }
      ctx.fillStyle = hexParaCss(ativa ? leg.destaque : leg.cor)
      ctx.fillText(palavras[i], 0, 0)
      ctx.restore()
      x += larguras[j] + espaco
    })
    y += alturaLinha
  }
}

function desenharGancho(ctx: CanvasRenderingContext2D, c: Cena) {
  if (!c.gancho || c.t > Math.min(3.5, c.duracao)) return
  const g = c.ed.gancho
  const opacidade = Math.min(1, (Math.min(3.5, c.duracao) - c.t) / 0.25)
  ctx.save()
  ctx.globalAlpha = Math.max(0, opacidade)
  ctx.font = `bold ${g.tamanho}px "${g.fonte}"`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  const palavras = c.gancho.split(/\s+/)
  const linhas = quebrar(ctx, palavras, L - 140 - 36)
  const alturaLinha = g.tamanho * 1.2
  let y = g.y * A
  for (const linha of linhas) {
    const texto = linha.map((i) => palavras[i]).join(' ')
    const w = ctx.measureText(texto).width
    ctx.fillStyle = hexParaCss(g.fundo)
    ctx.fillRect(L / 2 - w / 2 - 18, y - 18 + 4, w + 36, alturaLinha + 36 - 8)
    ctx.fillStyle = hexParaCss(g.cor)
    ctx.fillText(texto, L / 2, y + 4)
    y += alturaLinha
  }
  ctx.restore()
}

function desenharCredito(ctx: CanvasRenderingContext2D, c: Cena) {
  if (!c.credito) return
  ctx.save()
  ctx.globalAlpha = 0.75
  ctx.font = 'bold 34px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'bottom'
  ctx.lineWidth = 4
  ctx.strokeStyle = '#000'
  ctx.strokeText(c.credito, L / 2, 1868)
  ctx.fillStyle = '#fff'
  ctx.fillText(c.credito, L / 2, 1868)
  ctx.restore()
}

export function desenhar(ctx: CanvasRenderingContext2D, c: Cena) {
  const { ed, sw, sh } = c
  const fontes = fontesDasZonas(ed, c.corteJogo, c.corteWebcam)
  const pronto = c.video.readyState >= 2
  ctx.save()
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, L, A)

  // fundo
  if (pronto && ed.layout.fundo === 'desfocado') {
    const r = recorteCobrir(fontes.jogo, sw, sh, L, A)
    ctx.filter = 'blur(22px) brightness(0.86)'
    ctx.drawImage(c.video, r.sx, r.sy, r.sw, r.sh, -40, -40, L + 80, A + 80)
    ctx.filter = 'none'
  } else if (ed.layout.fundo === 'imagem' && c.fundoImg?.complete && c.fundoImg.naturalWidth) {
    const img = c.fundoImg
    const s = Math.max(L / img.naturalWidth, A / img.naturalHeight)
    const vw = L / s
    const vh = A / s
    ctx.drawImage(img, (img.naturalWidth - vw) / 2, (img.naturalHeight - vh) / 2, vw, vh, 0, 0, L, A)
  }

  // jogo e webcam (a ordem decide quem fica na frente)
  const camadas: { video: HTMLVideoElement; fonte: Regiao; caixa: ReturnType<typeof caixaPx> }[] = [
    { video: c.video, fonte: fontes.jogo, caixa: caixaPx(ed.layout.jogo.saida) },
  ]
  if (ed.layout.webcam && fontes.webcam) {
    camadas.push({ video: c.videoCam, fonte: fontes.webcam, caixa: caixaPx(ed.layout.webcam.saida) })
    if (!ed.layout.webcam_na_frente) camadas.reverse()
  }
  for (const cam of camadas) {
    if (cam.video.readyState < 2) continue
    const r = recorteCobrir(cam.fonte, sw, sh, cam.caixa.w, cam.caixa.h)
    ctx.drawImage(cam.video, r.sx, r.sy, r.sw, r.sh, cam.caixa.x, cam.caixa.y, cam.caixa.w, cam.caixa.h)
  }

  desenharLegenda(ctx, c)
  desenharGancho(ctx, c)
  desenharCredito(ctx, c)
  if (c.barra && c.duracao > 0) {
    ctx.fillStyle = '#FFE45C'
    ctx.fillRect(0, A - 10, (L * Math.min(c.t, c.duracao)) / c.duracao, 10)
  }
  ctx.restore()
}
