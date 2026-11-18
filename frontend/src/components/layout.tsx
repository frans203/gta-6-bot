import { Cog, LayoutDashboard, LayoutTemplate, Library, ListVideo, Menu, Scissors, ScrollText, Users } from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router'

import { useConectado, useEventos } from '@/api/eventos'
import { useSistema } from '@/api/hooks/contas'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { useConta } from '@/lib/conta'
import { cn } from '@/lib/utils'

const MENU = [
  { para: '/', rotulo: 'Painel', Icone: LayoutDashboard },
  { para: '/cortador/novo', rotulo: 'Cortar vídeo', Icone: Scissors },
  { para: '/biblioteca', rotulo: 'Biblioteca', Icone: Library },
  { para: '/fila', rotulo: 'Fila', Icone: ListVideo },
  { para: '/cortador/modelos', rotulo: 'Modelos de corte', Icone: LayoutTemplate },
  { para: '/contas', rotulo: 'Contas', Icone: Users },
  { para: '/jobs', rotulo: 'Jobs', Icone: Cog },
  { para: '/logs', rotulo: 'Logs', Icone: ScrollText },
]

function Logo() {
  return (
    <div className="flex items-center gap-3 px-3">
      <motion.div
        className="relative grid size-10 place-items-center rounded-xl bg-gradient-to-br from-roxo to-rosa shadow-[0_0_24px_-4px] shadow-rosa/70"
        whileHover={{ rotate: -8, scale: 1.06 }}
        transition={{ type: 'spring', stiffness: 400, damping: 15 }}
      >
        <span className="font-heading text-xl font-extrabold text-white">J</span>
      </motion.div>
      <div className="leading-none">
        <div className="texto-gradiente font-heading text-2xl font-extrabold tracking-tight">jason</div>
        <div className="mt-1 text-[10px] font-medium tracking-[0.25em] text-muted-foreground uppercase">cortes · postagem</div>
      </div>
    </div>
  )
}

function SeletorConta() {
  const { contas, conta, setContaId } = useConta()
  if (!conta) return null
  return (
    <div className="space-y-1.5 px-2">
      <div className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Conta</div>
      <Select value={conta.id} onValueChange={setContaId}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {contas.map((c) => (
            <SelectItem key={c.id} value={c.id}>
              {c.nome} <span className="text-muted-foreground">· {c.idioma.toUpperCase()}</span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function Indicadores() {
  const conectado = useConectado()
  const { data: sis } = useSistema()
  const ponto = (ok: boolean | undefined) =>
    cn('size-2 rounded-full', ok ? 'animate-pulse bg-verde shadow-[0_0_8px] shadow-verde' : 'bg-destructive')
  return (
    <div className="space-y-1 px-2 text-xs text-muted-foreground">
      <div className="flex items-center gap-2" title="Conexão de tempo real com o backend (SSE)">
        <span className={ponto(conectado)} /> {conectado ? 'tempo real conectado' : 'sem conexão com a API'}
      </div>
      <div className="flex items-center gap-2" title="Processo que executa os jobs (python jason.py worker)">
        <span className={ponto(sis?.worker_ativo)} /> {sis?.worker_ativo ? 'worker rodando' : 'worker parado'}
      </div>
      {sis && <div className="pt-1 text-[10px] opacity-70">v{sis.versao}</div>}
    </div>
  )
}

function Navegacao({ onNavegar, id }: { onNavegar?: () => void; id: string }) {
  return (
    <nav className="flex flex-col gap-1">
      {MENU.map(({ para, rotulo, Icone }) => (
        <NavLink
          key={para}
          to={para}
          end={para === '/'}
          onClick={onNavegar}
          className={({ isActive }) =>
            cn(
              'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
              isActive ? 'text-white' : 'text-sidebar-foreground/70 hover:bg-white/[0.04] hover:text-white',
            )
          }
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <motion.span
                  layoutId={`menu-ativo-${id}`}
                  className="absolute inset-0 rounded-xl border border-white/10 bg-gradient-to-r from-roxo/30 via-roxo/10 to-transparent shadow-[inset_2px_0_0] shadow-rosa"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.45 }}
                />
              )}
              <Icone
                className={cn(
                  'relative size-4 transition-all duration-200 group-hover:scale-110',
                  isActive ? 'text-rosa drop-shadow-[0_0_6px_var(--vc-rosa)]' : 'group-hover:text-ciano',
                )}
              />
              <span className="relative transition-transform duration-200 group-hover:translate-x-0.5">{rotulo}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

function ConteudoLateral({ onNavegar, id }: { onNavegar?: () => void; id: string }) {
  return (
    <div className="flex h-full flex-col gap-6 py-5">
      <Logo />
      <SeletorConta />
      <div className="px-1">
        <Navegacao onNavegar={onNavegar} id={id} />
      </div>
      <div className="mt-auto">
        <Indicadores />
      </div>
    </div>
  )
}

/** Casca da aplicação: barra lateral (gaveta no celular) + conteúdo. Também liga o tempo real (SSE). */
export function Layout() {
  useEventos()
  const [aberto, setAberto] = useState(false)
  const { pathname } = useLocation()
  return (
    <div className="fundo-app relative min-h-svh">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 border-r border-sidebar-border bg-sidebar/80 px-2 backdrop-blur-xl lg:block">
        <ConteudoLateral id="lateral" />
      </aside>
      <header className="sticky top-0 z-30 flex items-center gap-3 border-b bg-background/80 px-4 py-2 backdrop-blur lg:hidden">
        <Sheet open={aberto} onOpenChange={setAberto}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Abrir menu">
              <Menu />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 bg-sidebar p-2">
            <SheetTitle className="sr-only">Menu</SheetTitle>
            <ConteudoLateral onNavegar={() => setAberto(false)} id="gaveta" />
          </SheetContent>
        </Sheet>
        <span className="texto-gradiente font-heading text-xl font-extrabold tracking-tight">jason</span>
      </header>
      <main className="relative z-10 px-4 py-6 lg:ml-60 lg:px-8 lg:py-8">
        {/* cada página entra com um leve deslize + desfoque */}
        <motion.div
          key={pathname}
          className="mx-auto max-w-7xl"
          initial={{ opacity: 0, y: 12, filter: 'blur(6px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <Outlet />
        </motion.div>
      </main>
    </div>
  )
}
