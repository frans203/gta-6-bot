import { CalendarClock, Clapperboard, Cog, LayoutDashboard, LayoutTemplate, Link2, ListVideo, Menu, Scissors, ScrollText, Users } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router'

import { useConectado, useEventos } from '@/api/eventos'
import { useSistema } from '@/api/hooks/contas'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { useConta } from '@/lib/conta'
import { cn } from '@/lib/utils'

const MENU = [
  { para: '/', rotulo: 'Painel', Icone: LayoutDashboard },
  { para: '/fila', rotulo: 'Fila', Icone: ListVideo },
  { para: '/agenda', rotulo: 'Agenda', Icone: CalendarClock },
  { para: '/cortador/novo', rotulo: 'Cortar vídeo', Icone: Link2 },
  { para: '/cortador', rotulo: 'Streamers', Icone: Scissors, fim: true },
  { para: '/cortador/cortes', rotulo: 'Revisar cortes', Icone: Clapperboard },
  { para: '/cortador/modelos', rotulo: 'Modelos de corte', Icone: LayoutTemplate },
  { para: '/jobs', rotulo: 'Jobs', Icone: Cog },
  { para: '/logs', rotulo: 'Logs', Icone: ScrollText },
  { para: '/contas', rotulo: 'Contas', Icone: Users },
]

function Logo() {
  return (
    <div className="px-2">
      <div className="texto-sunset font-heading text-3xl font-black tracking-[0.2em]">JASON</div>
      <div className="text-[10px] font-semibold tracking-[0.35em] text-ciano">GTA VI · PIPELINE</div>
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
  const ponto = (ok: boolean | undefined) => cn('size-2 rounded-full', ok ? 'bg-verde shadow-[0_0_8px] shadow-verde' : 'bg-destructive')
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

function Navegacao({ onNavegar }: { onNavegar?: () => void }) {
  return (
    <nav className="flex flex-col gap-0.5">
      {MENU.map(({ para, rotulo, Icone, fim }) => (
        <NavLink
          key={para}
          to={para}
          end={para === '/' || fim}
          onClick={onNavegar}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
              isActive && 'bg-sidebar-accent text-white shadow-[inset_3px_0_0] shadow-rosa',
            )
          }
        >
          <Icone className="size-4" />
          {rotulo}
        </NavLink>
      ))}
    </nav>
  )
}

function ConteudoLateral({ onNavegar }: { onNavegar?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-6 py-5">
      <Logo />
      <SeletorConta />
      <div className="px-2">
        <Navegacao onNavegar={onNavegar} />
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
  return (
    <div className="fundo-vice min-h-svh">
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-sidebar-border bg-sidebar/95 px-2 lg:block">
        <ConteudoLateral />
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
            <ConteudoLateral onNavegar={() => setAberto(false)} />
          </SheetContent>
        </Sheet>
        <span className="texto-sunset font-heading text-xl font-black tracking-[0.2em]">JASON</span>
      </header>
      <main className="px-4 py-6 lg:ml-60 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
