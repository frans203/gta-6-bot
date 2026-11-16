import { useQuery } from '@tanstack/react-query'

import { chaves } from '../chaves'
import { api, dados } from '../cliente'
import type { ContaIn, ContaPatch } from '../tipos'
import { useAcao } from './util'

export function useSistema() {
  return useQuery({
    queryKey: chaves.sistema,
    queryFn: () => dados(api.GET('/api/sistema')),
    refetchInterval: 15_000,
  })
}

export function useContas() {
  return useQuery({ queryKey: chaves.contas, queryFn: () => dados(api.GET('/api/contas')) })
}

export function useCriarConta() {
  return useAcao((body: ContaIn) => dados(api.POST('/api/contas', { body })), {
    sucesso: (c) => `Conta ${c.nome} criada`,
    invalidar: [chaves.contas],
  })
}

export function useAtualizarConta() {
  return useAcao(
    ({ id, body }: { id: string; body: ContaPatch }) =>
      dados(api.PATCH('/api/contas/{conta_id}', { params: { path: { conta_id: id } }, body })),
    { sucesso: 'Conta atualizada', invalidar: [chaves.contas] },
  )
}

export function useLoginConta() {
  return useAcao(
    (id: string) => dados(api.POST('/api/contas/{conta_id}/login', { params: { path: { conta_id: id } } })),
    { sucesso: 'Chrome aberto. Faça login em cada aba e depois feche o Chrome inteiro.' },
  )
}
