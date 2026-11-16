import { type QueryKey, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

interface OpcoesAcao<R> {
  /** Mensagem (ou função) do toast de sucesso. Omitida = sem toast. */
  sucesso?: string | ((r: R) => string)
  /** Chaves a invalidar quando der certo. */
  invalidar?: QueryKey[]
}

/** useMutation com toasts de sucesso/erro e invalidação de cache: o padrão de toda ação da interface. */
export function useAcao<V, R>(fn: (vars: V) => Promise<R>, opcoes: OpcoesAcao<R> = {}) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (r) => {
      for (const k of opcoes.invalidar ?? []) void qc.invalidateQueries({ queryKey: k })
      if (opcoes.sucesso) toast.success(typeof opcoes.sucesso === 'function' ? opcoes.sucesso(r) : opcoes.sucesso)
    },
    onError: (e: Error) => {
      toast.error(e.message)
    },
  })
}
