import { useQuery } from '@tanstack/react-query'

import { chaves } from '../chaves'
import { api, dados } from '../cliente'
import type { components } from '../schema'
import { useAcao } from './util'

export type VigiaConfig = components['schemas']['VigiaConfig']

/** Um clipe que o vigia viu (cortes/vigia.py: _registro). */
export interface RegistroVigia {
  id: string
  titulo: string
  views: number
  url: string
  situacao: 'corte' | 'ignorado' | 'aguardando'
  motivo: string
  corte_id: number | null
  em: string
}
export const registros = (lista: unknown[]) => lista as RegistroVigia[]

export function useVigia(streamerId: number) {
  return useQuery({
    queryKey: chaves.vigia(streamerId),
    queryFn: () => dados(api.GET('/api/streamers/{streamer_id}/vigia', { params: { path: { streamer_id: streamerId } } })),
    refetchInterval: 30_000,
  })
}

export function usePainelVigia() {
  return useQuery({ queryKey: chaves.vigiaTodos, queryFn: () => dados(api.GET('/api/vigia')), refetchInterval: 30_000 })
}

export function useConfigurarVigia(streamerId: number) {
  return useAcao(
    (body: VigiaConfig) =>
      dados(api.PUT('/api/streamers/{streamer_id}/vigia', { params: { path: { streamer_id: streamerId } }, body })),
    { sucesso: (r) => (r.config.ativo ? 'Vigia ligado: olha os clipes a cada ' + r.config.intervalo_min + ' min' : 'Vigia salvo (desligado)'), invalidar: [chaves.vigiaTodos] },
  )
}

export function useVigiarAgora(streamerId: number) {
  return useAcao(
    () => dados(api.POST('/api/streamers/{streamer_id}/vigia/agora', { params: { path: { streamer_id: streamerId } } })),
    { sucesso: 'Olhando os clipes agora...', invalidar: [chaves.jobsTodos] },
  )
}
