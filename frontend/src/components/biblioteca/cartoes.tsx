import { Clapperboard, Film, Play, ScanFace, Scissors } from 'lucide-react'
import { motion, type Variants } from 'motion/react'
import { type ReactNode, useState } from 'react'

import { urls } from '@/api/cliente'
import type { Corte, Fonte, Job } from '@/api/tipos'
import { BarraJob } from '@/components/job-progresso'
import { Plataforma } from '@/components/plataforma'
import { StatusChip } from '@/components/status-chip'
import { gerando, LIMITE_TITULO, urlMiniatura } from '@/lib/biblioteca'
import { fmtDataHora, fmtDuracao, fmtTempo } from '@/lib/formatos'
import { cn } from '@/lib/utils'

/** Grade com os cards entrando em cascata. */
export const variantesGrade: Variants = {
  oculto: {},
  visivel: { transition: { staggerChildren: 0.045 } },
}
export const variantesItem: Variants = {
  oculto: { opacity: 0, y: 16, scale: 0.97 },
  visivel: { opacity: 1, y: 0, scale: 1, transition: { type: 'spring', bounce: 0.25, duration: 0.5 } },
}

export function Grade({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div variants={variantesGrade} initial="oculto" animate="visivel" className={cn('grid gap-5', className)}>
      {children}
    </motion.div>
  )
}

/** Título completo; acima de 200 caracteres corta e mostra "ver mais". */
export function TituloCompleto({ texto, className }: { texto: string; className?: string }) {
  const [aberto, setAberto] = useState(false)
  const longo = texto.length > LIMITE_TITULO
  return (
    <p className={cn('text-sm leading-snug font-medium break-words', className)}>
      {longo && !aberto ? `${texto.slice(0, LIMITE_TITULO).trimEnd()}…` : texto}
      {longo && (
        <button
          type="button"
          className="ml-1 text-xs font-semibold text-rosa hover:underline"
          onClick={(e) => {
            e.stopPropagation()
            setAberto((x) => !x)
          }}
        >
          {aberto ? 'ver menos' : 'ver mais'}
        </button>
      )}
    </p>
  )
}

/** Imagem com fallback (miniatura remota da Twitch/YouTube pode sumir). */
function Capa({ src, className, vazio }: { src?: string | null; className?: string; vazio: ReactNode }) {
  const [falhou, setFalhou] = useState(false)
  if (!src || falhou) {
    return (
      <div className={cn('flex size-full items-center justify-center bg-gradient-to-br from-roxo/30 via-black to-rosa/20 text-white/40', className)}>
        {vazio}
      </div>
    )
  }
  return <img src={src} alt="" loading="lazy" onError={() => setFalhou(true)} className={cn('size-full object-cover', className)} />
}

/** Casca comum dos cards: elevação, borda em gradiente e brilho no hover, "press" no clique. */
function Casca({ onClick, children, className }: { onClick: () => void; children: ReactNode; className?: string }) {
  return (
    <motion.button
      type="button"
      variants={variantesItem}
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 400, damping: 28 }}
      onClick={onClick}
      className={cn('cartao-brilho group text-left outline-none focus-visible:ring-2 focus-visible:ring-ring', className)}
    >
      {children}
    </motion.button>
  )
}

/** Vídeo original na aba "Para revisar": capa + título completo + quantos cortes. */
export function CartaoFonte({ fonte, onAbrir }: { fonte: Fonte; onAbrir: () => void }) {
  const st = fonte.cortes_status ?? {} // backend antigo (sem reiniciar) não manda o campo
  const aRevisar = (st.candidato ?? 0) + (st.enquadrar ?? 0) + (st.erro ?? 0)
  return (
    <Casca onClick={onAbrir}>
      <div className="relative aspect-video overflow-hidden rounded-t-[inherit]">
        <Capa
          src={urlMiniatura(fonte.miniatura)}
          className="transition-transform duration-500 group-hover:scale-105"
          vazio={<Film className="size-10" />}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          <span className="flex items-center gap-1 rounded-full bg-black/70 px-2 py-0.5 text-[11px] font-semibold backdrop-blur">
            <Scissors className="size-3 text-rosa" /> {aRevisar} {aRevisar === 1 ? 'corte' : 'cortes'}
          </span>
          {!!st.enquadrar && (
            <span className="flex items-center gap-1 rounded-full bg-amarelo/90 px-2 py-0.5 text-[11px] font-semibold text-black">
              <ScanFace className="size-3" /> {st.enquadrar} webcam
            </span>
          )}
        </div>
        {fonte.duracao != null && (
          <span className="absolute right-2 bottom-2 rounded-md bg-black/75 px-1.5 py-0.5 font-mono text-[11px] tabular-nums">
            {fmtDuracao(fonte.duracao)}
          </span>
        )}
        <div className="absolute bottom-2 left-2 flex items-center gap-1.5 text-xs font-medium">
          <Plataforma p={fonte.plataforma} soIcone />
          {fonte.streamer_nome}
        </div>
      </div>
      <div className="space-y-1 p-3.5">
        <TituloCompleto texto={fonte.titulo} />
        {!!st.pronto && <p className="text-[11px] text-verde">{st.pronto} já pronto(s)</p>}
      </div>
    </Casca>
  )
}

/** Corte dentro do modal do vídeo original: quadro do trecho, tempo, score e status. */
export function CartaoTrecho({ corte, job, onAbrir, capaFonte }: {
  corte: Corte
  job?: Job
  onAbrir: () => void
  capaFonte?: string | null
}) {
  const capa = corte.tem_quadro ? urls.quadroCorte(corte.id, corte.atualizado_em) : urlMiniatura(capaFonte)
  return (
    <Casca onClick={onAbrir}>
      <div className="relative aspect-video overflow-hidden rounded-t-[inherit]">
        <Capa src={capa} className="transition-transform duration-500 group-hover:scale-105" vazio={<Clapperboard className="size-8" />} />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30" />
        <span className="absolute top-2 left-2 flex items-center gap-1.5 font-mono text-sm font-bold drop-shadow">
          #{corte.n_na_fonte}
          {(corte.extra as { origem?: string }).origem === 'vigia' && (
            <span className="rounded-full bg-roxo/90 px-1.5 py-0.5 font-sans text-[10px] font-semibold">
              clipe · {String((corte.sinais as { views?: number }).views ?? 0)} views
            </span>
          )}
        </span>
        <div className="absolute top-2 right-2">
          <StatusChip status={corte.status} />
        </div>
        <span className="absolute bottom-2 left-2 rounded-md bg-black/75 px-1.5 py-0.5 font-mono text-[11px] tabular-nums">
          {fmtTempo(corte.inicio)} – {fmtTempo(corte.fim)}
        </span>
        <span className="absolute right-2 bottom-2 font-mono text-[11px] font-semibold text-rosa tabular-nums">★ {corte.score.toFixed(2)}</span>
        {corte.status === 'enquadrar' && (
          <div className="absolute inset-x-0 top-1/2 flex -translate-y-1/2 justify-center">
            <span className="flex items-center gap-1 rounded-full bg-amarelo px-2.5 py-1 text-xs font-semibold text-black shadow-lg">
              <ScanFace className="size-3.5" /> marcar a webcam
            </span>
          </div>
        )}
      </div>
      <div className="space-y-2 p-3">
        <p className="line-clamp-2 text-sm">{corte.titulo || <span className="text-muted-foreground">sem título</span>}</p>
        {gerando(corte) && job && <BarraJob job={job} />}
      </div>
    </Casca>
  )
}

/** Corte renderizado (Prontos / Na fila / Descartados): vertical, toca sem som no hover. */
export function CartaoPronto({ corte, job, onAbrir }: { corte: Corte; job?: Job; onAbrir: () => void }) {
  const [hover, setHover] = useState(false)
  const temVideo = !!corte.arquivo
  const capa = temVideo
    ? urls.miniaturaCorte(corte.id, corte.atualizado_em)
    : corte.tem_quadro
      ? urls.quadroCorte(corte.id, corte.atualizado_em)
      : urlMiniatura(corte.fonte_miniatura)
  const data = corte.criado_em
  return (
    <Casca onClick={onAbrir}>
      <div
        className="relative aspect-[9/16] overflow-hidden rounded-t-[inherit] bg-black"
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        <Capa src={capa} vazio={<Clapperboard className="size-8" />} />
        {temVideo && hover && !gerando(corte) && (
          <video
            src={urls.corte(corte.id, corte.atualizado_em)}
            autoPlay
            muted
            loop
            playsInline
            className="absolute inset-0 size-full object-cover"
          />
        )}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
        {temVideo && !hover && !gerando(corte) && (
          <div className="absolute inset-0 flex items-center justify-center opacity-0 transition-opacity group-hover:opacity-100">
            <Play className="size-10 fill-white/90 text-white/90" />
          </div>
        )}
        <span className="absolute top-2 left-2 rounded-full bg-black/70 px-2 py-0.5 font-mono text-xs font-bold backdrop-blur">
          #{corte.n_na_fonte}
        </span>
        <span className="absolute top-2 right-2 rounded-md bg-black/70 px-1.5 py-0.5 font-mono text-[11px] tabular-nums">
          {fmtTempo(corte.fim - corte.inicio)}
        </span>
        {gerando(corte) && (
          <div className="absolute inset-x-3 bottom-3 space-y-1.5">
            <p className="text-xs font-medium">{corte.arquivo ? 'atualizando…' : 'renderizando…'}</p>
            {job ? <BarraJob job={job} /> : <BarraJob job={{ status: 'fila', progresso: null }} />}
          </div>
        )}
      </div>
      <div className="space-y-1 p-3">
        <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <span className="font-mono font-semibold text-rosa">#{corte.n_na_fonte}</span>
          <span>·</span>
          <span>{fmtDataHora(data)}</span>
          <span>·</span>
          <Plataforma p={corte.plataforma} soIcone />
          <span className="truncate">{corte.streamer_nome}</span>
        </p>
        <TituloCompleto texto={corte.fonte_titulo} className="text-[13px]" />
      </div>
    </Casca>
  )
}
