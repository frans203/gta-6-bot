import { AlertTriangle, Cpu, HardDrive, Zap } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { useSistema } from '@/api/hooks/contas'
import { useJobs } from '@/api/hooks/jobs'
import { usePosts, useVideos } from '@/api/hooks/postagem'
import { urls } from '@/api/cliente'
import { PLATAFORMAS } from '@/api/tipos'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { JobProgresso } from '@/components/job-progresso'
import { IconeTwitch } from '@/components/icones-marca'
import { Plataforma } from '@/components/plataforma'
import { StatusChip } from '@/components/status-chip'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useConta } from '@/lib/conta'
import { fmtDataHora } from '@/lib/formatos'
import { cn } from '@/lib/utils'

function Indicador({ icone, rotulo, valor, ok }: { icone: React.ReactNode; rotulo: string; valor: React.ReactNode; ok?: boolean }) {
  return (
    <Card size="sm">
      <CardContent className="flex items-center gap-3">
        <div className={cn('rounded-lg p-2 [&_svg]:size-5', ok === false ? 'bg-destructive/15 text-destructive' : 'bg-ciano/10 text-ciano')}>
          {icone}
        </div>
        <div className="min-w-0">
          <div className="text-xs text-muted-foreground">{rotulo}</div>
          <div className="truncate font-semibold">{valor}</div>
        </div>
      </CardContent>
    </Card>
  )
}

function StatusSistema() {
  const { data: s, isLoading } = useSistema()
  if (isLoading || !s) return <Skeleton className="h-20" />
  const discos = Object.entries(s.disco_livre_gb)
    .map(([k, v]) => `${k} ${v} GB`)
    .join(' · ')
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Indicador icone={<Zap />} rotulo="Worker de jobs" valor={s.worker_ativo ? 'rodando' : 'parado (python jason.py web)'} ok={s.worker_ativo} />
      <Indicador icone={<Cpu />} rotulo={`GPU · Whisper ${s.whisper_modelo}`} valor={s.gpu ?? 'sem GPU NVIDIA'} ok={!!s.gpu} />
      <Indicador
        icone={<HardDrive />}
        rotulo="Disco livre"
        valor={discos}
        ok={Object.values(s.disco_livre_gb).every((v) => v > 2)}
      />
      <Indicador
        icone={<IconeTwitch />}
        rotulo="API da Twitch"
        valor={s.twitch_api ? 'configurada' : 'não configurada (.env)'}
        ok={s.twitch_api}
      />
    </div>
  )
}

function JobsAtivos() {
  const { data: jobs = [] } = useJobs({ status: 'fila,rodando,cancelando' })
  return (
    <Card>
      <CardHeader>
        <CardTitle>Jobs em andamento</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {jobs.length ? (
          jobs.map((j) => <JobProgresso key={j.id} job={j} />)
        ) : (
          <p className="text-sm text-muted-foreground">Nada rodando agora.</p>
        )}
        <Link to="/jobs" className="block pt-1 text-xs text-ciano hover:underline">
          Ver histórico de jobs →
        </Link>
      </CardContent>
    </Card>
  )
}

function ContagensConta() {
  const { conta } = useConta()
  const { data: videos = [], isLoading } = useVideos(conta?.id)
  if (isLoading) return <Skeleton className="h-40" />
  const conta3 = (p: string, ...st: string[]) => videos.filter((v) => st.includes(v.plataformas[p]?.status ?? 'pendente')).length
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {conta?.nome} · {videos.length} vídeo(s)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-y-3 text-sm">
          <div />
          <div className="text-xs text-muted-foreground">pendentes</div>
          <div className="text-xs text-muted-foreground">agendados</div>
          <div className="text-xs text-muted-foreground">publicados</div>
          {PLATAFORMAS.map((p) => (
            <div key={p} className="contents">
              <Plataforma p={p} />
              <div className="font-semibold text-muted-foreground">{conta3(p, 'pendente', 'erro', 'atrasado', 'limite_diario', 'nao_logado')}</div>
              <div className="font-semibold text-rosa">{conta3(p, 'agendado', 'agendado_pc')}</div>
              <div className="font-semibold text-verde">{conta3(p, 'publicado')}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function ProximosAgendamentos() {
  const { conta } = useConta()
  const [agora] = useState(() => new Date().toISOString().slice(0, 16))
  const { data: posts = [] } = usePosts({ conta_id: conta?.id, status: 'agendado,agendado_pc', de: agora }, !!conta)
  const proximos = [...posts].sort((a, b) => (a.para ?? '').localeCompare(b.para ?? '')).slice(0, 8)
  return (
    <Card>
      <CardHeader>
        <CardTitle>Próximos agendamentos</CardTitle>
      </CardHeader>
      <CardContent>
        {proximos.length ? (
          <ul className="space-y-2 text-sm">
            {proximos.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-2">
                <span className="w-32 shrink-0 font-medium text-laranja tabular-nums">{fmtDataHora(p.para)}</span>
                <Plataforma p={p.plataforma} soIcone />
                <span className="min-w-0 flex-1 truncate">{p.video}</span>
                <StatusChip status={p.status} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Nada agendado. <Link to="/agenda" className="text-ciano hover:underline">Montar um lote →</Link>
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function UltimosErros() {
  const { conta } = useConta()
  const { data: posts = [] } = usePosts({ conta_id: conta?.id, status: 'erro,nao_logado,limite_diario', limite: 8 }, !!conta)
  return (
    <Card>
      <CardHeader>
        <CardTitle>Últimos erros de postagem</CardTitle>
      </CardHeader>
      <CardContent>
        {posts.length ? (
          <ul className="space-y-3 text-sm">
            {posts.map((p) => (
              <li key={p.id} className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Plataforma p={p.plataforma} soIcone />
                  <span className="font-medium">{p.video}</span>
                  <StatusChip status={p.status} />
                  <span className="ml-auto text-xs text-muted-foreground">{fmtDataHora(p.em)}</span>
                </div>
                <p className="line-clamp-2 text-xs text-muted-foreground">{p.erro}</p>
                {p.print && (
                  <a href={urls.print(p.print)} target="_blank" rel="noreferrer" className="text-xs text-ciano hover:underline">
                    ver print da tela
                  </a>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <Vazio icone={<AlertTriangle />} titulo="Nenhum erro registrado" />
        )}
      </CardContent>
    </Card>
  )
}

export function PaginaPainel() {
  return (
    <>
      <Cabecalho titulo="Painel" descricao="Visão geral do pipeline: sistema, jobs, fila e agenda da conta selecionada." />
      <div className="space-y-6">
        <StatusSistema />
        <div className="grid gap-6 xl:grid-cols-2">
          <JobsAtivos />
          <ContagensConta />
          <ProximosAgendamentos />
          <UltimosErros />
        </div>
      </div>
    </>
  )
}
