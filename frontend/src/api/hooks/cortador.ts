import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo } from 'react'

import { useAtrasado } from '@/lib/use-atrasado'

import { chaves } from '../chaves'
import { api, dados } from '../cliente'
import type {
  AnalisarIn,
  AplicarCortesIn,
  BuscarFontesIn,
  CortarVideoIn,
  CortePatch,
  Fundo,
  ModeloIn,
  ModeloPatch,
  PreviaIn,
  StreamerIn,
  StreamerPatch,
} from '../tipos'
import { useAcao } from './util'

const msgJob = (j: { id: number; titulo: string }) => `Job #${j.id} na fila: ${j.titulo}`

export function usePlugins() {
  return useQuery({ queryKey: chaves.plugins, queryFn: () => dados(api.GET('/api/plugins')), staleTime: Infinity })
}

// ------------------------------------------------------------------ streamers

export function useStreamers() {
  return useQuery({ queryKey: chaves.streamers, queryFn: () => dados(api.GET('/api/streamers')) })
}

export function useStreamer(id: number) {
  return useQuery({
    queryKey: chaves.streamer(id),
    queryFn: () => dados(api.GET('/api/streamers/{streamer_id}', { params: { path: { streamer_id: id } } })),
  })
}

export function useCriarStreamer() {
  return useAcao((body: StreamerIn) => dados(api.POST('/api/streamers', { body })), {
    sucesso: (s) => `${s.nome} adicionado`,
    invalidar: [chaves.streamers],
  })
}

export function useAtualizarStreamer(id: number) {
  return useAcao(
    (body: StreamerPatch) =>
      dados(api.PATCH('/api/streamers/{streamer_id}', { params: { path: { streamer_id: id } }, body })),
    { sucesso: 'Streamer atualizado', invalidar: [chaves.streamers, chaves.streamer(id)] },
  )
}

export function useRemoverStreamer() {
  return useAcao(
    (id: number) => dados(api.DELETE('/api/streamers/{streamer_id}', { params: { path: { streamer_id: id } } })),
    { sucesso: 'Streamer removido', invalidar: [chaves.streamers, chaves.fontesTodas, chaves.cortesTodos] },
  )
}

export function useBuscarFontes(id: number) {
  return useAcao(
    (body: BuscarFontesIn) =>
      dados(api.POST('/api/streamers/{streamer_id}/buscar', { params: { path: { streamer_id: id } }, body })),
    { sucesso: msgJob, invalidar: [chaves.jobsTodos] },
  )
}

export function useDetectarWebcam(id: number) {
  return useAcao(
    (fonteId: number | undefined) =>
      dados(
        api.POST('/api/streamers/{streamer_id}/webcam/detectar', {
          params: { path: { streamer_id: id }, query: { fonte_id: fonteId } },
        }),
      ),
    { sucesso: msgJob, invalidar: [chaves.jobsTodos] },
  )
}

// ------------------------------------------------------------------ fontes

export function useFontes(streamerId?: number) {
  return useQuery({
    queryKey: chaves.fontes(streamerId),
    queryFn: () => dados(api.GET('/api/fontes', { params: { query: { streamer_id: streamerId } } })),
  })
}

export function useAdicionarFonte() {
  return useAcao(
    (body: { streamer_id: number; url: string }) => dados(api.POST('/api/fontes', { body })),
    { sucesso: 'Fonte adicionada (lendo os dados dela...)', invalidar: [chaves.fontesTodas, chaves.streamers] },
  )
}

export function useAnalisar() {
  return useAcao(
    ({ id, body }: { id: number; body: AnalisarIn }) =>
      dados(api.POST('/api/fontes/{fonte_id}/analisar', { params: { path: { fonte_id: id } }, body })),
    { sucesso: msgJob, invalidar: [chaves.jobsTodos, chaves.fontesTodas] },
  )
}

// ------------------------------------------------------------------ cortes

export interface FiltrosCortes {
  status?: string[]
  streamer_id?: number
  fonte_id?: number
}

export function useCortes(filtros: FiltrosCortes) {
  return useQuery({
    queryKey: chaves.cortes(filtros),
    queryFn: () => dados(api.GET('/api/cortes', { params: { query: filtros } })),
  })
}

export function useEditarCorte() {
  return useAcao(
    ({ id, body }: { id: number; body: CortePatch }) =>
      dados(api.PATCH('/api/cortes/{corte_id}', { params: { path: { corte_id: id } }, body })),
    { invalidar: [chaves.cortesTodos] },
  )
}

export function useRenderizar() {
  return useAcao(
    (id: number) => dados(api.POST('/api/cortes/{corte_id}/renderizar', { params: { path: { corte_id: id } } })),
    { sucesso: msgJob, invalidar: [chaves.jobsTodos, chaves.cortesTodos] },
  )
}

export function usePublicarCorte() {
  return useAcao(
    ({ id, conta }: { id: number; conta?: string }) =>
      dados(
        api.POST('/api/cortes/{corte_id}/publicar', {
          params: { path: { corte_id: id } },
          body: { conta_id: conta ?? null },
        }),
      ),
    { sucesso: 'Corte na fila de postagem da conta', invalidar: [chaves.cortesTodos, chaves.videosTodos] },
  )
}

export function useEnquadrar() {
  return useAcao(
    (id: number) => dados(api.POST('/api/cortes/{corte_id}/enquadrar', { params: { path: { corte_id: id } } })),
    { sucesso: msgJob, invalidar: [chaves.jobsTodos] },
  )
}

// ------------------------------------------------------------------ modelos de corte

export function useModelos() {
  return useQuery({ queryKey: chaves.modelos, queryFn: () => dados(api.GET('/api/modelos')) })
}

export function useCriarModelo() {
  return useAcao((body: ModeloIn) => dados(api.POST('/api/modelos', { body })), {
    sucesso: (m) => `Modelo “${m.nome}” criado`,
    invalidar: [chaves.modelos],
  })
}

export function useAtualizarModelo() {
  return useAcao(
    ({ id, body }: { id: number; body: ModeloPatch }) =>
      dados(api.PATCH('/api/modelos/{modelo_id}', { params: { path: { modelo_id: id } }, body })),
    { sucesso: 'Modelo salvo', invalidar: [chaves.modelos] },
  )
}

export function useRemoverModelo() {
  return useAcao(
    (id: number) => dados(api.DELETE('/api/modelos/{modelo_id}', { params: { path: { modelo_id: id } } })),
    { sucesso: 'Modelo removido', invalidar: [chaves.modelos, chaves.streamers, chaves.cortesTodos] },
  )
}

/** Prévia (JPEG 1080x1920) renderizada pelo backend com o mesmo ffmpeg do corte final. */
export function usePrevia(body: PreviaIn | null) {
  const atrasado = useAtrasado(body, 350)
  const consulta = useQuery({
    queryKey: ['previa', atrasado],
    enabled: !!atrasado,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
    gcTime: 30_000,
    queryFn: async ({ signal }) => {
      const r = await fetch('/api/previa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(atrasado),
        signal,
      })
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? `erro ${r.status} na prévia`)
      return r.blob()
    },
  })
  const url = useMemo(() => (consulta.data ? URL.createObjectURL(consulta.data) : null), [consulta.data])
  useEffect(() => () => void (url && URL.revokeObjectURL(url)), [url])
  return { url, carregando: consulta.isFetching, erro: consulta.error }
}

// ------------------------------------------------------------------ fluxo rápido (colar um link)

export function useIdentificar() {
  return useAcao((url: string) => dados(api.POST('/api/identificar', { body: { url } })))
}

export function useCortarVideo() {
  return useAcao((body: CortarVideoIn) => dados(api.POST('/api/cortar', { body })), {
    sucesso: (r) => (r.streamer_criado ? 'Streamer novo cadastrado. Procurando os melhores trechos...' : 'Procurando os melhores trechos...'),
    invalidar: [chaves.jobsTodos, chaves.streamers, chaves.fontesTodas],
  })
}

export function useFonte(id: number | null) {
  return useQuery({
    queryKey: [...chaves.fontesTodas, 'uma', id],
    enabled: id != null,
    queryFn: () => dados(api.GET('/api/fontes/{fonte_id}', { params: { path: { fonte_id: id! } } })),
  })
}

export function useAplicarCortes(fonteId: number) {
  return useAcao(
    (body: AplicarCortesIn) =>
      dados(api.POST('/api/fontes/{fonte_id}/aplicar', { params: { path: { fonte_id: fonteId } }, body })),
    { invalidar: [chaves.cortesTodos] },
  )
}

export function useRenderizarTodos(fonteId: number) {
  return useAcao(
    () => dados(api.POST('/api/fontes/{fonte_id}/renderizar', { params: { path: { fonte_id: fonteId } } })),
    {
      sucesso: (jobs) => (jobs.length ? `${jobs.length} corte(s) na fila de renderização` : 'Nenhum corte pronto para renderizar'),
      invalidar: [chaves.jobsTodos, chaves.cortesTodos],
    },
  )
}

export function useFundos() {
  return useQuery({ queryKey: chaves.fundos, queryFn: () => dados(api.GET('/api/fundos')) })
}

export function useEnviarFundo() {
  return useAcao(
    async (arquivo: File) => {
      const r = await fetch('/api/fundos', { method: 'POST', headers: { 'Content-Type': arquivo.type }, body: arquivo })
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? `erro ${r.status} ao enviar`)
      return (await r.json()) as Fundo
    },
    { sucesso: 'Imagem de fundo enviada', invalidar: [chaves.fundos] },
  )
}
