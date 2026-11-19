import { AlertTriangle, Cpu, HardDrive, Loader2, Plus, Radar, Scissors, Zap } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { useSistema } from '@/api/hooks/contas'
import { useFontesComCortes } from '@/api/hooks/cortador'
import { registros, useAdicionarVigia, usePainelVigia } from '@/api/hooks/vigia'
import { useJobs } from '@/api/hooks/jobs'
import { usePosts, useVideos } from '@/api/hooks/postagem'
import { urls } from '@/api/cliente'
import { PLATAFORMAS } from '@/api/tipos'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { JobProgresso } from '@/components/job-progresso'
import { IconeTwitch } from '@/components/icones-marca'
import { Plataforma } from '@/components/plataforma'
import { StatusChip } from '@/components/status-chip'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { RollingNumber } from '@/components/ui/rolling-number'
import { Skeleton } from '@/components/ui/skeleton'
import { ABAS_BIBLIOTECA, urlMiniatura } from '@/lib/biblioteca'
import { useConta } from '@/lib/conta'
import { fmtDataHora } from '@/lib/formatos'
import { cn } from '@/lib/utils'

function Indicador({ icone, rotulo, valor, ok }: { icone: React.ReactNode; rotulo: string; valor: React.ReactNode; ok?: boolean }) {
  return (
    <Card size="sm" className="group hover:-translate-y-0.5">
      <CardContent className="flex items-center gap-3">
        <div
          className={cn(
            'rounded-xl p-2.5 ring-1 transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-6 [&_svg]:size-5',
            ok === false ? 'bg-destructive/15 text-destructive ring-destructive/30' : 'bg-gradient-to-br from-roxo/25 to-rosa/15 text-ciano ring-white/10',
          )}
        >
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
              <div className="font-mono text-lg font-semibold text-muted-foreground tabular-nums">
                <RollingNumber value={conta3(p, 'pendente', 'erro', 'atrasado', 'limite_diario', 'nao_logado')} />
              </div>
              <div className="font-mono text-lg font-semibold text-rosa tabular-nums">
                <RollingNumber value={conta3(p, 'agendado', 'agendado_pc')} />
              </div>
              <div className="font-mono text-lg font-semibold text-verde tabular-nums">
                <RollingNumber value={conta3(p, 'publicado')} />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function ParaRevisar() {
  const { data: fontes = [], isLoading } = useFontesComCortes([...ABAS_BIBLIOTECA.revisar.status])
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Para revisar
          <Link to="/biblioteca" className="text-xs font-normal text-rosa hover:underline">
            abrir a Biblioteca →
          </Link>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-24" />
        ) : fontes.length ? (
          <ul className="space-y-2 text-sm">
            {fontes.slice(0, 6).map((f) => {
              const st = f.cortes_status ?? {}
              const n = (st.candidato ?? 0) + (st.enquadrar ?? 0) + (st.erro ?? 0)
              return (
                <li key={f.id}>
                  <Link
                    to={`/biblioteca?fonte=${f.id}`}
                    className="flex items-center gap-3 rounded-lg p-1.5 transition-colors hover:bg-white/5"
                  >
                    {f.miniatura ? (
                      <img src={urlMiniatura(f.miniatura, 160) ?? ''} alt="" className="aspect-video w-16 shrink-0 rounded-md object-cover" />
                    ) : (
                      <div className="aspect-video w-16 shrink-0 rounded-md bg-gradient-to-br from-roxo/40 to-rosa/30" />
                    )}
                    <span className="min-w-0 flex-1 truncate">{f.titulo}</span>
                    <span className="shrink-0 rounded-full bg-rosa/15 px-2 py-0.5 font-mono text-xs text-rosa">{n}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Nada esperando revisão.{' '}
            <Link to="/cortador/novo" className="text-rosa hover:underline">
              Cortar um vídeo →
            </Link>
          </p>
        )}
      </CardContent>
    </Card>
  )
}

/** Campo "canal da Twitch" → cadastra (se for novo) e já liga o vigia. */
function AdicionarAoVigia() {
  const [canal, setCanal] = useState('')
  const adicionar = useAdicionarVigia()
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        if (canal.trim()) adicionar.mutate(canal.trim(), { onSuccess: () => setCanal('') })
      }}
    >
      <Input
        value={canal}
        onChange={(e) => setCanal(e.target.value)}
        placeholder="canal da Twitch (nome ou link)"
        aria-label="Canal da Twitch para vigiar"
        className="h-8 text-sm"
      />
      <Button size="sm" type="submit" variant="outline" disabled={!canal.trim() || adicionar.isPending}>
        {adicionar.isPending ? <Loader2 className="animate-spin" /> : <Plus />} Vigiar
      </Button>
    </form>
  )
}

function VigiaPainel() {
  const { data = [] } = usePainelVigia()
  const ativos = data.filter((v) => v.config.ativo)
  const recentes = data
    .flatMap((v) => registros(v.recentes).filter((x) => x.situacao === 'corte').map((x) => ({ ...x, nome: v.nome })))
    .sort((a, b) => String(b.em).localeCompare(String(a.em)))
    .slice(0, 5)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Radar className={cn('size-4', ativos.length ? 'animate-pulse text-verde' : 'text-muted-foreground')} /> Vigia de clipes
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <AdicionarAoVigia />
        <div className="flex flex-wrap gap-2">
          {data.map((v) => (
            <Link
              key={v.streamer_id}
              to={`/cortador/streamers/${v.streamer_id}?aba=vigia`}
              className={cn(
                'flex items-center gap-2 rounded-full border px-3 py-1 text-xs transition-colors hover:border-roxo/60',
                v.config.ativo ? 'border-verde/40 bg-verde/10' : 'text-muted-foreground',
              )}
            >
              <span className={cn('size-1.5 rounded-full', v.config.ativo ? 'bg-verde' : 'bg-muted-foreground')} />
              {v.nome}
              {v.config.ativo && <span className="text-muted-foreground">· {v.hoje} hoje{v.aguardando.length ? ` · ${v.aguardando.length} esperando` : ''}</span>}
            </Link>
          ))}
        </div>
        {recentes.length ? (
          <ul className="space-y-1.5">
            {recentes.map((x) => (
              <li key={x.id}>
                <Link to={`/biblioteca?corte=${x.corte_id}`} className="flex items-center gap-2 rounded-md px-1.5 py-1 hover:bg-white/5">
                  <Scissors className="size-3.5 shrink-0 text-rosa" />
                  <span className="min-w-0 flex-1 truncate">{x.titulo}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">{x.nome} · {x.views} views</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted-foreground">
            {ativos.length ? 'Nenhum clipe virou corte ainda.' : 'Digite um canal da Twitch acima: o vigia olha os clipes novos sozinho e manda os bons para a Biblioteca.'}
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
      <Cabecalho titulo="Painel" descricao="Visão geral: sistema, jobs, cortes para revisar e a fila da conta selecionada." />
      <div className="space-y-6">
        <StatusSistema />
        <div className="grid gap-6 xl:grid-cols-2">
          <JobsAtivos />
          <ContagensConta />
          <ParaRevisar />
          <VigiaPainel />
          <UltimosErros />
        </div>
      </div>
    </>
  )
}
