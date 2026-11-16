import { useQuery } from '@tanstack/react-query'

import { chaves } from '../chaves'
import { api, dados } from '../cliente'
import type { AgendarIn, EnviarIn, Grade, PostPatch } from '../tipos'
import { useAcao } from './util'

export function useVideos(conta: string | undefined) {
  return useQuery({
    queryKey: chaves.videos(conta ?? ''),
    queryFn: () => dados(api.GET('/api/contas/{conta_id}/videos', { params: { path: { conta_id: conta! } } })),
    enabled: !!conta,
  })
}

export function useSalvarLegenda(conta: string) {
  return useAcao(
    ({ nome, titulo, tags }: { nome: string; titulo: string; tags: string }) =>
      dados(
        api.PUT('/api/contas/{conta_id}/videos/{nome}/legenda', {
          params: { path: { conta_id: conta, nome } },
          body: { titulo, tags },
        }),
      ),
    { sucesso: 'Legenda salva', invalidar: [chaves.videos(conta)] },
  )
}

export interface FiltrosPlano {
  plataformas?: string[]
  por_hora?: number | null
  ate?: string | null
}

export function usePlano(conta: string | undefined, filtros: FiltrosPlano, ativo: boolean) {
  return useQuery({
    queryKey: chaves.plano(conta ?? '', filtros),
    queryFn: () =>
      dados(
        api.GET('/api/contas/{conta_id}/plano', {
          params: {
            path: { conta_id: conta! },
            query: {
              plataformas: filtros.plataformas,
              por_hora: filtros.por_hora ?? undefined,
              ate: filtros.ate || undefined,
            },
          },
        }),
      ),
    enabled: !!conta && ativo,
  })
}

export function useAgendar(conta: string) {
  return useAcao(
    (body: AgendarIn) => dados(api.POST('/api/contas/{conta_id}/agendar', { params: { path: { conta_id: conta } }, body })),
    { sucesso: (j) => `Job #${j.id} na fila: ${j.titulo}`, invalidar: [chaves.jobsTodos] },
  )
}

export function useEnviar(conta: string) {
  return useAcao(
    (body: EnviarIn) => dados(api.POST('/api/contas/{conta_id}/enviar', { params: { path: { conta_id: conta } }, body })),
    { sucesso: (j) => `Job #${j.id} na fila: ${j.titulo}`, invalidar: [chaves.jobsTodos] },
  )
}

export interface FiltrosPosts {
  conta_id?: string
  status?: string
  de?: string
  ate?: string
  limite?: number
}

export function usePosts(filtros: FiltrosPosts, ativo = true) {
  return useQuery({
    queryKey: chaves.posts(filtros),
    queryFn: () => dados(api.GET('/api/posts', { params: { query: filtros } })),
    enabled: ativo,
  })
}

export function useCorrigirPost() {
  return useAcao(
    ({ id, body }: { id: number; body: PostPatch }) =>
      dados(api.PATCH('/api/posts/{post_id}', { params: { path: { post_id: id } }, body })),
    { sucesso: 'Status corrigido', invalidar: [chaves.postsTodos, chaves.videosTodos] },
  )
}

export function useApagarPost() {
  return useAcao((id: number) => dados(api.DELETE('/api/posts/{post_id}', { params: { path: { post_id: id } } })), {
    sucesso: 'Voltou para pendente',
    invalidar: [chaves.postsTodos, chaves.videosTodos],
  })
}

export function useHorarios() {
  return useQuery({ queryKey: chaves.horarios, queryFn: () => dados(api.GET('/api/horarios')) })
}

export function useSalvarHorarios() {
  return useAcao((body: Record<string, Grade>) => dados(api.PUT('/api/horarios', { body })), {
    sucesso: 'Grade de horários salva',
    invalidar: [chaves.horarios, chaves.planoTodos],
  })
}

export function useTarefasWindows() {
  return useQuery({ queryKey: chaves.tarefasWindows, queryFn: () => dados(api.GET('/api/tarefas-windows')) })
}

export function useBaixarPack() {
  return useAcao((qtd: number) => dados(api.POST('/api/pack/baixar', { body: { qtd } })), {
    sucesso: (j) => `Job #${j.id} na fila: ${j.titulo}`,
    invalidar: [chaves.jobsTodos],
  })
}
