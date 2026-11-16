/** Cores e rótulos de status (mesmas cores do CLI jason.py). */

export const ROTULO_STATUS: Record<string, string> = {
  publicado: 'publicado',
  agendado: 'agendado',
  agendado_pc: 'agendado (PC)',
  pendente: 'pendente',
  erro: 'erro',
  nao_logado: 'sem login',
  revisar: 'revisar',
  pulado_reivindicacao: 'pulado (Content ID)',
  limite_diario: 'limite diário',
  atrasado: 'atrasado',
  fila_vazia: 'fila vazia',
  // jobs
  fila: 'na fila',
  rodando: 'rodando',
  ok: 'ok',
  cancelando: 'cancelando',
  cancelado: 'cancelado',
  // cortes / fontes
  candidato: 'candidato',
  enquadrar: 'marcar webcam',
  aprovado: 'aprovado',
  renderizando: 'renderizando',
  pronto: 'pronto',
  na_fila: 'na fila de postagem',
  descartado: 'descartado',
  nova: 'nova',
  analisando: 'analisando',
  analisada: 'analisada',
}

const VERDE = 'bg-verde/15 text-verde border-verde/40'
const ROSA = 'bg-rosa/15 text-rosa border-rosa/40'
const LARANJA = 'bg-laranja/15 text-laranja border-laranja/40'
const CIANO = 'bg-ciano/15 text-ciano border-ciano/40'
const AMARELO = 'bg-amarelo/15 text-amarelo border-amarelo/40'
const ROXO = 'bg-roxo/20 text-[#d9a6ff] border-roxo/50'
const VERMELHO = 'bg-destructive/15 text-destructive border-destructive/40'
const CINZA = 'bg-muted text-muted-foreground border-border'

export const COR_STATUS: Record<string, string> = {
  publicado: VERDE,
  ok: VERDE,
  pronto: VERDE,
  analisada: VERDE,
  agendado: ROSA,
  na_fila: ROSA,
  agendado_pc: LARANJA,
  aprovado: LARANJA,
  enquadrar: AMARELO,
  pendente: CINZA,
  fila: CINZA,
  nova: CINZA,
  candidato: CIANO,
  revisar: CIANO,
  rodando: CIANO,
  renderizando: CIANO,
  analisando: CIANO,
  erro: VERMELHO,
  nao_logado: VERMELHO,
  atrasado: VERMELHO,
  limite_diario: AMARELO,
  pulado_reivindicacao: AMARELO,
  cancelando: AMARELO,
  cancelado: CINZA,
  descartado: CINZA,
  fila_vazia: CINZA,
}

export const corStatus = (s: string) => COR_STATUS[s] ?? ROXO
export const rotuloStatus = (s: string) => ROTULO_STATUS[s] ?? s.replaceAll('_', ' ')
