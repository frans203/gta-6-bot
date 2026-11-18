import { ArrowLeft, ExternalLink, Languages, Layers, Wand2 } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { Link } from 'react-router'

import { useAplicarCortes, useCorte, useCortes, useFonte, useRenderizarTodos } from '@/api/hooks/cortador'
import type { Corte, Job } from '@/api/tipos'
import { ImagemDeFundo, PerguntaIdioma, SugerirModeloComStreamer } from '@/components/ajustes-fonte'
import { Grade, CartaoTrecho, TituloCompleto } from '@/components/biblioteca/cartoes'
import { EditorCorte } from '@/components/biblioteca/editor-corte'
import { Plataforma } from '@/components/plataforma'
import { SelectModelo } from '@/components/previa'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { jobsDoCorte, STATUS_A_GERAR, urlMiniatura } from '@/lib/biblioteca'
import { fmtDuracao } from '@/lib/formatos'

const CLASSE_MODAL =
  'max-h-[92svh] w-full max-w-[calc(100%-1.5rem)] gap-0 overflow-y-auto border border-white/10 bg-background/95 p-0 shadow-[0_0_80px_-20px] shadow-roxo/60 backdrop-blur-xl sm:max-w-6xl'

/** Desliza o conteúdo ao trocar entre a lista de cortes e um corte. */
function Painel({ chave, lado, children }: { chave: string; lado: 1 | -1; children: React.ReactNode }) {
  return (
    <motion.div
      key={chave}
      initial={{ opacity: 0, x: 40 * lado }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 * lado }}
      transition={{ type: 'spring', bounce: 0.15, duration: 0.4 }}
    >
      {children}
    </motion.div>
  )
}

function Secao({ icone, titulo, children }: { icone: React.ReactNode; titulo: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3 rounded-2xl border bg-card/60 p-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <span className="text-rosa [&_svg]:size-4">{icone}</span> {titulo}
      </h3>
      {children}
    </div>
  )
}

function ModeloParaTodos({ fonteId, cortes }: { fonteId: number; cortes: Corte[] }) {
  const aplicar = useAplicarCortes(fonteId)
  const iguais = cortes.every((c) => c.modelo_id === cortes[0]?.modelo_id)
  return (
    <div className="max-w-sm">
      <SelectModelo
        valor={iguais ? (cortes[0]?.modelo_id ?? null) : null}
        rotuloPadrao={iguais ? 'Do streamer' : 'Vários (cada corte com o seu)'}
        onChange={(x) => aplicar.mutate({ modelo_id: x })}
      />
    </div>
  )
}

/**
 * Modal de um vídeo original: ajustes para todos os cortes (legenda, fundo, modelo), os cortes que podem ser
 * gerados dele e "Renderizar todos". Clicar num corte abre o editor dele no próprio modal.
 */
export function ModalFonte({ fonteId, corteId, jobs, onCorte, onFechar }: {
  fonteId: number
  corteId: number | null
  jobs: Job[]
  onCorte: (id: number | null) => void
  onFechar: () => void
}) {
  const { data: fonte } = useFonte(fonteId)
  const { data: cortes = [], isLoading } = useCortes({ fonte_id: fonteId })
  const renderizarTodos = useRenderizarTodos(fonteId)
  const ordenados = [...cortes].sort((a, b) => a.inicio - b.inicio)
  const aGerar = ordenados.filter((c) => STATUS_A_GERAR.includes(c.status))
  const ativos = ordenados.filter((c) => c.status !== 'descartado')
  const prontos = ordenados.filter((c) => ['pronto', 'na_fila'].includes(c.status)).length
  const pendentes = aGerar.filter((c) => c.status === 'enquadrar').length
  const liberados = aGerar.filter((c) => ['candidato', 'erro'].includes(c.status)).length
  const corte = corteId != null ? cortes.find((c) => c.id === corteId) : undefined

  return (
    <Dialog open onOpenChange={(v) => !v && onFechar()}>
      <DialogContent className={CLASSE_MODAL}>
        {/* cabeçalho com a capa desfocada atrás */}
        <div className="relative overflow-hidden border-b">
          {fonte?.miniatura && (
            <img src={urlMiniatura(fonte.miniatura) ?? ''} alt="" className="absolute inset-0 size-full scale-110 object-cover opacity-25 blur-2xl" />
          )}
          <div className="relative flex gap-4 p-5 pr-12">
            {fonte?.miniatura && (
              <img src={urlMiniatura(fonte.miniatura) ?? ''} alt="" className="hidden aspect-video w-40 shrink-0 rounded-xl object-cover shadow-lg sm:block" />
            )}
            <div className="min-w-0 space-y-1.5">
              <DialogTitle asChild>
                <div>{fonte ? <TituloCompleto texto={fonte.titulo} className="font-heading text-lg font-bold" /> : <Skeleton className="h-6 w-80" />}</div>
              </DialogTitle>
              <DialogDescription asChild>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  {fonte && (
                    <>
                      <span className="flex items-center gap-1.5">
                        <Plataforma p={fonte.plataforma} soIcone />
                        <Link to={`/cortador/streamers/${fonte.streamer_id}`} className="font-medium text-foreground hover:text-rosa">
                          {fonte.streamer_nome}
                        </Link>
                      </span>
                      <span className="font-mono">{fmtDuracao(fonte.duracao)}</span>
                      <span>{ativos.length} corte(s)</span>
                      <a href={fonte.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-rosa">
                        original <ExternalLink className="size-3" />
                      </a>
                    </>
                  )}
                </div>
              </DialogDescription>
            </div>
          </div>
        </div>

        <div className="overflow-hidden p-5">
          <AnimatePresence mode="wait" initial={false}>
            {corte ? (
              <Painel chave={`corte-${corte.id}`} lado={1}>
                <Button variant="ghost" size="sm" className="mb-4 -ml-2" onClick={() => onCorte(null)}>
                  <ArrowLeft /> Todos os cortes deste vídeo
                </Button>
                <EditorCorte key={corte.id} corte={corte} jobs={jobsDoCorte(jobs, corte.id)} />
              </Painel>
            ) : (
              <Painel chave="lista" lado={-1}>
                <div className="space-y-5">
                  {isLoading ? (
                    <Skeleton className="h-60" />
                  ) : (
                    <>
                      <div className="flex flex-wrap items-end justify-between gap-3">
                        <div>
                          <h3 className="font-heading text-base font-bold">Cortes para gerar</h3>
                          <p className="text-xs text-muted-foreground">
                            {pendentes > 0 && `${pendentes} esperando você marcar a webcam (ficam de fora). `}
                            {prontos > 0 && (
                              <Link to="/biblioteca?aba=prontos" className="text-verde hover:underline">
                                {prontos} já pronto(s) →
                              </Link>
                            )}
                          </p>
                        </div>
                        <Button
                          className="botao-brilho"
                          disabled={renderizarTodos.isPending || liberados === 0}
                          onClick={() => renderizarTodos.mutate()}
                        >
                          <Wand2 /> Renderizar todos ({liberados})
                        </Button>
                      </div>
                      {aGerar.length ? (
                        <Grade className="grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                          {aGerar.map((c) => (
                            <CartaoTrecho
                              key={c.id}
                              corte={c}
                              job={jobsDoCorte(jobs, c.id)[0]}
                              capaFonte={fonte?.miniatura}
                              onAbrir={() => onCorte(c.id)}
                            />
                          ))}
                        </Grade>
                      ) : (
                        <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                          Nenhum corte esperando: os deste vídeo já foram gerados ou descartados.
                        </p>
                      )}
                      <h3 className="pt-4 font-heading text-base font-bold">Ajustes para todos os cortes</h3>
                      <SugerirModeloComStreamer fonteId={fonteId} cortes={ativos} />
                      <div className="grid gap-4 lg:grid-cols-2">
                        <Secao icone={<Languages />} titulo="Legenda">
                          <PerguntaIdioma fonteId={fonteId} cortes={ativos} />
                        </Secao>
                        <Secao icone={<Layers />} titulo="Modelo de corte (todos)">
                          <ModeloParaTodos fonteId={fonteId} cortes={ativos} />
                        </Secao>
                      </div>
                      <Secao icone={<Layers />} titulo="Imagem de fundo">
                        <ImagemDeFundo fonteId={fonteId} cortes={ativos} />
                      </Secao>

                    </>
                  )}
                </div>
              </Painel>
            )}
          </AnimatePresence>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/** Modal de um corte (Prontos / Na fila / Descartados): o mesmo editor, com o vídeo renderizado. */
export function ModalCorte({ corteId, jobs, onFechar, onAbrirFonte }: {
  corteId: number
  jobs: Job[]
  onFechar: () => void
  onAbrirFonte: (fonteId: number) => void
}) {
  const { data: corte } = useCorte(corteId)
  return (
    <Dialog open onOpenChange={(v) => !v && onFechar()}>
      <DialogContent className={CLASSE_MODAL}>
        <div className="border-b p-5 pr-12">
          <DialogTitle asChild>
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-mono text-lg font-bold text-rosa">#{corte?.n_na_fonte}</span>
              {corte ? <TituloCompleto texto={corte.fonte_titulo} className="font-heading text-base font-bold" /> : <Skeleton className="h-5 w-72" />}
            </div>
          </DialogTitle>
          <DialogDescription asChild>
            <div className="mt-1 text-xs text-muted-foreground">
              {corte && (
                <button type="button" className="hover:text-rosa" onClick={() => onAbrirFonte(corte.fonte_id)}>
                  Ver o vídeo original e os outros cortes →
                </button>
              )}
            </div>
          </DialogDescription>
        </div>
        <div className="p-5">
          {corte ? <EditorCorte key={corte.id} corte={corte} jobs={jobsDoCorte(jobs, corte.id)} /> : <Skeleton className="h-96" />}
        </div>
      </DialogContent>
    </Dialog>
  )
}
