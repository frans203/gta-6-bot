import { createBrowserRouter } from 'react-router'

import { Layout } from '@/components/layout'
import { NaoEncontrada } from '@/pages/nao-encontrada'
import { PaginaPainel } from '@/pages/painel'

/** Carrega a página só quando a rota é aberta (bundle menor). */
const pagina = (carregar: () => Promise<React.ComponentType>) => async () => ({ Component: await carregar() })

/** Rotas da aplicação. Página nova = um arquivo em src/pages + uma linha aqui + item no MENU do layout. */
export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <PaginaPainel /> },
      { path: '/fila', lazy: pagina(async () => (await import('@/pages/fila')).PaginaFila) },
      { path: '/agenda', lazy: pagina(async () => (await import('@/pages/agenda')).PaginaAgenda) },
      { path: '/cortador', lazy: pagina(async () => (await import('@/pages/cortador')).PaginaCortador) },
      { path: '/cortador/streamers/:id', lazy: pagina(async () => (await import('@/pages/streamer')).PaginaStreamer) },
      { path: '/cortador/novo', lazy: pagina(async () => (await import('@/pages/cortar-video')).PaginaCortarVideo) },
      { path: '/cortador/modelos', lazy: pagina(async () => (await import('@/pages/modelos')).PaginaModelos) },
      { path: '/cortador/cortes', lazy: pagina(async () => (await import('@/pages/cortes')).PaginaCortes) },
      { path: '/jobs', lazy: pagina(async () => (await import('@/pages/jobs')).PaginaJobs) },
      { path: '/logs', lazy: pagina(async () => (await import('@/pages/logs')).PaginaLogs) },
      { path: '/contas', lazy: pagina(async () => (await import('@/pages/contas')).PaginaContas) },
      { path: '*', element: <NaoEncontrada /> },
    ],
  },
])
