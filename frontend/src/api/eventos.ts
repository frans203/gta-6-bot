import { type QueryClient, type QueryKey, useQueryClient } from '@tanstack/react-query'
import { useEffect, useSyncExternalStore } from 'react'
import { toast } from 'sonner'

import { chaves } from './chaves'
import type { Job, JobDetalhe } from './tipos'

const TERMINAIS = ['ok', 'erro', 'cancelado']

/** O que recarregar quando um job de cada tipo termina. Tipo novo de job? Acrescente aqui. */
const INVALIDAR_POR_TIPO: Record<string, QueryKey[]> = {
  enviar: [chaves.videosTodos, chaves.postsTodos, chaves.tarefasWindows, chaves.planoTodos],
  agendar: [chaves.videosTodos, chaves.postsTodos, chaves.tarefasWindows, chaves.planoTodos],
  enviar_agendado: [chaves.videosTodos, chaves.postsTodos, chaves.tarefasWindows, chaves.planoTodos],
  baixar_pack: [chaves.videosTodos, chaves.planoTodos],
  buscar_fontes: [chaves.fontesTodas, chaves.streamers],
  info_fonte: [chaves.fontesTodas],
  analisar_fonte: [chaves.fontesTodas, chaves.cortesTodos, chaves.streamers],
  detectar_webcam: [chaves.streamers, ['streamer']],
  enquadrar_corte: [chaves.cortesTodos, chaves.fontesTodas],
  cortar_video: [chaves.cortesTodos, chaves.fontesTodas, chaves.streamers],
  renderizar_corte: [chaves.cortesTodos, chaves.fontesTodas, chaves.streamers],
}

// ------------------------------------------------------------------ store simples (log ao vivo + conexão)

type Ouvinte = () => void
const MAX_LINHAS = 1000
let linhasLog: string[] = []
let conectado = false
const ouvintes = new Set<Ouvinte>()
const avisar = () => ouvintes.forEach((o) => o())
const assinar = (o: Ouvinte) => {
  ouvintes.add(o)
  return () => ouvintes.delete(o)
}

/** Linhas de log recebidas pelo SSE desde que a página abriu. */
export const useLogAoVivo = () => useSyncExternalStore(assinar, () => linhasLog)
/** true enquanto o EventSource está conectado ao backend. */
export const useConectado = () => useSyncExternalStore(assinar, () => conectado)

// ------------------------------------------------------------------ cache dos jobs

function aplicarJob(qc: QueryClient, job: Job) {
  let achou = false
  qc.setQueriesData<Job[]>({ queryKey: chaves.jobsTodos }, (lista) => {
    if (!lista) return lista
    const i = lista.findIndex((j) => j.id === job.id)
    if (i < 0) return lista
    achou = true
    const nova = [...lista]
    nova[i] = job
    return nova
  })
  qc.setQueryData<JobDetalhe>(chaves.job(job.id), (d) => (d ? { ...d, ...job } : d))
  if (!achou) void qc.invalidateQueries({ queryKey: chaves.jobsTodos })
}

/** Conecta em /api/eventos (SSE). Monte UMA vez, no layout. */
export function useEventos() {
  const qc = useQueryClient()
  useEffect(() => {
    const avisados = new Set<string>()
    const es = new EventSource('/api/eventos')
    es.onopen = () => {
      conectado = true
      avisar()
    }
    es.onerror = () => {
      conectado = false
      avisar()
    }
    es.addEventListener('job', (ev) => {
      const job = JSON.parse((ev as MessageEvent).data) as Job
      aplicarJob(qc, job)
      const chave = `${job.id}:${job.status}`
      if (TERMINAIS.includes(job.status) && !avisados.has(chave)) {
        avisados.add(chave)
        for (const k of INVALIDAR_POR_TIPO[job.tipo] ?? []) void qc.invalidateQueries({ queryKey: k })
        void qc.invalidateQueries({ queryKey: chaves.sistema })
        if (job.status === 'ok') toast.success(`Concluído: ${job.titulo}`)
        else if (job.status === 'erro') toast.error(`Falhou: ${job.titulo}`, { description: job.erro ?? undefined })
        else toast(`Cancelado: ${job.titulo}`)
      }
    })
    es.addEventListener('log', (ev) => {
      const linha = JSON.parse((ev as MessageEvent).data) as string
      linhasLog = [...linhasLog.slice(-(MAX_LINHAS - 1)), linha]
      avisar()
    })
    return () => {
      es.close()
      conectado = false
      avisar()
    }
  }, [qc])
}
