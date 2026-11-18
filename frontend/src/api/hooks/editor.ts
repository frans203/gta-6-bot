import { useQuery } from '@tanstack/react-query'

import { chaves } from '../chaves'
import { api, dados } from '../cliente'
import type { CortePatch } from '../tipos'
import { useAcao } from './util'

/** Dados do editor de vídeo de um corte (trecho, legenda, edição salva e a padrão). */
export function useEditorInfo(corteId: number) {
  return useQuery({
    queryKey: chaves.editor(corteId),
    queryFn: () => dados(api.GET('/api/cortes/{corte_id}/editor', { params: { path: { corte_id: corteId } } })),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })
}

export function usePrepararEditor(corteId: number) {
  return useAcao(
    () => dados(api.POST('/api/cortes/{corte_id}/editor/preparar', { params: { path: { corte_id: corteId } } })),
    { sucesso: 'Preparando o editor (baixando o trecho e transcrevendo)...', invalidar: [chaves.jobsTodos] },
  )
}

/** Salva a edição (e o texto do gancho) no corte. */
export function useSalvarEdicao(corteId: number) {
  return useAcao(
    (body: CortePatch) => dados(api.PATCH('/api/cortes/{corte_id}', { params: { path: { corte_id: corteId } }, body })),
    { invalidar: [chaves.cortesTodos, chaves.editor(corteId)] },
  )
}

export function useEnviarFonteTexto() {
  return useAcao(
    async (arquivo: File) => {
      const r = await fetch(`/api/fontes-texto?nome=${encodeURIComponent(arquivo.name)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: arquivo,
      })
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? `erro ${r.status} ao enviar a fonte`)
      return (await r.json()) as { nome: string; arquivo: string | null }
    },
    { sucesso: (f) => `Fonte “${f.nome}” adicionada`, invalidar: [['editor']] },
  )
}

/** Quadro exato do ffmpeg com a edição (botão "Conferir no render"). */
export function usePreviaEdicao() {
  return useAcao(async (body: { corte_id: number; edicao: unknown; gancho: string | null }) => {
    const r = await fetch('/api/previa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? `erro ${r.status} na prévia`)
    return URL.createObjectURL(await r.blob())
  })
}
