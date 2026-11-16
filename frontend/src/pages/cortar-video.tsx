import { Check, CheckCircle2, ImagePlus, Languages, Link2, Loader2, ScanFace, Scissors, Upload, Wand2, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { urls } from '@/api/cliente'
import {
  useAplicarCortes,
  useCortarVideo,
  useCortes,
  useEditarCorte,
  useEnviarFundo,
  useFonte,
  useFundos,
  useIdentificar,
  useModelos,
  usePlugins,
  useRenderizar,
  useRenderizarTodos,
  useStreamers,
} from '@/api/hooks/cortador'
import { useJob, useJobs } from '@/api/hooks/jobs'
import type { Corte, CortePatch, Identificado, Job } from '@/api/tipos'
import { Cabecalho } from '@/components/cabecalho'
import { Enquadramento } from '@/components/enquadramento'
import { BarraJob, JobProgresso } from '@/components/job-progresso'
import { Plataforma } from '@/components/plataforma'
import { SelectModelo } from '@/components/previa'
import { StatusChip } from '@/components/status-chip'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { modeloEfetivo, podeRenderizar } from '@/lib/enquadramento'
import { fmtDuracao, fmtTempo } from '@/lib/formatos'
import { cn } from '@/lib/utils'

const NOME_IDIOMA: Record<string, string> = { pt: 'Português', en: 'Inglês', es: 'Espanhol' }
const nomeIdioma = (c?: string | null) => (c ? (NOME_IDIOMA[c] ?? c.toUpperCase()) : '?')
const IDIOMAS_LEGENDA = ['pt', 'en', 'es']
const QTDS = [1, 3, 5, 8, 10]
const PRETO_MINIMO = 0.15

function Passo({ n, titulo, feito, children, descricao }: {
  n: number
  titulo: string
  feito?: boolean
  descricao?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span
            className={cn(
              'flex size-6 items-center justify-center rounded-full text-xs font-bold',
              feito ? 'bg-verde text-black' : 'bg-primary text-primary-foreground',
            )}
          >
            {feito ? <Check className="size-3.5" /> : n}
          </span>
          {titulo}
        </CardTitle>
        {descricao && <CardDescription>{descricao}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

// ------------------------------------------------------------------ 1 e 2: link + quantidade

function ResumoLink({ i }: { i: Identificado }) {
  return (
    <div className="flex gap-3 rounded-lg border p-3">
      {i.miniatura && <img src={i.miniatura} alt="" className="aspect-video w-36 shrink-0 rounded object-cover" />}
      <div className="min-w-0 space-y-1 text-sm">
        <p className="line-clamp-2 font-medium">{i.titulo || i.url}</p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <Plataforma p={i.plataforma} />
          {i.plataforma === 'outro' && <span>({i.site})</span>}
          <span>{i.canal_nome}</span>
          <Badge variant="secondary">{i.tipo === 'clipe' ? 'clipe' : 'vídeo / VOD'}</Badge>
          {i.duracao != null && <span className="tabular-nums">{fmtDuracao(i.duracao)}</span>}
          {i.idioma && <span>idioma: {nomeIdioma(i.idioma)}</span>}
        </div>
        <p className="text-xs">
          {i.streamer_id ? (
            <span className="text-verde">
              {i.fonte_id ? 'Vídeo já cadastrado' : 'Streamer já cadastrado'}: <b>{i.streamer_nome}</b>.
            </span>
          ) : (
            <span className="text-ciano">Streamer novo: vou cadastrar “{i.canal_nome}” automaticamente.</span>
          )}
        </p>
      </div>
    </div>
  )
}

/** Jobs de "cortar vídeo" em andamento e os últimos feitos: dá para sair da página e voltar. */
function EmAndamento({ onAbrir }: { onAbrir: (fonte: number, job: number) => void }) {
  const { data: jobs = [] } = useJobs({ tipo: 'cortar_video', limite: 6 })
  if (!jobs.length) return null
  const ativos = jobs.filter((j) => ['fila', 'rodando', 'cancelando'].includes(j.status))
  const recentes = jobs.filter((j) => !ativos.includes(j)).slice(0, 4)
  const abrir = (j: Job) => onAbrir(j.params.fonte_id as number, j.id)
  return (
    <Card>
      <CardHeader>
        <CardTitle>{ativos.length ? 'Cortes em andamento' : 'Vídeos recentes'}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {ativos.map((j) => (
          <div key={j.id} className="space-y-2 rounded-lg border p-3">
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="min-w-0 truncate font-medium">{j.titulo.replace(/^Cortar · /, '')}</span>
              <Button size="sm" onClick={() => abrir(j)}>
                Abrir
              </Button>
            </div>
            <BarraJob job={j} />
            <p className="text-xs text-muted-foreground">{j.mensagem}</p>
          </div>
        ))}
        {recentes.map((j) => (
          <button
            key={j.id}
            type="button"
            onClick={() => abrir(j)}
            className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted/50"
          >
            <span className="min-w-0 truncate">{j.titulo.replace(/^Cortar · /, '')}</span>
            <StatusChip status={j.status} />
          </button>
        ))}
      </CardContent>
    </Card>
  )
}

function PassosIniciais({ onComecar }: { onComecar: (fonte: number, job: number) => void }) {
  const [url, setUrl] = useState('')
  const [qtd, setQtd] = useState(3)
  const [duracao, setDuracao] = useState(45)
  const [modelo, setModelo] = useState<number | null>(null)
  const identificar = useIdentificar()
  const cortar = useCortarVideo()
  const { data: streamers = [] } = useStreamers()
  const i = identificar.data
  const { data: modelos = [] } = useModelos()
  const modeloStreamer = streamers.find((s) => s.id === i?.streamer_id)?.modelo_id ?? null
  const nomeModeloPadrao = (modelos.find((m) => m.id === modeloStreamer) ?? modelos.find((m) => m.padrao))?.nome
  const curto = i?.duracao != null && i.duracao <= duracao * 1.3

  return (
    <div className="space-y-4">
      <EmAndamento onAbrir={onComecar} />
      <Passo n={1} titulo="Link do vídeo" feito={!!i} descricao="Twitch, YouTube, Kick ou outro site: VOD, vídeo ou clipe.">
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (url.trim()) identificar.mutate(url.trim())
          }}
        >
          <Input
            className="min-w-64 flex-1"
            placeholder="https://www.twitch.tv/videos/... ou https://youtube.com/watch?v=..."
            value={url}
            onChange={(e) => {
              setUrl(e.target.value)
              identificar.reset()
            }}
          />
          <Button type="submit" disabled={!url.trim() || identificar.isPending}>
            {identificar.isPending ? <Loader2 className="animate-spin" /> : <Link2 />} Ler link
          </Button>
        </form>
        {i && (
          <div className="mt-3 space-y-2">
            <ResumoLink i={i} />
            {i.fonte_id && (
              <p className="text-xs text-amarelo">
                Este vídeo já foi cortado antes.{' '}
                <Link className="underline" to={`/cortador/cortes?fonte=${i.fonte_id}`}>
                  Ver os cortes dele
                </Link>{' '}
                ou continue para gerar de novo (os já revisados ficam).
              </p>
            )}
          </div>
        )}
      </Passo>

      {i && (
        <Passo n={2} titulo="Quantos cortes?">
          <div className="space-y-5">
            {curto ? (
              <p className="text-sm text-muted-foreground">O vídeo é curto ({fmtDuracao(i.duracao)}): ele vira 1 corte inteiro.</p>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  {QTDS.map((n) => (
                    <Button key={n} type="button" size="sm" variant={qtd === n ? 'default' : 'outline'} onClick={() => setQtd(n)}>
                      {n}
                    </Button>
                  ))}
                  <span className="ml-2 text-sm text-muted-foreground tabular-nums">{qtd} corte(s)</span>
                </div>
                <Slider min={1} max={20} step={1} value={[qtd]} onValueChange={([v]) => setQtd(v)} className="max-w-sm" />
              </div>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Duração de cada corte</Label>
                <Select value={String(duracao)} onValueChange={(v) => setDuracao(Number(v))}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[30, 45, 60, 90].map((s) => (
                      <SelectItem key={s} value={String(s)}>
                        {s} segundos
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Modelo de corte</Label>
                <SelectModelo
                  valor={modelo}
                  rotuloPadrao={`${i.streamer_id ? 'Do streamer' : 'Padrão'}: ${nomeModeloPadrao ?? '...'}`}
                  onChange={setModelo}
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button
                disabled={cortar.isPending}
                onClick={() =>
                  cortar.mutate(
                    { url: i.url, quantidade: curto ? 1 : qtd, duracao, modelo_id: modelo },
                    { onSuccess: (r) => onComecar(r.fonte_id, r.job.id) },
                  )
                }
              >
                <Scissors /> Fazer os cortes
              </Button>
            </div>
          </div>
        </Passo>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ 4: idioma da legenda

function PerguntaIdioma({ fonteId, cortes }: { fonteId: number; cortes: Corte[] }) {
  const aplicar = useAplicarCortes(fonteId)
  const falado = cortes.find((c) => c.fonte_idioma)?.fonte_idioma ?? cortes.find((c) => c.extra.idioma)?.extra.idioma as string | undefined
  if (!falado) return <p className="text-sm text-muted-foreground">Ainda descobrindo o idioma falado...</p>
  const atual = cortes[0]?.idioma_legenda ?? falado
  const opcoes = Array.from(new Set([falado, 'pt', 'en'].filter((x) => IDIOMAS_LEGENDA.includes(x))))
  return (
    <div className="space-y-2">
      <p className="text-sm">
        O vídeo está em <b>{nomeIdioma(falado)}</b>. Legenda em:
      </p>
      <div className="flex flex-wrap gap-2">
        {opcoes.map((x) => (
          <Button
            key={x}
            variant={atual === x ? 'default' : 'outline'}
            disabled={aplicar.isPending}
            onClick={() => aplicar.mutate({ idioma_legenda: x === falado ? null : (x as 'pt' | 'en' | 'es') })}
          >
            {atual === x && <Check />} {nomeIdioma(x)} {x === falado ? '(original)' : '(traduzida)'}
          </Button>
        ))}
      </div>
      {atual !== falado && (
        <p className="text-xs text-muted-foreground">
          A tradução roda no seu PC (modelo gratuito, sem IA paga). Na 1ª vez baixa ~80 MB. Gírias podem sair literais: confira no
          vídeo pronto.
        </p>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ 5: espaço preto / imagem de fundo

function ImagemDeFundo({ fonteId, cortes }: { fonteId: number; cortes: Corte[] }) {
  const { data: fundos = [] } = useFundos()
  const { data: modelos = [] } = useModelos()
  const enviar = useEnviarFundo()
  const aplicar = useAplicarCortes(fonteId)
  const arquivo = useRef<HTMLInputElement>(null)
  const preto = Math.max(0, ...cortes.map((c) => (c.extra.espaco_preto as number | undefined) ?? 0))
  const atual = cortes.find((c) => c.fundo)?.fundo ?? null
  const modeloFundo = modelos.find((m) => m.layout === 'fundo_imagem')

  const usar = (nome: string) => aplicar.mutate({ fundo: nome, modelo_id: modeloFundo?.id ?? null })
  const enviarArquivo = (f?: File) => f && enviar.mutate(f, { onSuccess: (r) => usar(r.nome) })

  return (
    <div className="space-y-3">
      {preto >= PRETO_MINIMO ? (
        <p className="text-sm">
          Este vídeo tem <b className="text-amarelo">{Math.round(preto * 100)}% de espaço preto</b> (barras). Escolha uma imagem de fundo:
          o corte fica com a <b>imagem atrás</b>, o <b>vídeo em cima</b>, a <b>legenda</b> e o <b>streamer embaixo</b>.
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          Sem barras pretas relevantes{preto > 0 ? ` (${Math.round(preto * 100)}%)` : ''}. Se quiser, use mesmo assim uma imagem de
          fundo.
        </p>
      )}
      <div
        className="flex flex-wrap gap-2"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          enviarArquivo(e.dataTransfer.files[0])
        }}
      >
        {fundos.map((f) => (
          <button
            key={f.nome}
            type="button"
            onClick={() => usar(f.nome)}
            className={cn(
              'relative h-28 w-16 overflow-hidden rounded-md border-2',
              atual === f.nome ? 'border-primary' : 'border-transparent opacity-80 hover:opacity-100',
            )}
            title={f.nome}
          >
            <img src={urls.fundo(f.nome)} alt="" className="size-full object-cover" />
            {atual === f.nome && <CheckCircle2 className="absolute top-1 right-1 size-4 text-primary" />}
          </button>
        ))}
        <button
          type="button"
          onClick={() => arquivo.current?.click()}
          className="flex h-28 w-16 flex-col items-center justify-center gap-1 rounded-md border-2 border-dashed text-[10px] text-muted-foreground hover:bg-muted/50"
        >
          {enviar.isPending ? <Loader2 className="size-5 animate-spin" /> : <ImagePlus className="size-5" />}
          enviar
        </button>
        <input
          ref={arquivo}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => enviarArquivo(e.target.files?.[0])}
        />
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <Upload className="size-3.5" /> Arraste uma imagem aqui ou clique em “enviar” (JPG/PNG/WEBP, de preferência vertical 1080x1920).
        {atual && (
          <Button size="sm" variant="ghost" onClick={() => aplicar.mutate({ fundo: null, modelo_id: null })}>
            <X /> Não usar fundo
          </Button>
        )}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ 6: enquadramento de cada corte

function CorteParaEnquadrar({ corte, jobs, aberto }: { corte: Corte; jobs: Job[]; aberto: boolean }) {
  const [mostrar, setMostrar] = useState(aberto)
  const [rascunho, setRascunho] = useState<CortePatch>({})
  const editar = useEditarCorte()
  const renderizar = useRenderizar()
  const { data: modelos = [] } = useModelos()
  const { data: plugins } = usePlugins()
  const modelo = modeloEfetivo(modelos, corte.modelo_id, corte)
  const precisaWebcam = !!plugins?.layouts.find((l) => l.id === modelo?.layout)?.opcoes.precisa_webcam
  const pendente = !podeRenderizar(corte, precisaWebcam, {})
  const render = jobs.find((j) => j.tipo === 'renderizar_corte')
  const alterado = Object.keys(rascunho).length > 0

  return (
    <div className={cn('space-y-3 rounded-lg border p-3', pendente && 'border-amarelo/50')}>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">#{corte.id}</span>
        <span className="tabular-nums">
          {fmtTempo(corte.inicio)} – {fmtTempo(corte.fim)}
        </span>
        <StatusChip status={corte.status} />
        {!pendente && corte.webcam?.origem === 'auto' && (
          <span className="flex items-center gap-1 text-xs text-verde">
            <ScanFace className="size-3.5" /> streamer identificado
          </span>
        )}
        {!pendente && corte.webcam?.origem === 'manual' && <span className="text-xs text-verde">marcado por você</span>}
        {(corte.extra as { webcam?: string }).webcam === 'nenhuma' && (
          <span className="text-xs text-muted-foreground">sem streamer (sai só o jogo)</span>
        )}
        <div className="ml-auto flex gap-2">
          {corte.status === 'pronto' && (
            <Button size="sm" variant="outline" asChild>
              <a href={urls.corte(corte.id, corte.atualizado_em)} target="_blank" rel="noreferrer">
                Ver vídeo
              </a>
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={() => setMostrar((x) => !x)}>
            {mostrar ? 'Fechar' : ['pronto', 'na_fila'].includes(corte.status) ? 'Alterar crop' : 'Conferir enquadramento'}
          </Button>
        </div>
      </div>
      {render && (
        <div className="space-y-1">
          <BarraJob job={render} />
          <p className="text-xs text-muted-foreground">{render.mensagem}</p>
        </div>
      )}
      {corte.status === 'erro' && corte.erro && <p className="text-xs text-destructive">{corte.erro}</p>}
      {mostrar && (
        <>
          <Enquadramento
            corte={corte}
            modeloId={corte.modelo_id}
            estilo={corte.estilo_legenda}
            gancho={corte.gancho}
            rascunho={{
              ...('webcam' in rascunho && { webcam: rascunho.webcam }),
              ...('jogo' in rascunho && { jogo: rascunho.jogo }),
            }}
            onChange={(r) => setRascunho((x) => ({ ...x, ...r }))}
            job={jobs.find((j) => j.tipo === 'enquadrar_corte')}
            editavel={!['aprovado', 'renderizando'].includes(corte.status)}
          />
          {['aprovado', 'renderizando'].includes(corte.status) && (
            <p className="text-xs text-muted-foreground">Gerando o vídeo... o crop fica editável de novo quando terminar.</p>
          )}
          {corte.status === 'na_fila' && (
            <p className="text-xs text-amarelo">
              Este corte já foi para a fila de postagem. Se mudar o crop, gere de novo e mande para a fila outra vez para trocar o
              vídeo (na tela Revisar cortes).
            </p>
          )}
          {alterado && (
            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="ghost" onClick={() => setRascunho({})}>
                Desfazer
              </Button>
              <Button
                variant="outline"
                disabled={editar.isPending}
                onClick={() => editar.mutate({ id: corte.id, body: rascunho }, { onSuccess: () => setRascunho({}) })}
              >
                <Check /> Só salvar
              </Button>
              <Button
                disabled={editar.isPending || renderizar.isPending}
                onClick={() =>
                  editar.mutate(
                    { id: corte.id, body: rascunho },
                    { onSuccess: () => (setRascunho({}), renderizar.mutate(corte.id)) },
                  )
                }
              >
                <Wand2 /> Salvar e gerar de novo
              </Button>
            </div>
          )}
          {!alterado && ['pronto', 'na_fila', 'candidato', 'erro'].includes(corte.status) && (
            <div className="flex justify-end">
              <Button size="sm" variant="outline" disabled={renderizar.isPending} onClick={() => renderizar.mutate(corte.id)}>
                <Wand2 /> {corte.status === 'candidato' ? 'Gerar este' : 'Gerar este de novo'}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function SugerirModeloComStreamer({ fonteId, cortes }: { fonteId: number; cortes: Corte[] }) {
  const { data: modelos = [] } = useModelos()
  const { data: plugins } = usePlugins()
  const aplicar = useAplicarCortes(fonteId)
  const usaCam = (c: Corte) =>
    !!plugins?.layouts.find((l) => l.id === modeloEfetivo(modelos, c.modelo_id, c)?.layout)?.opcoes.precisa_webcam
  const achados = cortes.filter((c) => c.webcam && ['auto', 'manual'].includes(c.webcam.origem ?? '') && !usaCam(c))
  const alvo = modelos.find((m) => m.layout === 'jogo_em_cima' && m.padrao) ?? modelos.find((m) => m.layout === 'jogo_em_cima')
  if (!achados.length || !alvo || !plugins) return null
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-ciano/40 bg-ciano/10 p-3 text-sm">
      <ScanFace className="size-5 shrink-0 text-ciano" />
      <p className="min-w-0 flex-1">
        Achei a câmera do streamer em {achados.length} corte(s), mas o modelo atual não mostra a webcam.
      </p>
      <Button size="sm" disabled={aplicar.isPending} onClick={() => aplicar.mutate({ modelo_id: alvo.id })}>
        Usar “{alvo.nome}”
      </Button>
    </div>
  )
}

// ------------------------------------------------------------------ página

function Revisao({ fonteId, jobId }: { fonteId: number; jobId: number | null }) {
  const { data: job } = useJob(jobId)
  const { data: fonte } = useFonte(fonteId)
  const { data: cortes = [] } = useCortes({ fonte_id: fonteId })
  const { data: jobsRender = [] } = useJobs({ status: 'fila,rodando', tipo: 'renderizar_corte,enquadrar_corte' })
  const renderizar = useRenderizarTodos(fonteId)
  const analisando = job && ['fila', 'rodando', 'cancelando'].includes(job.status)
  const ativos = [...cortes].filter((c) => c.status !== 'descartado').sort((a, b) => a.inicio - b.inicio)
  const pendentes = ativos.filter((c) => c.status === 'enquadrar').length
  const prontos = ativos.filter((c) => c.status === 'pronto').length
  const renderizando = ativos.filter((c) => ['aprovado', 'renderizando'].includes(c.status)).length

  return (
    <div className="space-y-4">
      {fonte && (
        <p className="text-sm text-muted-foreground">
          <b className="text-foreground">{fonte.titulo}</b> · {fmtDuracao(fonte.duracao)}
        </p>
      )}
      {job && (analisando || job.status === 'erro') && (
        <Passo n={3} titulo="Fazendo os cortes" descricao="Acha os melhores trechos e prepara cada um: streamer, barras pretas e idioma.">
          <JobProgresso job={job} />
        </Passo>
      )}

      {!analisando && ativos.length > 0 && (
        <>
          <Passo n={3} titulo={`${ativos.length} corte(s) encontrados`} feito>
            <p className="text-sm text-muted-foreground">
              {pendentes
                ? `${pendentes} têm uma câmera com posição incerta: recorte no passo 6. Os outros seguem normalmente.`
                : 'Nada para marcar: os cortes seguem direto (com o streamer quando ele aparece, só o jogo quando não).'}
            </p>
          </Passo>

          <SugerirModeloComStreamer fonteId={fonteId} cortes={ativos} />

          <Passo n={4} titulo="Idioma da legenda" feito={!!ativos[0]?.fonte_idioma}>
            <div className="flex items-start gap-3">
              <Languages className="mt-0.5 size-5 shrink-0 text-ciano" />
              <PerguntaIdioma fonteId={fonteId} cortes={ativos} />
            </div>
          </Passo>

          <Passo n={5} titulo="Imagem de fundo" feito={ativos.some((c) => c.fundo)}>
            <ImagemDeFundo fonteId={fonteId} cortes={ativos} />
          </Passo>

          <Passo
            n={6}
            titulo="Enquadramento"
            feito={pendentes === 0}
            descricao="Só os amarelos precisam de você: têm câmera, mas a posição ficou incerta. Arraste o retângulo STREAMER até a webcam e salve (ou diga que não tem streamer)."
          >
            <div className="space-y-3">
              {ativos.map((c) => (
                <CorteParaEnquadrar
                  key={c.id}
                  corte={c}
                  jobs={jobsRender.filter((j) => j.params.corte_id === c.id)}
                  aberto={c.status === 'enquadrar'}
                />
              ))}
            </div>
          </Passo>

          <Passo n={7} titulo="Gerar os vídeos" feito={prontos > 0 && prontos === ativos.length}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                {renderizando > 0 && `${renderizando} gerando... `}
                {prontos > 0 && `${prontos} pronto(s). `}
                {pendentes > 0 && `${pendentes} ainda sem enquadramento (ficam de fora).`}
              </p>
              <div className="flex gap-2">
                {prontos > 0 && (
                  <Button variant="outline" asChild>
                    <Link to={`/cortador/cortes?fonte=${fonteId}&aba=prontos`}>Ver prontos e mandar para a fila</Link>
                  </Button>
                )}
                <Button disabled={renderizar.isPending || ativos.length === pendentes} onClick={() => renderizar.mutate()}>
                  <Wand2 /> {prontos ? 'Gerar de novo' : 'Gerar os vídeos'}
                </Button>
              </div>
            </div>
          </Passo>
        </>
      )}
    </div>
  )
}

export function PaginaCortarVideo() {
  const [params, setParams] = useSearchParams()
  const fonte = params.get('fonte') ? Number(params.get('fonte')) : null
  const job = params.get('job') ? Number(params.get('job')) : null

  return (
    <>
      <Cabecalho
        titulo="Cortar vídeo"
        descricao="Cole o link, diga quantos cortes quer, confira o enquadramento e gere. Sem IA paga: tudo roda no seu PC."
      >
        {fonte && (
          <Button variant="outline" onClick={() => setParams({})}>
            <Link2 /> Outro vídeo
          </Button>
        )}
      </Cabecalho>
      {fonte ? (
        <Revisao fonteId={fonte} jobId={job} />
      ) : (
        <PassosIniciais onComecar={(f, j) => setParams({ fonte: String(f), job: String(j) })} />
      )}
    </>
  )
}
