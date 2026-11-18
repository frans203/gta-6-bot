/**
 * Regras do editor de vídeo (sem componentes). As contas espelham o backend (cortes/edicao.py + layouts.py):
 * o que aparece no canvas é o que o ffmpeg vai gerar.
 */
import type { components } from '@/api/schema'
import type { Regiao } from '@/api/tipos'

export type Edicao = components['schemas']['Edicao']
export type Caixa = components['schemas']['Caixa']
export type Zona = components['schemas']['ZonaEd']
export type LayoutEd = components['schemas']['LayoutEd']
export type LegendaEd = components['schemas']['LegendaEd']
export type GanchoEd = components['schemas']['GanchoEd']
export type EditorInfo = components['schemas']['EditorOut']
export interface Palavra {
  p: string
  i: number
  f: number
}

export const L = 1080
export const A = 1920
export const QUADRO: Regiao = { x: 0, y: 0, w: 1, h: 1 }
export const DUR_MIN = 0.2

const limitar = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v))
const par = (n: number) => Math.max(2, Math.floor(n / 2) * 2)

// ------------------------------------------------------------------ linha do tempo

/** Trecho em segundos do ARQUIVO baixado (o arquivo começa em `base` segundos da live). */
export interface SegArq {
  a: number
  b: number
  /** posição do trecho na linha do tempo do vídeo editado */
  ini: number
  /** índice na lista da edição */
  k: number
}

export function segmentosArquivo(ed: Edicao, base: number, duracaoArquivo: number): SegArq[] {
  const out: SegArq[] = []
  let ini = 0
  ed.segmentos.forEach((s, k) => {
    const a = Math.max(0, s.i - base)
    const b = Math.min(duracaoArquivo, s.f - base)
    if (b - a >= 0.1) {
      out.push({ a, b, ini, k })
      ini += b - a
    }
  })
  return out
}

export const duracaoTotal = (segs: SegArq[]) => segs.reduce((t, s) => t + (s.b - s.a), 0)

/** Tempo da linha do tempo -> trecho e segundo do arquivo. */
export function localizar(segs: SegArq[], t: number): { seg: SegArq; arquivo: number } | null {
  if (!segs.length) return null
  for (const s of segs) {
    if (t < s.ini + (s.b - s.a) - 1e-6) return { seg: s, arquivo: s.a + Math.max(0, t - s.ini) }
  }
  const ult = segs[segs.length - 1]
  return { seg: ult, arquivo: ult.b }
}

/** Palavras (segundos do arquivo) -> na linha do tempo editada. Igual a edicao.remapear(). */
export function remapear(palavras: Palavra[], segs: SegArq[]): Palavra[] {
  const out: Palavra[] = []
  for (const s of segs) {
    for (const w of palavras) {
      if (w.i >= s.a && w.i < s.b) out.push({ p: w.p, i: w.i - s.a + s.ini, f: Math.min(w.f, s.b) - s.a + s.ini })
    }
  }
  return out.sort((x, y) => x.i - y.i)
}

/** Agrupa palavras em blocos (igual a legendas.blocos). */
export function blocos(palavras: Palavra[], porBloco: number, pausaMax = 0.7): Palavra[][] {
  const out: Palavra[][] = []
  let atual: Palavra[] = []
  for (const w of palavras) {
    const ult = atual[atual.length - 1]
    if (ult && (atual.length >= porBloco || w.i - ult.f > pausaMax || /[.?!]$/.test(ult.p))) {
      out.push(atual)
      atual = []
    }
    atual.push(w)
  }
  if (atual.length) out.push(atual)
  return out
}

/** Bloco e palavra destacada no instante t (mesma regra do .ass). */
export function legendaNoTempo(grupos: Palavra[][], t: number): { bloco: Palavra[]; ativa: number } | null {
  for (let g = 0; g < grupos.length; g++) {
    const bloco = grupos[g]
    let fimBloco = bloco[bloco.length - 1].f + 0.25
    if (g + 1 < grupos.length) fimBloco = Math.min(fimBloco, grupos[g + 1][0].i)
    if (t < bloco[0].i || t >= fimBloco) continue
    for (let w = 0; w < bloco.length; w++) {
      const fim = w + 1 < bloco.length ? bloco[w + 1].i : fimBloco
      if (t >= bloco[w].i && t < fim) return { bloco, ativa: w }
    }
  }
  return null
}

// ------------------------------------------------------------------ edição dos trechos

/** Corta o trecho que está no tempo t em dois. */
export function cortarEm(ed: Edicao, segs: SegArq[], t: number, base: number): Edicao | null {
  const pos = localizar(segs, t)
  if (!pos) return null
  const abs = pos.arquivo + base
  const s = ed.segmentos[pos.seg.k]
  if (abs - s.i < DUR_MIN || s.f - abs < DUR_MIN) return null
  const segmentos = [...ed.segmentos]
  segmentos.splice(pos.seg.k, 1, { i: s.i, f: abs }, { i: abs, f: s.f })
  return { ...ed, segmentos }
}

export function apagarTrecho(ed: Edicao, k: number): Edicao | null {
  if (ed.segmentos.length <= 1) return null
  return { ...ed, segmentos: ed.segmentos.filter((_, i) => i !== k) }
}

export function moverTrecho(ed: Edicao, de: number, para: number): Edicao {
  const segmentos = [...ed.segmentos]
  const [s] = segmentos.splice(de, 1)
  segmentos.splice(para, 0, s)
  return { ...ed, segmentos }
}

/** Ajusta início/fim de um trecho (segundos da live), sem sair do arquivo baixado. */
export function aparar(ed: Edicao, k: number, lado: 'i' | 'f', valor: number, base: number, duracaoArquivo: number): Edicao {
  const s = ed.segmentos[k]
  const novo =
    lado === 'i'
      ? { ...s, i: limitar(valor, base, s.f - DUR_MIN) }
      : { ...s, f: limitar(valor, s.i + DUR_MIN, base + duracaoArquivo) }
  const segmentos = [...ed.segmentos]
  segmentos[k] = { i: Math.round(novo.i * 1000) / 1000, f: Math.round(novo.f * 1000) / 1000 }
  return { ...ed, segmentos }
}

// ------------------------------------------------------------------ recortes (cobrir sem distorcer, igual ao ffmpeg)

/** Região em frações -> retângulo em pixels do vídeo original (igual a layouts.regiao_px). */
export function regiaoPx(r: Regiao | null | undefined, sw: number, sh: number) {
  const q = r ?? QUADRO
  const x = par(limitar(q.x, 0, 1) * sw)
  const y = par(limitar(q.y, 0, 1) * sh)
  return { x, y, w: par(Math.min(q.w * sw, sw - x)), h: par(Math.min(q.h * sh, sh - y)) }
}

/** Pedaço do original que aparece numa caixa w x h ("cobrir": corta o excesso no centro). */
export function recorteCobrir(fonte: Regiao | null | undefined, sw: number, sh: number, w: number, h: number) {
  const c = regiaoPx(fonte, sw, sh)
  const s = Math.max(w / c.w, h / c.h)
  const vw = w / s
  const vh = h / s
  return { sx: c.x + (c.w - vw) / 2, sy: c.y + (c.h - vh) / 2, sw: vw, sh: vh }
}

export const caixaPx = (c: Caixa) => ({ x: Math.round(c.x * L), y: Math.round(c.y * A), w: par(c.w * L), h: par(c.h * A) })

/** Recorte efetivo do jogo e da webcam (a edição pode ter o próprio; senão o do corte). */
export function fontesDasZonas(ed: Edicao, corteJogo?: Regiao | null, corteWebcam?: Regiao | null) {
  const zc = ed.layout.webcam
  return {
    jogo: ed.layout.jogo.fonte ?? corteJogo ?? QUADRO,
    webcam: zc ? (zc.fonte ?? corteWebcam ?? null) : null,
  }
}

// ------------------------------------------------------------------ predefinições de layout

export type Predefinicao = 'jogo_em_cima' | 'streamer_em_cima' | 'canto' | 'so_jogo'

export function aplicarPredefinicao(lay: LayoutEd, p: Predefinicao, temWebcam: boolean): LayoutEd {
  const cam = lay.webcam
  const zonaCam = (saida: Caixa) => ({ saida, fonte: cam?.fonte ?? null })
  switch (p) {
    case 'jogo_em_cima':
      return { ...lay, jogo: { ...lay.jogo, saida: { x: 0, y: 0, w: 1, h: 0.55 } }, webcam: temWebcam ? zonaCam({ x: 0, y: 0.55, w: 1, h: 0.45 }) : null }
    case 'streamer_em_cima':
      return { ...lay, jogo: { ...lay.jogo, saida: { x: 0, y: 0.36, w: 1, h: 0.64 } }, webcam: temWebcam ? zonaCam({ x: 0, y: 0, w: 1, h: 0.36 }) : null }
    case 'canto':
      return {
        ...lay,
        fundo: lay.fundo === 'preto' ? 'desfocado' : lay.fundo,
        jogo: { ...lay.jogo, saida: { x: 0, y: 0.18, w: 1, h: 0.64 } },
        webcam: temWebcam ? zonaCam({ x: 0.56, y: 0.06, w: 0.4, h: 0.13 }) : null,
        webcam_na_frente: true,
      }
    case 'so_jogo':
      return { ...lay, jogo: { ...lay.jogo, saida: { x: 0, y: 0, w: 1, h: 1 } }, webcam: null }
  }
}

// ------------------------------------------------------------------ formatos

export function fmtSeg(s: number) {
  const m = Math.floor(s / 60)
  const r = s - m * 60
  return `${m}:${r.toFixed(1).padStart(4, '0')}`
}

export const hexParaCss = (h: string) => `#${h}`
export const cssParaHex = (c: string) => c.replace('#', '').toUpperCase().slice(0, 6)
