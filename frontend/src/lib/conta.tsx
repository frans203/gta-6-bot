import { createContext, type ReactNode, useContext, useMemo, useState } from 'react'

import { useContas } from '@/api/hooks/contas'
import type { Conta } from '@/api/tipos'

const CHAVE = 'jason:conta'

interface ContaCtx {
  contas: Conta[]
  conta: Conta | undefined
  setContaId: (id: string) => void
  carregando: boolean
}

const Ctx = createContext<ContaCtx | null>(null)

function lerSalva(): string | null {
  try {
    return localStorage.getItem(CHAVE)
  } catch {
    return null
  }
}

/** Conta selecionada globalmente (salva no navegador). Padrão: a conta marcada como `padrao`. */
export function ProvedorConta({ children }: { children: ReactNode }) {
  const { data: contas = [], isLoading } = useContas()
  const [salva, setSalva] = useState<string | null>(lerSalva)

  const valor = useMemo<ContaCtx>(() => {
    const conta = contas.find((c) => c.id === salva) ?? contas.find((c) => c.padrao) ?? contas[0]
    return {
      contas,
      conta,
      carregando: isLoading,
      setContaId: (id) => {
        setSalva(id)
        try {
          localStorage.setItem(CHAVE, id)
        } catch {
          /* navegador sem storage: segue só em memória */
        }
      },
    }
  }, [contas, salva, isLoading])

  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>
}

// oxlint-disable-next-line react/only-export-components -- provedor e hook juntos de propósito
export function useConta() {
  const c = useContext(Ctx)
  if (!c) throw new Error('useConta fora do ProvedorConta')
  return c
}
