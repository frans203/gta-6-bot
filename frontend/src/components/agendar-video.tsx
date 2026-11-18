import { CalendarClock, Loader2, Monitor, Star, Undo2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { useJob } from '@/api/hooks/jobs'
import { useAgendarVideo, useApagarPost, useHorariosSugeridos, type ItemAgendar } from '@/api/hooks/postagem'
import type { Conta, Plataforma as Rede, Post, Video } from '@/api/tipos'
import { ProgressoJob } from '@/components/job-progresso'
import { Plataforma } from '@/components/plataforma'
import { StatusChip } from '@/components/status-chip'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { agruparPorDia, chaveDia, fmtDataHora, fmtDia, fmtHora } from '@/lib/formatos'
import { cn } from '@/lib/utils'

/** Status que já resolvem a rede (servicos/agenda.py: FEITO). */
const FEITO = ['publicado', 'agendado', 'agendado_pc', 'pulado_reivindicacao', 'removido']

const NOME_REDE: Record<string, string> = { youtube: 'Shorts', instagram: 'Reels' }

/** Data local sem fuso, no formato que o backend espera ("2026-11-18T20:30:00"). */
function isoLocal(d: Date) {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:00`
}

/** Valor do <input type="datetime-local"> → horário com minuto múltiplo de 5 (exigência do TikTok). */
function arredondar5(valor: string) {
  const d = new Date(valor)
  if (Number.isNaN(d.getTime())) return null
  d.setMinutes(Math.round(d.getMinutes() / 5) * 5, 0, 0)
  return isoLocal(d)
}

function rotuloDia(chave: string) {
  const hoje = chaveDia(new Date())
  const amanha = chaveDia(new Date(Date.now() + 86_400_000))
  if (chave === hoje) return 'Hoje'
  if (chave === amanha) return 'Amanhã'
  return fmtDia(`${chave}T12:00:00`)
}

/**
 * Agendar UM vídeo com um horário próprio em cada rede. As sugestões vêm da grade do horarios.json
 * (★ = horário de pico); dá para escolher outro horário à mão ou não agendar numa rede.
 */
export function AgendarVideo({ conta, video, postDe }: {
  conta: Conta
  video: Video
  postDe: (rede: string) => Post | undefined
}) {
  const { data, isLoading } = useHorariosSugeridos(conta.id)
  const agendar = useAgendarVideo(conta.id, video.video)
  const desmarcar = useApagarPost()
  const [jobId, setJobId] = useState<number | null>(null)
  const { data: job } = useJob(jobId)
  // undefined = ainda não mexeu (vale a sugestão automática); null = "não agendar"
  const [escolha, setEscolha] = useState<Record<string, string | null | undefined>>({})

  if (isLoading || !data) return <Skeleton className="h-96" />

  const redes = conta.plataformas as Rede[]
  const pendentes = redes.filter((r) => !FEITO.includes(video.plataformas[r]?.status ?? 'pendente'))

  /** Sugestão automática: o 1º horário de pico livre; senão o 1º livre. */
  const automatico = (r: string) => {
    const livres = (data.redes[r] ?? []).filter((h) => h.disponivel && !h.ocupado_por)
    return (livres.find((h) => h.destaque) ?? livres[0])?.quando ?? null
  }
  const valor = (r: string) => (escolha[r] === undefined ? automatico(r) : escolha[r])
  const itens: ItemAgendar[] = pendentes.flatMap((r) => {
    const q = valor(r)
    return q ? [{ plataforma: r, quando: q }] : []
  })

  return (
    <div className="space-y-5">
      <div className="grid gap-3 lg:grid-cols-3">
        {redes.map((r) => {
          const estado = video.plataformas[r] ?? { status: 'pendente' }
          const feito = FEITO.includes(estado.status)
          const post = postDe(r)
          const sugestoes = data.redes[r] ?? []
          const atual = valor(r)
          const manual = atual && !sugestoes.some((h) => h.quando === atual) ? atual : null
          return (
            <div key={r} className="flex flex-col gap-3 rounded-xl border bg-white/[0.02] p-3">
              <div className="flex items-center justify-between gap-2">
                <Plataforma p={r} />
                <span className="text-[11px] text-muted-foreground">{NOME_REDE[r]}</span>
              </div>

              {feito ? (
                <div className="space-y-2 text-sm">
                  <StatusChip status={estado.status} />
                  {estado.para && estado.status !== 'publicado' && (
                    <p className="text-xs text-muted-foreground tabular-nums">para {fmtDataHora(estado.para)}</p>
                  )}
                  {estado.status === 'agendado_pc' && post ? (
                    <Button size="xs" variant="outline" disabled={desmarcar.isPending} onClick={() => desmarcar.mutate(post.id)}>
                      <Undo2 /> Desmarcar
                    </Button>
                  ) : estado.status === 'agendado' ? (
                    <p className="text-[11px] text-muted-foreground">
                      Para mudar o horário, edite direto no {r === 'youtube' ? 'YouTube Studio' : 'TikTok'}.
                    </p>
                  ) : null}
                </div>
              ) : (
                <>
                  <div className="max-h-80 space-y-3 overflow-y-auto pr-1">
                    {agruparPorDia(sugestoes, (h) => h.quando).map(([dia, lista]) => (
                      <div key={dia} className="space-y-1.5">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{rotuloDia(dia)}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {lista.map((h) => {
                            const sel = atual === h.quando
                            return (
                              <button
                                key={h.quando}
                                type="button"
                                disabled={!h.disponivel}
                                title={
                                  !h.disponivel
                                    ? `perto demais de agora (mínimo ${data.antecedencia_min} min)`
                                    : h.ocupado_por
                                      ? `já tem ${h.ocupado_por} nesse horário`
                                      : h.destaque
                                        ? 'horário de pico'
                                        : undefined
                                }
                                onClick={() => setEscolha((e) => ({ ...e, [r]: h.quando }))}
                                className={cn(
                                  'inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-sm tabular-nums transition',
                                  'hover:border-rosa/60 hover:bg-rosa/10 disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-transparent',
                                  sel && 'border-rosa bg-rosa/20 text-foreground ring-1 ring-rosa/60',
                                  h.ocupado_por && !sel && 'border-dashed text-muted-foreground',
                                )}
                              >
                                {fmtHora(h.quando)}
                                {h.destaque && <Star className="size-3 fill-amarelo text-amarelo" />}
                                {h.ocupado_por && <span className="text-[10px] text-amarelo">ocupado</span>}
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    ))}
                    {!sugestoes.length && <p className="text-xs text-muted-foreground">Sem horários na grade.</p>}
                  </div>

                  <div className="space-y-1.5 border-t pt-3">
                    <label className="text-[11px] text-muted-foreground" htmlFor={`outro-${r}`}>
                      Outro horário
                    </label>
                    <Input
                      id={`outro-${r}`}
                      type="datetime-local"
                      step={300}
                      value={manual ? manual.slice(0, 16) : ''}
                      onChange={(e) => setEscolha((x) => ({ ...x, [r]: arredondar5(e.target.value) }))}
                      className={cn(manual && 'border-rosa ring-1 ring-rosa/60')}
                    />
                    <button
                      type="button"
                      onClick={() => setEscolha((e) => ({ ...e, [r]: null }))}
                      className={cn(
                        'w-full rounded-lg border px-2.5 py-1 text-xs transition hover:bg-white/5',
                        atual === null && 'border-white/40 bg-white/10',
                      )}
                    >
                      Não agendar nesta rede
                    </button>
                  </div>
                  {r === 'instagram' && (
                    <p className="flex gap-1.5 text-[11px] text-amarelo">
                      <Monitor className="mt-px size-3.5 shrink-0" />
                      Quem posta o Instagram no horário é o {data.sistema_local}: o computador precisa estar ligado.
                    </p>
                  )}
                </>
              )}
            </div>
          )
        })}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rosa/30 bg-rosa/5 p-3">
        <div className="min-w-0 text-sm">
          {itens.length ? (
            <ul className="flex flex-wrap gap-x-4 gap-y-1">
              {itens.map((i) => (
                <li key={i.plataforma} className="flex items-center gap-1.5">
                  <Plataforma p={i.plataforma} soIcone /> <span className="tabular-nums">{fmtDataHora(i.quando)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <span className="text-muted-foreground">
              {pendentes.length ? 'Escolha um horário em pelo menos uma rede.' : 'Este vídeo já está resolvido em todas as redes.'}
            </span>
          )}
          <p className="mt-1 text-[11px] text-muted-foreground">
            ★ horário de pico · mínimo de {data.antecedencia_min} min de antecedência · minutos múltiplos de 5
          </p>
        </div>
        <Button
          className="botao-brilho"
          disabled={!itens.length || agendar.isPending}
          onClick={() => agendar.mutate(itens, { onSuccess: (j) => setJobId(j.id) })}
        >
          {agendar.isPending ? <Loader2 className="animate-spin" /> : <CalendarClock />} Agendar
        </Button>
      </div>

      {job && (
        <div className="space-y-1.5 rounded-xl border p-3">
          <ProgressoJob job={job} />
          <p className="text-[11px] text-muted-foreground">
            O Chrome do script abre e agenda em cada rede.{' '}
            <Link to={`/jobs?job=${job.id}`} className="text-rosa hover:underline">
              ver o job #{job.id}
            </Link>
          </p>
        </div>
      )}
    </div>
  )
}
