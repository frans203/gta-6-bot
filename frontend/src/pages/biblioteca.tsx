import { CheckCircle2, Clapperboard, Library, ListVideo, Scissors, Trash2 } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { Link, useSearchParams } from 'react-router'

import { useCortes, useFontesComCortes, useStreamers } from '@/api/hooks/cortador'
import { useJobs } from '@/api/hooks/jobs'
import { AbasAnimadas } from '@/components/abas-animadas'
import { CartaoFonte, CartaoPronto, Grade } from '@/components/biblioteca/cartoes'
import { ModalCorte, ModalFonte } from '@/components/biblioteca/modais'
import { Cabecalho, Vazio } from '@/components/cabecalho'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { ABAS_BIBLIOTECA, type AbaBiblioteca, jobsDoCorte } from '@/lib/biblioteca'

const ICONES = { revisar: Scissors, prontos: CheckCircle2, fila: ListVideo, descartados: Trash2 }

function GradeCarregando({ vertical }: { vertical?: boolean }) {
  return (
    <div className={vertical ? 'grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5' : 'grid gap-5 sm:grid-cols-2 xl:grid-cols-3'}>
      {Array.from({ length: vertical ? 10 : 6 }, (_, i) => (
        <Skeleton key={i} className={vertical ? 'aspect-[9/16] rounded-2xl' : 'aspect-[4/3] rounded-2xl'} />
      ))}
    </div>
  )
}

/**
 * Biblioteca de cortes.
 *  - Para revisar: um card por vídeo original; o modal mostra os cortes que podem ser gerados dele.
 *  - Prontos / Na fila / Descartados: um card por corte (vertical, toca no hover).
 * Estado na URL: ?aba=prontos&fonte=12&corte=34 (dá para voltar, recarregar e mandar o link).
 */
export function PaginaBiblioteca() {
  const [params, setParams] = useSearchParams()
  const aba = ((params.get('aba') ?? 'revisar') in ABAS_BIBLIOTECA ? (params.get('aba') ?? 'revisar') : 'revisar') as AbaBiblioteca
  const fonteId = params.get('fonte') ? Number(params.get('fonte')) : null
  const corteId = params.get('corte') ? Number(params.get('corte')) : null
  const streamerId = params.get('streamer') ? Number(params.get('streamer')) : undefined

  const { data: streamers = [] } = useStreamers()
  const statusAba = [...ABAS_BIBLIOTECA[aba].status]
  const fontes = useFontesComCortes([...ABAS_BIBLIOTECA.revisar.status])
  const cortes = useCortes({ status: aba === 'revisar' ? ['__nenhum__'] : statusAba, streamer_id: streamerId })
  const { data: jobs = [] } = useJobs({ status: 'fila,rodando', tipo: 'renderizar_corte,enquadrar_corte' })

  const listaFontes = (fontes.data ?? []).filter((f) => !streamerId || f.streamer_id === streamerId)
  const listaCortes = aba === 'revisar' ? [] : (cortes.data ?? [])

  const mudar = (mudancas: Record<string, string | number | null | undefined>) => {
    const p = new URLSearchParams(params)
    for (const [k, v] of Object.entries(mudancas)) {
      if (v == null || v === '') p.delete(k)
      else p.set(k, String(v))
    }
    setParams(p)
  }

  return (
    <>
      <Cabecalho
        titulo="Biblioteca"
        descricao="Vídeos originais esperando revisão e os cortes já gerados. Clique para ver, ajustar a cara do streamer e renderizar."
      >
        <Select value={streamerId ? String(streamerId) : 'todos'} onValueChange={(x) => mudar({ streamer: x === 'todos' ? null : x })}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os streamers</SelectItem>
            {streamers.map((s) => (
              <SelectItem key={s.id} value={String(s.id)}>
                {s.nome}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button asChild className="botao-brilho">
          <Link to="/cortador/novo">
            <Scissors /> Cortar vídeo
          </Link>
        </Button>
      </Cabecalho>

      <AbasAnimadas
        className="mb-6"
        valor={aba}
        onChange={(x) => mudar({ aba: x === 'revisar' ? null : x })}
        abas={(Object.keys(ABAS_BIBLIOTECA) as AbaBiblioteca[]).map((k) => ({
          id: k,
          rotulo: ABAS_BIBLIOTECA[k].rotulo,
          Icone: ICONES[k],
          contagem: k === 'revisar' ? listaFontes.length : k === aba ? listaCortes.length : undefined,
        }))}
      />

      <AnimatePresence mode="wait">
        <motion.div
          key={aba}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {aba === 'revisar' ? (
            fontes.isLoading ? (
              <GradeCarregando />
            ) : listaFontes.length ? (
              <Grade className="sm:grid-cols-2 xl:grid-cols-3">
                {listaFontes.map((f) => (
                  <CartaoFonte key={f.id} fonte={f} onAbrir={() => mudar({ fonte: f.id, corte: null })} />
                ))}
              </Grade>
            ) : (
              <Vazio icone={<Library />} titulo="Nada para revisar">
                Cole o link de uma live ou VOD em <Link to="/cortador/novo" className="text-rosa hover:underline">Cortar vídeo</Link>: os
                melhores trechos aparecem aqui.
              </Vazio>
            )
          ) : cortes.isLoading ? (
            <GradeCarregando vertical />
          ) : listaCortes.length ? (
            <Grade className="grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {listaCortes.map((c) => (
                <CartaoPronto key={c.id} corte={c} job={jobsDoCorte(jobs, c.id)[0]} onAbrir={() => mudar({ corte: c.id, fonte: null })} />
              ))}
            </Grade>
          ) : (
            <Vazio icone={<Clapperboard />} titulo="Nenhum corte aqui">
              {aba === 'prontos' && 'Renderize os cortes de um vídeo na aba “Para revisar”.'}
            </Vazio>
          )}
        </motion.div>
      </AnimatePresence>

      {fonteId != null && (
        <ModalFonte
          fonteId={fonteId}
          corteId={corteId}
          jobs={jobs}
          onCorte={(id) => mudar({ corte: id })}
          onFechar={() => mudar({ fonte: null, corte: null })}
        />
      )}
      {fonteId == null && corteId != null && (
        <ModalCorte
          corteId={corteId}
          jobs={jobs}
          onFechar={() => mudar({ corte: null })}
          onAbrirFonte={(f) => mudar({ aba: null, corte: null, fonte: f })}
        />
      )}
    </>
  )
}
