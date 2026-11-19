import { CalendarClock, Check, Clapperboard,Minus, Plus, Radar, RotateCcw, ScanFace, Scissors, Send, Trash2, Wand2, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { urls } from '@/api/cliente'
import { useEditarCorte, useModelos, usePlugins, usePublicarCorte, useRenderizar } from '@/api/hooks/cortador'
import type { Corte, CortePatch, Job } from '@/api/tipos'
import { SelectPlugin } from '@/components/form-streamer'
import { Enquadramento } from '@/components/enquadramento'
import { ProgressoJob } from '@/components/job-progresso'
import { Plataforma } from '@/components/plataforma'
import { Player9x16, PlayerFonte } from '@/components/players'
import { SelectModelo } from '@/components/previa'
import { StatusChip } from '@/components/status-chip'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { AbasAnimadas } from '@/components/abas-animadas'
import { gerando } from '@/lib/biblioteca'
import { useConta } from '@/lib/conta'
import { modeloEfetivo, podeRenderizar } from '@/lib/enquadramento'
import { Motivos, NOMES_SINAIS } from '@/components/sinais'
import { fmtTempo, lerTempo } from '@/lib/formatos'
import { cn } from '@/lib/utils'

const COR_SINAL: Record<string, string> = {
  audio: 'bg-rosa',
  mais_assistidos: 'bg-ciano',
  clipes_twitch: 'bg-roxo',
  views: 'bg-laranja',
  chat_youtube: 'bg-amarelo',
}
const FORA_DAS_BARRAS = new Set(['pico', 'views', 'frase', 'aprendido'])

/** Barrinhas com a força de cada detector no pico do corte. */
function Sinais({ corte }: { corte: Corte }) {
  // só os detectores principais viram barra; os auxiliares (fala_risada, chat_reacoes...) aparecem em Motivos
  const sinais = Object.entries(corte.sinais).filter(
    ([k, v]) => !FORA_DAS_BARRAS.has(k) && typeof v === 'number' && !k.startsWith('fala_') && !k.startsWith('chat_m') && !k.startsWith('chat_r'),
  )
  return (
    <div className="space-y-1.5 rounded-xl border bg-muted/30 p-3">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Score</span>
        <span className="font-mono font-semibold text-rosa tabular-nums">{corte.score.toFixed(2)}</span>
      </div>
      {sinais.map(([k, v], i) => (
        <div key={k} className="flex items-center gap-2 text-[11px]">
          <span className="w-28 truncate text-muted-foreground">{NOMES_SINAIS[k] ?? k.replaceAll('_', ' ')}</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <motion.div
              className={`h-full rounded-full ${COR_SINAL[k] ?? 'bg-verde'}`}
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(1, v as number) * 100}%` }}
              transition={{ duration: 0.7, delay: 0.1 + i * 0.06, ease: 'easeOut' }}
            />
          </div>
        </div>
      ))}
      <Motivos sinais={corte.sinais} className="pt-1" />
    </div>
  )
}

/** Campo de tempo (m:ss) com botões de ±5 s. */
function CampoTempo({ id, rotulo, valor, onChange, desativado }: {
  id: string
  rotulo: string
  valor: number
  onChange: (s: number) => void
  desativado?: boolean
}) {
  const [texto, setTexto] = useState(fmtTempo(valor))
  const [ultimo, setUltimo] = useState(valor)
  if (ultimo !== valor) {
    setUltimo(valor)
    setTexto(fmtTempo(valor))
  }
  const passo = (d: number) => onChange(Math.max(0, valor + d))
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{rotulo}</Label>
      <div className="flex items-center gap-1">
        <Button type="button" size="icon-sm" variant="outline" onClick={() => passo(-5)} title="-5 s" disabled={desativado}>
          <Minus />
        </Button>
        <Input
          id={id}
          className="w-24 text-center font-mono tabular-nums"
          value={texto}
          disabled={desativado}
          onChange={(e) => setTexto(e.target.value)}
          onBlur={() => {
            const s = lerTempo(texto)
            if (s == null) setTexto(fmtTempo(valor))
            else onChange(s)
          }}
        />
        <Button type="button" size="icon-sm" variant="outline" onClick={() => passo(5)} title="+5 s" disabled={desativado}>
          <Plus />
        </Button>
      </div>
    </div>
  )
}

/** Onde o corte foi parar na fila (servico.publicar_na_fila grava em extra.fila). */
const destinoFila = (c: Corte) => (c.extra as { fila?: { conta: string; video: string } } | null)?.fila

const urlAgendar = (d: { conta: string; video: string }) =>
  `/fila?${new URLSearchParams({ conta: d.conta, video: d.video, aba: 'agendar' })}`

/** Corte já na fila: abre a Fila na aba Agendar desse vídeo. */
function IrParaAgendar({ corte }: { corte: Corte }) {
  const d = destinoFila(corte)
  return (
    <Button asChild className="botao-brilho">
      <Link to={d ? urlAgendar(d) : '/fila'}>
        <CalendarClock /> Agendar
      </Link>
    </Button>
  )
}

function MandarParaFila({ corte }: { corte: Corte }) {
  const { contas } = useConta()
  const [conta, setConta] = useState(corte.conta_id ?? contas.find((c) => c.padrao)?.id ?? '')
  const publicar = usePublicarCorte()
  const navegar = useNavigate()
  return (
    <div className="flex flex-wrap items-end gap-2 rounded-xl border border-rosa/30 bg-rosa/5 p-3">
      <div className="min-w-40 flex-1 space-y-1.5">
        <Label>Mandar para a fila da conta</Label>
        <Select value={conta} onValueChange={setConta}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Escolha a conta" />
          </SelectTrigger>
          <SelectContent>
            {contas.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                {c.nome}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button variant="outline" disabled={!conta || publicar.isPending} onClick={() => publicar.mutate({ id: corte.id, conta })}>
        <Send /> Mandar para a fila
      </Button>
      <Button
        className="botao-brilho"
        disabled={!conta || publicar.isPending}
        onClick={() =>
          publicar.mutate(
            { id: corte.id, conta },
            { onSuccess: (c) => navegar(urlAgendar(destinoFila(c) ?? { conta, video: corte.arquivo?.split(/[\\/]/).pop() ?? '' })) },
          )
        }
      >
        <CalendarClock /> Mandar e agendar
      </Button>
    </div>
  )
}

interface ClipeVigia {
  id: string
  url: string
  views: number
  titulo?: string | null
  criador?: string | null
}

/** Corte que veio do vigia: o clipe original e botões para puxar mais contexto da live. */
function ContextoDaLive({ corte, inicio, fim, onChange }: {
  corte: Corte
  inicio: number
  fim: number
  onChange: (c: { inicio?: number; fim?: number }) => void
}) {
  const extra = corte.extra as { clipes?: ClipeVigia[]; contexto?: { fonte?: string; motivo?: string } }
  const clipes = extra.clipes ?? []
  const doVod = extra.contexto?.fonte === 'vod'
  const t = Math.floor(inicio)
  const linkLive = `${corte.fonte_url}?t=${Math.floor(t / 3600)}h${Math.floor((t % 3600) / 60)}m${t % 60}s`
  return (
    <div className="space-y-2.5 rounded-xl border border-roxo/40 bg-roxo/10 p-3 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <Radar className="size-4 text-rosa" />
        <b className="text-sm">Clipe da Twitch</b>
        <span className="text-muted-foreground">
          {clipes.reduce((s, c) => s + c.views, 0)} views · {clipes.length} clipe(s) deste momento
        </span>
        {clipes.map((c, i) => (
          <a key={c.id} href={c.url} target="_blank" rel="noreferrer" className="text-ciano hover:underline">
            clipe {i + 1}
            {c.criador ? ` (${c.criador})` : ''}
          </a>
        ))}
      </div>
      {doVod ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted-foreground">Mais contexto da live:</span>
          <Button size="xs" variant="outline" onClick={() => onChange({ inicio: Math.max(0, inicio - 10) })}>
            +10 s antes
          </Button>
          <Button size="xs" variant="outline" onClick={() => onChange({ fim: fim + 10 })}>
            +10 s depois
          </Button>
          <a href={linkLive} target="_blank" rel="noreferrer" className="ml-auto text-ciano hover:underline">
            ver na live →
          </a>
        </div>
      ) : (
        <p className="text-muted-foreground">
          {extra.contexto?.motivo === 'VOD só para inscritos'
            ? 'O VOD desta live é só para inscritos (não dá para baixar): este corte é o próprio clipe, sem contexto extra.'
            : 'Esta live não tem VOD (o streamer não salva as lives): este corte é o próprio clipe, sem contexto extra.'}
        </p>
      )}
    </div>
  )
}

/**
 * Tudo de um corte: aba "Corte" (trecho, título, gancho, modelo, renderizar, mandar para a fila) e aba
 * "Cara do streamer" (região da webcam, detectar de novo). Mudar a região de um corte pronto gera o vídeo de novo
 * sozinho (o backend enfileira o render) e o player troca quando terminar.
 */
export function EditorCorte({ corte, jobs }: { corte: Corte; jobs: Job[] }) {
  const [aba, setAba] = useState<'corte' | 'streamer'>(corte.status === 'enquadrar' ? 'streamer' : 'corte')
  const [rascunho, setRascunho] = useState<CortePatch>({})
  const navegar = useNavigate()
  const editar = useEditarCorte()
  const renderizar = useRenderizar()
  const { data: modelos = [] } = useModelos()
  const { data: plugins } = usePlugins()
  const v = { ...corte, ...rascunho } as Corte
  const set = (campos: CortePatch) => setRascunho((r) => ({ ...r, ...campos }))
  const alterado = Object.keys(rascunho).length > 0
  const ocupado = gerando(corte)
  const editavel = !ocupado
  const renderizado = !!corte.arquivo && ['pronto', 'na_fila', 'aprovado', 'renderizando'].includes(corte.status)
  const jobRender = jobs.find((j) => j.tipo === 'renderizar_corte')
  const jobEnquadrar = jobs.find((j) => j.tipo === 'enquadrar_corte')
  const modelo = modeloEfetivo(modelos, v.modelo_id, corte)
  const precisaWebcam = !!plugins?.layouts.find((l) => l.id === modelo?.layout)?.opcoes.precisa_webcam
  const liberado = podeRenderizar(corte, precisaWebcam, rascunho)
  const mudouRegiao = 'webcam' in rascunho || 'jogo' in rascunho || 'sem_webcam' in rascunho
  const rascunhoEnq = {
    ...('webcam' in rascunho && { webcam: rascunho.webcam }),
    ...('jogo' in rascunho && { jogo: rascunho.jogo }),
  }

  const salvar = (depois?: () => void) => {
    if (!alterado) return depois?.()
    editar.mutate({ id: corte.id, body: rascunho }, { onSuccess: () => (setRascunho({}), depois?.()) })
  }
  // num corte pronto, salvar a região já dispara o render no backend; o "jogo" sozinho não, então pede aqui
  const salvarRegiao = () =>
    salvar(() => {
      if (corte.status === 'pronto' && !('webcam' in rascunho) && 'jogo' in rascunho) renderizar.mutate(corte.id)
    })

  const barraAcoes = (
    <div className="flex flex-wrap justify-end gap-2 border-t pt-3">
      {alterado && (
        <>
          <Button variant="ghost" onClick={() => setRascunho({})}>
            <X /> Desfazer
          </Button>
          <Button variant="outline" disabled={editar.isPending} onClick={() => (mudouRegiao ? salvarRegiao() : salvar())}>
            <Check /> {mudouRegiao && corte.status === 'pronto' ? 'Salvar e atualizar o vídeo' : 'Salvar'}
          </Button>
        </>
      )}
      {editavel && corte.status !== 'descartado' && (
        <Button
          variant={renderizado ? 'outline' : 'default'}
          disabled={renderizar.isPending || editar.isPending || !liberado}
          title={liberado ? undefined : 'Marque a posição do streamer na aba “Cara do streamer” primeiro'}
          onClick={() => salvar(() => renderizar.mutate(corte.id))}
        >
          <Wand2 /> {renderizado ? 'Renderizar de novo' : 'Renderizar'}
        </Button>
      )}
    </div>
  )

  return (
    // corte vertical já renderizado: coluna estreita; prévia da live (16:9): coluna larga, senão fica minúscula
    <div className={cn('grid gap-6', renderizado ? 'lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]' : 'lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]')}>
      {/* coluna do vídeo */}
      <div className="space-y-3">
        <div className="relative">
          {renderizado ? (
            <Player9x16 src={urls.corte(corte.id, corte.atualizado_em)} className="max-w-none" />
          ) : (
            <PlayerFonte url={corte.fonte_url} inicio={v.inicio} fim={v.fim} />
          )}
          <AnimatePresence>
            {ocupado && renderizado && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-xl bg-black/70 p-6 text-center backdrop-blur-sm"
              >
                <Wand2 className="size-7 animate-pulse text-rosa" />
                <p className="text-sm font-medium">Atualizando o vídeo…</p>
                {jobRender && <ProgressoJob job={jobRender} className="w-full" />}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Plataforma p={corte.plataforma} soIcone />
          <Link to={`/cortador/streamers/${corte.streamer_id}`} className="font-medium text-foreground hover:text-rosa">
            {corte.streamer_nome}
          </Link>
          <span>·</span>
          <span className="font-mono tabular-nums">
            {fmtTempo(v.inicio)} – {fmtTempo(v.fim)}
          </span>
        </div>
      </div>

      {/* coluna dos ajustes */}
      <div className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm text-muted-foreground">#{corte.n_na_fonte || corte.id}</span>
            <StatusChip status={corte.status} />
            <Badge variant="secondary" className="font-mono tabular-nums">
              {fmtTempo(v.fim - v.inicio)}
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            {corte.status !== 'descartado' && (
              <Button size="sm" variant="outline" onClick={() => void navegar(`/editor/${corte.id}`)} title="Fonte, cores, posições, cortes e ordem dos trechos">
                <Clapperboard /> Editar vídeo
              </Button>
            )}
            {editavel && !['descartado', 'na_fila'].includes(corte.status) && (
              <Button size="sm" variant="ghost" onClick={() => editar.mutate({ id: corte.id, body: { status: 'descartado' } })}>
                <Trash2 /> Descartar
              </Button>
            )}
          </div>
          {corte.status === 'descartado' && (
            <Button size="sm" variant="ghost" onClick={() => editar.mutate({ id: corte.id, body: { status: 'candidato' } })}>
              <RotateCcw /> Restaurar
            </Button>
          )}
        </div>

        {ocupado && jobRender && !renderizado && <ProgressoJob job={jobRender} />}
        {corte.status === 'erro' && corte.erro && (
          <p className="line-clamp-4 rounded-lg border border-destructive/30 bg-destructive/10 p-2.5 text-xs text-destructive">{corte.erro}</p>
        )}

        <AbasAnimadas<'corte' | 'streamer'>
          valor={aba}
          onChange={setAba}
          abas={[
            { id: 'corte', rotulo: 'Corte', Icone: Scissors },
            {
              id: 'streamer',
              rotulo: 'Cara do streamer',
              Icone: ScanFace,
              alerta: corte.status === 'enquadrar' || !!jobEnquadrar,
            },
          ]}
        >
          {aba === 'corte' ? (
            <div className="space-y-4">
              {(corte.extra as { origem?: string }).origem === 'vigia' && editavel && (
                <ContextoDaLive corte={corte} inicio={v.inicio} fim={v.fim} onChange={(c) => set(c)} />
              )}
              <div className="flex flex-wrap gap-4">
                <CampoTempo id={`ini-${corte.id}`} rotulo="Início" valor={v.inicio} onChange={(s) => set({ inicio: s })} desativado={!editavel} />
                <CampoTempo id={`fim-${corte.id}`} rotulo="Fim" valor={v.fim} onChange={(s) => set({ fim: s })} desativado={!editavel} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor={`tit-${corte.id}`}>Título (legenda do post)</Label>
                <Input id={`tit-${corte.id}`} value={v.titulo} maxLength={300} onChange={(e) => set({ titulo: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor={`gan-${corte.id}`}>Gancho (texto no topo nos primeiros segundos)</Label>
                <Input
                  id={`gan-${corte.id}`}
                  value={v.gancho ?? ''}
                  maxLength={120}
                  placeholder="ex.: ELE NÃO ESPERAVA ISSO 😳"
                  onChange={(e) => set({ gancho: e.target.value || null })}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Modelo de corte</Label>
                  <SelectModelo valor={v.modelo_id} rotuloPadrao="Do streamer" onChange={(x) => set({ modelo_id: x })} />
                </div>
                <div className="space-y-1.5">
                  <Label>Legenda</Label>
                  <SelectPlugin tipo="estilos" valor={v.estilo_legenda} rotuloPadrao="Do modelo" onChange={(x) => set({ estilo_legenda: x })} />
                </div>
              </div>
              <Sinais corte={corte} />
              {barraAcoes}
              {corte.status === 'pronto' && <MandarParaFila corte={corte} />}
              {corte.status === 'na_fila' && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rosa/30 bg-rosa/5 p-3">
                  <p className="min-w-0 flex-1 text-xs text-muted-foreground">
                    Já está na fila de postagem. Mudou algo? Renderize de novo e mande para a fila outra vez (troca o vídeo, se ainda não
                    foi postado).
                  </p>
                  <IrParaAgendar corte={corte} />
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {corte.status === 'pronto' && (
                <p className="rounded-lg border border-ciano/30 bg-ciano/10 p-2.5 text-xs">
                  Este corte já foi gerado. Ao salvar uma região nova (ou detectar de novo), o vídeo é <b>atualizado sozinho</b>.
                </p>
              )}
              {corte.status === 'na_fila' && (
                <p className="rounded-lg border border-amarelo/30 bg-amarelo/10 p-2.5 text-xs">
                  Este corte já está na fila de postagem. Se mudar a região, renderize de novo e mande para a fila outra vez.
                </p>
              )}
              {corte.status !== 'descartado' ? (
                <Enquadramento
                  corte={corte}
                  modeloId={v.modelo_id}
                  estilo={v.estilo_legenda}
                  gancho={v.gancho}
                  rascunho={rascunhoEnq}
                  onChange={(r) => set(r)}
                  job={jobEnquadrar}
                  editavel={editavel}
                />
              ) : (
                <p className="text-sm text-muted-foreground">Restaure o corte para mexer no enquadramento.</p>
              )}
              {barraAcoes}
            </div>
          )}
        </AbasAnimadas>
      </div>
    </div>
  )
}
