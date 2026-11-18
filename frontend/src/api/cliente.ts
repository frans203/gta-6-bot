import createClient from 'openapi-fetch'

import type { paths } from './schema'

/** Cliente tipado gerado do OpenAPI do backend (`npm run api:tipos` após mudar a API). */
export const api = createClient<paths>({ baseUrl: '' })

export class ErroApi extends Error {
  status: number
  constructor(mensagem: string, status: number) {
    super(mensagem)
    this.status = status
  }
}

function mensagemDeErro(erro: unknown, status: number): string {
  if (erro && typeof erro === 'object' && 'detail' in erro) {
    const d = (erro as { detail: unknown }).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d)) {
      return d
        .map((x) => (x && typeof x === 'object' && 'msg' in x ? String((x as { msg: unknown }).msg) : String(x)))
        .join('; ')
    }
  }
  return `erro ${status} na API`
}

/** Desembrulha a resposta do openapi-fetch: devolve `data` ou lança ErroApi com a mensagem do backend. */
export async function dados<T>(
  promessa: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await promessa
  if (error !== undefined || !response.ok) {
    throw new ErroApi(mensagemDeErro(error, response.status), response.status)
  }
  return data as T
}

/** URLs de arquivos servidos pela API (vídeos, prints, quadros). */
export const urls = {
  video: (conta: string, nome: string) =>
    `/api/contas/${encodeURIComponent(conta)}/videos/${encodeURIComponent(nome)}/arquivo`,
  corte: (id: number, versao?: string) => `/api/cortes/${id}/arquivo${versao ? `?v=${encodeURIComponent(versao)}` : ''}`,
  print: (nome: string) => `/api/prints/${encodeURIComponent(nome)}`,
  quadro: (streamerId: number, versao?: number) => `/api/streamers/${streamerId}/quadro?v=${versao ?? 0}`,
  fundo: (nome: string) => `/api/fundos/${encodeURIComponent(nome)}`,
  quadroCorte: (corteId: number, versao?: string) =>
    `/api/cortes/${corteId}/quadro${versao ? `?v=${encodeURIComponent(versao)}` : ''}`,
  /** trecho baixado (com folga) que o editor toca */
  bruto: (corteId: number) => `/api/cortes/${corteId}/bruto`,
  fonteTexto: (arquivo: string) => `/api/fontes-texto/${encodeURIComponent(arquivo)}`,
  /** quadro do vídeo pronto (grade da Biblioteca) */
  miniaturaCorte: (corteId: number, versao?: string) =>
    `/api/cortes/${corteId}/miniatura${versao ? `?v=${encodeURIComponent(versao)}` : ''}`,
}
