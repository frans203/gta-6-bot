import { Square } from 'lucide-react'

import { useCancelarJob } from '@/api/hooks/jobs'
import { JOB_ATIVO, type Job } from '@/api/tipos'
import { StatusChip } from '@/components/status-chip'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { fmtRelativo } from '@/lib/formatos'
import { cn } from '@/lib/utils'

/** Barra de progresso de um job (determinada ou "pulsando" quando o job não sabe quanto falta). */
export function BarraJob({ job, className }: { job: Pick<Job, 'status' | 'progresso'>; className?: string }) {
  if (job.status === 'fila') return <Progress value={0} className={cn('h-1.5', className)} />
  if (job.progresso == null && job.status === 'rodando') {
    return (
      <div className={cn('relative h-1.5 overflow-hidden rounded-full bg-muted', className)}>
        <div className="absolute inset-y-0 w-1/3 animate-[pulse_1.2s_ease-in-out_infinite] rounded-full bg-gradient-to-r from-roxo to-rosa" />
      </div>
    )
  }
  return <Progress value={(job.progresso ?? (job.status === 'ok' ? 1 : 0)) * 100} className={cn('h-1.5', className)} />
}

/** Bloco de progresso compacto: mensagem atual + porcentagem + barra (dentro de modais e cards). */
export function ProgressoJob({ job, className }: { job: Pick<Job, 'status' | 'progresso' | 'mensagem'>; className?: string }) {
  const pct = job.progresso != null ? Math.round(job.progresso * 100) : null
  return (
    <div className={cn('space-y-1.5', className)}>
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="min-w-0 truncate text-muted-foreground">{job.status === 'fila' ? 'na fila…' : job.mensagem || 'trabalhando…'}</span>
        {pct != null && job.status !== 'fila' && <span className="shrink-0 font-mono text-rosa tabular-nums">{pct}%</span>}
      </div>
      <BarraJob job={job} />
    </div>
  )
}

/** Linha de job: título, status, mensagem atual, progresso e botão de cancelar. */
export function JobProgresso({ job, onAbrir }: { job: Job; onAbrir?: (id: number) => void }) {
  const cancelar = useCancelarJob()
  const ativo = JOB_ATIVO.includes(job.status)
  return (
    <div className="space-y-2 rounded-lg border bg-card/60 p-3">
      <div className="flex items-start justify-between gap-2">
        <button
          type="button"
          className="min-w-0 text-left text-sm font-medium hover:underline disabled:no-underline"
          onClick={() => onAbrir?.(job.id)}
          disabled={!onAbrir}
        >
          <span className="text-muted-foreground">#{job.id}</span> {job.titulo}
        </button>
        <div className="flex shrink-0 items-center gap-1">
          <StatusChip status={job.status} />
          {ativo && job.status !== 'cancelando' && (
            <Button
              size="icon-xs"
              variant="ghost"
              title="Cancelar (para no próximo passo seguro)"
              disabled={cancelar.isPending}
              onClick={() => cancelar.mutate(job.id)}
            >
              <Square />
            </Button>
          )}
        </div>
      </div>
      {ativo && <BarraJob job={job} />}
      <p className="truncate text-xs text-muted-foreground" title={job.erro ?? job.mensagem}>
        {job.status === 'erro' ? job.erro : job.mensagem} · {fmtRelativo(job.atualizado_em)}
      </p>
    </div>
  )
}
