import type { Corte, Job } from '@/api/tipos'

/** Status de cada aba da Biblioteca. "Para revisar" lista vídeos originais; as outras, cortes. */
export const ABAS_BIBLIOTECA = {
  revisar: { rotulo: 'Para revisar', status: ['candidato', 'enquadrar', 'erro'] },
  prontos: { rotulo: 'Prontos', status: ['pronto', 'aprovado', 'renderizando'] },
  fila: { rotulo: 'Na fila', status: ['na_fila'] },
  descartados: { rotulo: 'Descartados', status: ['descartado'] },
} as const
export type AbaBiblioteca = keyof typeof ABAS_BIBLIOTECA

/** Cortes que ainda aparecem dentro do modal do vídeo original (os que podem ser gerados). */
export const STATUS_A_GERAR = ['candidato', 'enquadrar', 'erro', 'aprovado', 'renderizando']
export const gerando = (c: Pick<Corte, 'status'>) => ['aprovado', 'renderizando'].includes(c.status)

/** Miniatura da Twitch vem com "%{width}x%{height}" no meio da URL. */
export function urlMiniatura(url?: string | null, largura = 640) {
  if (!url) return null
  return url.replace('%{width}', String(largura)).replace('%{height}', String(Math.round((largura * 9) / 16)))
}

/** Jobs ativos de render/enquadramento de um corte (o mais recente primeiro). */
export const jobsDoCorte = (jobs: Job[], id: number) => jobs.filter((j) => j.params.corte_id === id)

export const LIMITE_TITULO = 200
