import { useQuery } from '@tanstack/react-query'

import { chaves } from '../chaves'
import { api, dados } from '../cliente'
import { useAcao } from './util'

export interface FiltrosJobs {
  status?: string
  tipo?: string
  limite?: number
}

/** Lista de jobs. O SSE (useEventos) mantém o cache atualizado; o refetch periódico é só uma rede de segurança. */
export function useJobs(filtros: FiltrosJobs = {}) {
  return useQuery({
    queryKey: chaves.jobs(filtros),
    queryFn: () => dados(api.GET('/api/jobs', { params: { query: filtros } })),
    refetchInterval: 30_000,
  })
}

export function useJob(id: number | null) {
  return useQuery({
    queryKey: chaves.job(id ?? 0),
    queryFn: () => dados(api.GET('/api/jobs/{job_id}', { params: { path: { job_id: id! } } })),
    enabled: id != null,
    refetchInterval: (q) => (['fila', 'rodando', 'cancelando'].includes(q.state.data?.status ?? '') ? 2_000 : false),
  })
}

export function useCancelarJob() {
  return useAcao(
    (id: number) => dados(api.POST('/api/jobs/{job_id}/cancelar', { params: { path: { job_id: id } } })),
    { sucesso: (j) => (j.status === 'cancelado' ? 'Job cancelado' : 'Cancelando no próximo passo seguro...'), invalidar: [chaves.jobsTodos] },
  )
}

export function useRepetirJob() {
  return useAcao(
    (id: number) => dados(api.POST('/api/jobs/{job_id}/repetir', { params: { path: { job_id: id } } })),
    { sucesso: (j) => `Job #${j.id} na fila de novo`, invalidar: [chaves.jobsTodos] },
  )
}

export function useLogs(linhas = 300) {
  return useQuery({
    queryKey: chaves.logs,
    queryFn: () => dados(api.GET('/api/logs', { params: { query: { linhas } } })),
    staleTime: Infinity,
  })
}

export function usePrints() {
  return useQuery({ queryKey: chaves.prints, queryFn: () => dados(api.GET('/api/prints', { params: { query: {} } })) })
}
