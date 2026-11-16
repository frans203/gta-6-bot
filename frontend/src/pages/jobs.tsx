import { Cog, RefreshCw, Square } from 'lucide-react'
import { useState } from 'react'

import { useCancelarJob, useJob, useJobs, useRepetirJob } from '@/api/hooks/jobs'
import { JOB_ATIVO } from '@/api/tipos'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { BarraJob } from '@/components/job-progresso'
import { StatusChip } from '@/components/status-chip'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { fmtDataHora, fmtRelativo } from '@/lib/formatos'

function duracao(ini?: string | null, fim?: string | null) {
  if (!ini) return '—'
  const s = Math.round(((fim ? new Date(fim) : new Date()).getTime() - new Date(ini).getTime()) / 1000)
  return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}min ${s % 60}s` : `${Math.floor(s / 3600)}h${Math.floor((s % 3600) / 60)}`
}

function DetalheJob({ id, onFechar }: { id: number | null; onFechar: () => void }) {
  const { data: j } = useJob(id)
  const cancelar = useCancelarJob()
  const repetir = useRepetirJob()
  return (
    <Sheet open={id != null} onOpenChange={(a) => !a && onFechar()}>
      <SheetContent className="w-full sm:max-w-2xl">
        {!j ? (
          <Skeleton className="m-4 h-40" />
        ) : (
          <>
            <SheetHeader>
              <SheetTitle>
                #{j.id} {j.titulo}
              </SheetTitle>
              <SheetDescription asChild>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusChip status={j.status} /> {j.tipo} · criado {fmtDataHora(j.criado_em)} · duração{' '}
                  {duracao(j.iniciado_em, j.terminado_em)}
                </div>
              </SheetDescription>
            </SheetHeader>
            <div className="flex min-h-0 flex-1 flex-col gap-3 px-4 pb-4">
              {JOB_ATIVO.includes(j.status) && <BarraJob job={j} />}
              <p className="text-sm">{j.mensagem}</p>
              {j.erro && <pre className="rounded-md bg-destructive/10 p-2 text-xs whitespace-pre-wrap text-destructive">{j.erro}</pre>}
              <div className="flex gap-2">
                {JOB_ATIVO.includes(j.status) && j.status !== 'cancelando' && (
                  <Button variant="outline" onClick={() => cancelar.mutate(j.id)}>
                    <Square /> Cancelar
                  </Button>
                )}
                {!JOB_ATIVO.includes(j.status) && (
                  <Button variant="outline" onClick={() => repetir.mutate(j.id)}>
                    <RefreshCw /> Repetir
                  </Button>
                )}
              </div>
              <details className="text-xs">
                <summary className="cursor-pointer text-muted-foreground">Parâmetros e resultado</summary>
                <pre className="mt-2 overflow-x-auto rounded-md bg-muted p-2">{JSON.stringify({ params: j.params, resultado: j.resultado }, null, 2)}</pre>
              </details>
              <div className="text-xs font-medium text-muted-foreground">Log</div>
              <ScrollArea className="min-h-0 flex-1 rounded-md border bg-black/40">
                <pre className="p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap">{j.log || '(vazio)'}</pre>
              </ScrollArea>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

const FILTROS: Record<string, string | undefined> = {
  todos: undefined,
  ativos: 'fila,rodando,cancelando',
  ok: 'ok',
  erro: 'erro',
  cancelado: 'cancelado',
}

export function PaginaJobs() {
  const [filtro, setFiltro] = useState('todos')
  const [aberto, setAberto] = useState<number | null>(null)
  const { data: jobs = [], isLoading } = useJobs({ status: FILTROS[filtro], limite: 200 })

  return (
    <>
      <Cabecalho titulo="Jobs" descricao="Tarefas longas executadas pelo worker (postar, agendar, buscar, analisar, renderizar...).">
        <Select value={filtro} onValueChange={setFiltro}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos</SelectItem>
            <SelectItem value="ativos">Em andamento</SelectItem>
            <SelectItem value="ok">Concluídos</SelectItem>
            <SelectItem value="erro">Com erro</SelectItem>
            <SelectItem value="cancelado">Cancelados</SelectItem>
          </SelectContent>
        </Select>
      </Cabecalho>
      {isLoading ? (
        <Skeleton className="h-96" />
      ) : !jobs.length ? (
        <Vazio icone={<Cog />} titulo="Nenhum job" />
      ) : (
        <div className="rounded-xl border bg-card/60">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-14">#</TableHead>
                <TableHead>Job</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden md:table-cell">Andamento</TableHead>
                <TableHead className="hidden sm:table-cell">Atualizado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((j) => (
                <TableRow key={j.id} className="cursor-pointer" onClick={() => setAberto(j.id)}>
                  <TableCell className="text-muted-foreground tabular-nums">{j.id}</TableCell>
                  <TableCell className="max-w-80">
                    <div className="truncate font-medium">{j.titulo}</div>
                    <div className="text-xs text-muted-foreground">{j.tipo}</div>
                  </TableCell>
                  <TableCell>
                    <StatusChip status={j.status} />
                  </TableCell>
                  <TableCell className="hidden max-w-72 md:table-cell">
                    {JOB_ATIVO.includes(j.status) && <BarraJob job={j} className="mb-1" />}
                    <div className="truncate text-xs text-muted-foreground">{j.status === 'erro' ? j.erro : j.mensagem}</div>
                  </TableCell>
                  <TableCell className="hidden text-xs text-muted-foreground sm:table-cell">{fmtRelativo(j.atualizado_em)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <DetalheJob id={aberto} onFechar={() => setAberto(null)} />
    </>
  )
}
