/** Regras do enquadramento (sem componentes): regiões em frações 0..1 do quadro original. */
import type { Corte, Modelo, Regiao } from '@/api/tipos'

/** Posição sugerida quando nada foi detectado (canto inferior direito, comum em lives). Igual ao backend. */
export const WEBCAM_EXEMPLO: Regiao = { x: 0.7, y: 0.65, w: 0.28, h: 0.3 }

export const CORES_REGIAO = {
  webcam: { caixa: 'border-ciano bg-ciano/15', etiqueta: 'bg-ciano' },
  jogo: { caixa: 'border-amarelo border-dashed bg-amarelo/5', etiqueta: 'bg-amarelo' },
}

const limitar = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v))

export function normalizarRegiao(r: Regiao): Regiao {
  const w = limitar(r.w, 0.03, 1)
  const h = limitar(r.h, 0.03, 1)
  return { x: limitar(r.x, 0, 1 - w), y: limitar(r.y, 0, 1 - h), w, h }
}

/** Só x, y, w, h (tira confiança/origem). */
export const soRegiao = (r: Regiao): Regiao => ({ x: r.x, y: r.y, w: r.w, h: r.h })

/** Modelo que vale para o corte: o escolhido nele, senão o do streamer, senão o padrão. */
export function modeloEfetivo(modelos: Modelo[], modeloId: number | null | undefined, corte: Corte): Modelo | undefined {
  return (
    modelos.find((m) => m.id === modeloId) ??
    modelos.find((m) => m.id === corte.streamer_modelo_id) ??
    modelos.find((m) => m.padrao)
  )
}

/** Recorte central que o render usa quando a área do jogo não foi marcada (vídeo 16:9). */
export function jogoPadrao(m: Modelo | undefined): Regiao {
  const div = m?.params.divisao ?? 0.55
  const altura = m?.layout === 'jogo_em_cima' ? div : m?.layout === 'webcam_em_cima' ? 1 - div : 1
  const w = Math.min(1, ((1080 / (1920 * altura)) * 1080) / 1920)
  return { x: (1 - w) / 2, y: 0, w, h: 1 }
}

export interface RascunhoEnquadramento {
  webcam?: Regiao | null
  jogo?: Regiao | null
}

/** true se o corte pode ir para o render (webcam confirmada, ou o modelo não usa webcam). */
export function podeRenderizar(corte: Corte, precisaWebcam: boolean, rascunho: RascunhoEnquadramento) {
  if (!precisaWebcam || corte.status !== 'enquadrar') return true
  return rascunho.webcam != null
}
