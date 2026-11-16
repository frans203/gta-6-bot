import type { ReactNode } from 'react'

/** Título de página + descrição + ações à direita. */
export function Cabecalho({ titulo, descricao, children }: { titulo: ReactNode; descricao?: ReactNode; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="font-heading text-2xl font-bold tracking-tight">{titulo}</h1>
        {descricao && <p className="mt-1 text-sm text-muted-foreground">{descricao}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  )
}

/** Estado vazio de listas. */
export function Vazio({ icone, titulo, children }: { icone?: ReactNode; titulo: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed p-10 text-center">
      {icone && <div className="text-muted-foreground [&_svg]:size-8">{icone}</div>}
      <p className="font-medium">{titulo}</p>
      {children && <div className="max-w-md text-sm text-muted-foreground">{children}</div>}
    </div>
  )
}
