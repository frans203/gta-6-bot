import { ArrowLeft, Clapperboard, Eye, Loader2, Redo2, Save, ScanEye, Type, Undo2, Wand2, Clock, LayoutTemplate } from 'lucide-react'
import { motion } from 'motion/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { urls } from '@/api/cliente'
import { useCorte, useRenderizar } from '@/api/hooks/cortador'
import { useEditorInfo, usePrepararEditor, usePreviaEdicao, useSalvarEdicao } from '@/api/hooks/editor'
import { useJobs } from '@/api/hooks/jobs'
import type { Corte } from '@/api/tipos'
import { AbasAnimadas } from '@/components/abas-animadas'
import { Vazio } from '@/components/cabecalho'
import { PainelLayout, PainelTempo, PainelTexto } from '@/components/editor/paineis'
import { type Elemento, PreviaCanvas } from '@/components/editor/previa-canvas'
import { Timeline } from '@/components/editor/timeline'
import { ProgressoJob } from '@/components/job-progresso'
import { StatusChip } from '@/components/status-chip'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { useHistorico } from '@/lib/editor/historico'
import {
  apagarTrecho,
  blocos,
  cortarEm,
  type Edicao,
  type EditorInfo,
  type Palavra,
  remapear,
  segmentosArquivo,
} from '@/lib/editor/modelo'
import { useReproducao } from '@/lib/editor/reproducao'

const chaveRascunho = (id: number) => `editor-rascunho-${id}`
const lerRascunho = (id: number): { ed: Edicao; gancho: string } | null => {
  try {
    const t = localStorage.getItem(chaveRascunho(id))
    return t ? JSON.parse(t) : null
  } catch {
    return null
  }
}
const gravarRascunho = (id: number, v: { ed: Edicao; gancho: string } | null) => {
  try {
    if (v) localStorage.setItem(chaveRascunho(id), JSON.stringify(v))
    else localStorage.removeItem(chaveRascunho(id))
  } catch {
    /* sem armazenamento (aba anônima): segue sem rascunho */
  }
}

const fontesCarregadas = new Set<string>()

/** Carrega as fontes enviadas pelo usuário (as do sistema o navegador já acha pelo nome). */
function useFontesCarregadas(fontes: EditorInfo['fontes'], usadas: string[]) {
  const [versao, setVersao] = useState(0)
  useEffect(() => {
    let vivo = true
    const tarefas = fontes
      .filter((f) => f.arquivo && !fontesCarregadas.has(f.nome))
      .map(async (f) => {
        const face = new FontFace(f.nome, `url(${urls.fonteTexto(f.arquivo!)})`)
        await face.load()
        ;(document.fonts as unknown as { add: (f: FontFace) => void }).add(face)
        fontesCarregadas.add(f.nome)
      })
    void Promise.allSettled([...tarefas, ...usadas.map((n) => document.fonts.load(`bold 80px "${n}"`))]).then(
      () => vivo && setVersao((v) => v + 1),
    )
    return () => {
      vivo = false
    }
  }, [fontes, usadas.join('|')]) // eslint-disable-line react-hooks/exhaustive-deps
  return versao
}

function TelaPreparar({ corteId }: { corteId: number }) {
  const preparar = usePrepararEditor(corteId)
  const { data: jobs = [] } = useJobs({ tipo: 'preparar_editor', status: 'fila,rodando' })
  const job = jobs.find((j) => j.params.corte_id === corteId)
  return (
    <div className="mx-auto max-w-lg py-16">
      <Vazio icone={<Clapperboard />} titulo="Preparar o editor">
        <p>
          Para editar, baixo o trecho com 10 s de folga de cada lado e transcrevo a fala (legenda). Leva de alguns segundos a 1 minuto.
        </p>
        <div className="mt-5 space-y-3">
          {job ? (
            <ProgressoJob job={job} />
          ) : (
            <Button className="botao-brilho" disabled={preparar.isPending} onClick={() => preparar.mutate()}>
              {preparar.isPending ? <Loader2 className="animate-spin" /> : <Wand2 />} Preparar agora
            </Button>
          )}
        </div>
      </Vazio>
    </div>
  )
}

function Editor({ corte, info }: { corte: Corte; info: EditorInfo }) {
  const navegar = useNavigate()
  const salvoInicial = useMemo(() => ({ ed: (info.edicao ?? info.padrao)!, gancho: corte.gancho ?? '' }), []) // eslint-disable-line react-hooks/exhaustive-deps
  const hist = useHistorico<{ ed: Edicao; gancho: string }>(salvoInicial)
  const [salvo, setSalvo] = useState(JSON.stringify(salvoInicial))
  const { ed, gancho } = hist.valor
  const alterado = JSON.stringify(hist.valor) !== salvo
  const [aba, setAba] = useState<'texto' | 'layout' | 'tempo'>('texto')
  const [selTrecho, setSelTrecho] = useState<number | null>(null)
  const [selElemento, setSelElemento] = useState<Elemento | null>(null)
  const [previaRender, setPreviaRender] = useState<string | null>(null)
  const salvar = useSalvarEdicao(corte.id)
  const renderizar = useRenderizar()
  const conferir = usePreviaEdicao()
  const { data: jobsRender = [] } = useJobs({ tipo: 'renderizar_corte', status: 'fila,rodando' })
  const jobRender = jobsRender.find((j) => j.params.corte_id === corte.id)

  // rascunho não salvo de outra visita
  const [rascunho, setRascunho] = useState(() => {
    const r = lerRascunho(corte.id)
    return r && JSON.stringify(r) !== JSON.stringify(salvoInicial) ? r : null
  })
  useEffect(() => {
    if (!rascunho) gravarRascunho(corte.id, alterado ? hist.valor : null)
  }, [hist.valor, alterado, corte.id, rascunho])
  useEffect(() => {
    const avisar = (e: BeforeUnloadEvent) => {
      if (alterado) e.preventDefault()
    }
    window.addEventListener('beforeunload', avisar)
    return () => window.removeEventListener('beforeunload', avisar)
  }, [alterado])

  const mudar = useCallback((novo: Edicao, grupo?: string) => hist.definir((v) => ({ ...v, ed: novo }), grupo), [hist])
  const segs = useMemo(() => segmentosArquivo(ed, info.base, info.duracao), [ed, info.base, info.duracao])
  const usarCam = !ed.sincronizado && Math.abs(ed.atraso_streamer) > 0.01
  const rep = useReproducao(segs, ed.atraso_streamer, usarCam)
  const grupos = useMemo(
    () => blocos(remapear(info.palavras as unknown as Palavra[], segs), ed.legenda.por_bloco),
    [info.palavras, segs, ed.legenda.por_bloco],
  )
  const versaoFontes = useFontesCarregadas(info.fontes, [ed.legenda.fonte, ed.gancho.fonte])

  const camOk = !ed.layout.webcam || !!ed.layout.webcam.fonte || ['auto', 'manual'].includes(corte.webcam?.origem ?? '')
  const ocupado = ['aprovado', 'renderizando'].includes(corte.status)

  const cortar = useCallback(() => {
    const novo = cortarEm(ed, segs, rep.tRef.current, info.base)
    if (novo) mudar(novo)
    else toast('Muito perto da ponta do trecho para cortar aqui')
  }, [ed, segs, rep.tRef, info.base, mudar])
  const apagar = useCallback(() => {
    if (selTrecho == null) return
    const novo = apagarTrecho(ed, selTrecho)
    if (novo) {
      mudar(novo)
      setSelTrecho(null)
    }
  }, [ed, selTrecho, mudar])

  const gravar = (depois?: () => void) =>
    salvar.mutate(
      { edicao: ed, gancho: gancho || null },
      {
        onSuccess: () => {
          setSalvo(JSON.stringify(hist.valor))
          gravarRascunho(corte.id, null)
          if (depois) depois()
          else toast.success('Edição salva')
        },
      },
    )
  const gravarERenderizar = () => gravar(() => renderizar.mutate(corte.id))

  // atalhos
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      const alvo = e.target as HTMLElement
      if (alvo.closest('input, textarea, [contenteditable], [role="slider"], [role="combobox"]')) return
      const ctrl = e.ctrlKey || e.metaKey
      if (ctrl && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        if (e.shiftKey) hist.refazer()
        else hist.desfazer()
      } else if (ctrl && e.key.toLowerCase() === 'y') {
        e.preventDefault()
        hist.refazer()
      } else if (ctrl && e.key.toLowerCase() === 's') {
        e.preventDefault()
        gravar()
      } else if (e.key === ' ') {
        e.preventDefault()
        rep.alternar()
      } else if (e.key.toLowerCase() === 's' && !ctrl) {
        cortar()
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        apagar()
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault()
        const passo = (e.shiftKey ? 1 : 1 / 30) * (e.key === 'ArrowLeft' ? -1 : 1)
        rep.pausar()
        rep.ir(rep.tRef.current + passo)
      } else if (e.key === 'Home') {
        rep.ir(0)
      }
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  })

  const voltar = () => {
    if (alterado && !window.confirm('Sair sem salvar? O rascunho fica guardado neste navegador.')) return
    void navegar(`/biblioteca?${['pronto', 'na_fila'].includes(corte.status) ? `corte=${corte.id}` : `fonte=${corte.fonte_id}&corte=${corte.id}`}`)
  }

  const janelaA = corte.inicio - info.base
  const fundoImg = info.fundo_imagem ? urls.fundo(info.fundo_imagem) : null

  return (
    <div className="space-y-4">
      {/* barra superior */}
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="ghost" size="sm" onClick={voltar}>
          <ArrowLeft /> Biblioteca
        </Button>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-bold text-rosa">#{corte.n_na_fonte}</span>
            <h1 className="truncate font-heading text-lg font-bold">{corte.fonte_titulo}</h1>
            <StatusChip status={corte.status} />
          </div>
          <p className="text-xs text-muted-foreground">
            {corte.streamer_nome} · {alterado ? <span className="text-amarelo">alterações não salvas</span> : 'tudo salvo'}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Button size="icon-sm" variant="ghost" disabled={!hist.podeDesfazer} onClick={hist.desfazer} title="Desfazer (Ctrl+Z)">
            <Undo2 />
          </Button>
          <Button size="icon-sm" variant="ghost" disabled={!hist.podeRefazer} onClick={hist.refazer} title="Refazer (Ctrl+Shift+Z)">
            <Redo2 />
          </Button>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={conferir.isPending}
          title="Gera 1 quadro com o mesmo ffmpeg do vídeo final"
          onClick={() => conferir.mutate({ corte_id: corte.id, edicao: ed, gancho: gancho || null }, { onSuccess: setPreviaRender })}
        >
          {conferir.isPending ? <Loader2 className="animate-spin" /> : <ScanEye />} Conferir no render
        </Button>
        <Button variant="outline" size="sm" disabled={!alterado || salvar.isPending} onClick={() => gravar()}>
          <Save /> Salvar
        </Button>
        <Button
          size="sm"
          className="botao-brilho"
          disabled={salvar.isPending || renderizar.isPending || ocupado || !camOk}
          title={camOk ? 'Salva e gera o vídeo' : 'Confirme a posição do streamer na aba Layout'}
          onClick={gravarERenderizar}
        >
          <Wand2 /> Salvar e gerar vídeo
        </Button>
      </div>

      {rascunho && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap items-center gap-3 rounded-xl border border-amarelo/40 bg-amarelo/10 px-4 py-2.5 text-sm"
        >
          <span className="flex-1">Achei um rascunho não salvo deste corte.</span>
          <Button size="sm" onClick={() => (hist.definir(rascunho), setRascunho(null))}>
            Restaurar
          </Button>
          <Button size="sm" variant="ghost" onClick={() => (gravarRascunho(corte.id, null), setRascunho(null))}>
            Descartar
          </Button>
        </motion.div>
      )}
      {jobRender && (
        <div className="rounded-xl border border-roxo/40 bg-roxo/10 p-3">
          <ProgressoJob job={jobRender} />
        </div>
      )}

      {/* prévia + painéis */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,auto)_minmax(0,1fr)]">
        <div className="flex h-[min(68svh,760px)] justify-center">
          <PreviaCanvas
            ed={ed}
            sw={info.largura}
            sh={info.altura}
            rep={rep}
            fonteVideo={urls.bruto(corte.id)}
            fundoImg={fundoImg}
            corteJogo={corte.jogo}
            corteWebcam={corte.webcam}
            grupos={grupos}
            gancho={gancho || null}
            credito={info.credito}
            barra={info.barra}
            selecionado={selElemento}
            onSelecionar={(e) => {
              setSelElemento(e)
              if (e === 'legenda' || e === 'gancho') setAba('texto')
              else if (e) setAba('layout')
            }}
            onChange={mudar}
            versao={versaoFontes}
          />
        </div>
        <div className="max-h-[min(68svh,760px)] min-w-0 overflow-y-auto pr-1">
          <AbasAnimadas<'texto' | 'layout' | 'tempo'>
            valor={aba}
            onChange={setAba}
            abas={[
              { id: 'texto', rotulo: 'Texto', Icone: Type },
              { id: 'layout', rotulo: 'Layout', Icone: LayoutTemplate, alerta: !camOk },
              { id: 'tempo', rotulo: 'Tempo', Icone: Clock },
            ]}
          >
            {aba === 'texto' ? (
              <PainelTexto ed={ed} info={info} gancho={gancho} onGancho={(t) => hist.definir((v) => ({ ...v, gancho: t }), 'gancho-texto')} onChange={mudar} />
            ) : aba === 'layout' ? (
              <PainelLayout
                ed={ed}
                info={info}
                corte={corte}
                onChange={mudar}
                onRestaurar={() => info.padrao && mudar({ ...ed, layout: info.padrao.layout, legenda: { ...ed.legenda, y: info.padrao.legenda.y }, gancho: { ...ed.gancho, y: info.padrao.gancho.y } })}
              />
            ) : (
              <PainelTempo ed={ed} base={info.base} selecionado={selTrecho} onSelecionar={setSelTrecho} onChange={mudar} />
            )}
          </AbasAnimadas>
        </div>
      </div>

      <Timeline
        ed={ed}
        segs={segs}
        base={info.base}
        duracaoArquivo={info.duracao}
        janela={{ a: janelaA, b: janelaA + (corte.fim - corte.inicio) }}
        rep={rep}
        selecionado={selTrecho}
        onSelecionar={setSelTrecho}
        onChange={mudar}
        onCortar={cortar}
        onApagar={apagar}
      />
      <p className="text-center text-[11px] text-muted-foreground">
        <kbd>Espaço</kbd> tocar · <kbd>S</kbd> cortar · <kbd>Delete</kbd> apagar trecho · <kbd>←</kbd>/<kbd>→</kbd> 1 quadro (
        <kbd>Shift</kbd> 1 s) · <kbd>Ctrl+Z</kbd> desfazer · <kbd>Ctrl+S</kbd> salvar
      </p>

      <Dialog open={!!previaRender} onOpenChange={(v) => !v && setPreviaRender(null)}>
        <DialogContent className="max-w-sm sm:max-w-sm">
          <DialogTitle className="flex items-center gap-2">
            <Eye className="size-4 text-rosa" /> Quadro do render
          </DialogTitle>
          <DialogDescription>Gerado pelo mesmo ffmpeg do vídeo final (quadro do meio do trecho, legenda de exemplo).</DialogDescription>
          {previaRender && <img src={previaRender} alt="Quadro do render" className="w-full rounded-xl" />}
        </DialogContent>
      </Dialog>
    </div>
  )
}

/** Editor de vídeo de um corte: texto, layout (jogo/streamer), trechos (cortar/reordenar) e sincronia. */
export function PaginaEditor() {
  const id = Number(useParams().id)
  const { data: corte, isLoading: carregandoCorte } = useCorte(id)
  const { data: info, isLoading } = useEditorInfo(id)
  if (isLoading || carregandoCorte) return <Skeleton className="h-[70svh] rounded-2xl" />
  if (!corte || !info) return <Vazio titulo="Corte não encontrado" />
  if (!info.pronto || !info.padrao) return <TelaPreparar corteId={id} />
  return <Editor key={id} corte={corte} info={info} />
}

