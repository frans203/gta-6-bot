import { LogIn, Pencil, Plus, Star } from 'lucide-react'
import { useState } from 'react'

import { useAtualizarConta, useCriarConta, useLoginConta } from '@/api/hooks/contas'
import type { Conta, ContaIn, Plataforma as P } from '@/api/tipos'
import { Cabecalho } from '@/components/cabecalho'
import { Confirmar } from '@/components/confirmar'
import { EscolherPlataformas } from '@/components/escolher-plataformas'
import { Plataforma } from '@/components/plataforma'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useConta } from '@/lib/conta'

type Dados = Omit<ContaIn, 'tags'> & { tags: string }

function FormConta({ inicial, editando, enviando, onEnviar }: {
  inicial: Dados
  editando?: boolean
  enviando?: boolean
  onEnviar: (d: Dados) => void
}) {
  const [d, setD] = useState<Dados>(inicial)
  const idValido = /^[a-z0-9_]{2,40}$/.test(d.id)
  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault()
        onEnviar(d)
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="id">Identificador</Label>
          <Input id="id" value={d.id} disabled={editando} placeholder="gamer_en" onChange={(e) => setD({ ...d, id: e.target.value.toLowerCase() })} />
          {!editando && <p className="text-xs text-muted-foreground">Letras minúsculas, números e _ (não muda depois).</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="nome">Nome</Label>
          <Input id="nome" value={d.nome} onChange={(e) => setD({ ...d, nome: e.target.value })} placeholder="Gamer Clips EN" />
        </div>
        <div className="space-y-1.5">
          <Label>Idioma dos posts</Label>
          <Select value={d.idioma} onValueChange={(v) => setD({ ...d, idioma: v as Dados['idioma'] })}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pt">Português</SelectItem>
              <SelectItem value="en">Inglês</SelectItem>
              <SelectItem value="es">Espanhol</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Plataformas</Label>
          <EscolherPlataformas valor={d.plataformas ?? []} onChange={(p: P[]) => setD({ ...d, plataformas: p })} />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="tags">Hashtags padrão dos cortes</Label>
        <Textarea id="tags" rows={2} value={d.tags} onChange={(e) => setD({ ...d, tags: e.target.value })} placeholder="vazio = padrão do idioma" />
      </div>
      <div className="flex justify-end">
        <Button type="submit" disabled={enviando || !idValido || !d.nome.trim() || !d.plataformas?.length}>
          {editando ? 'Salvar' : 'Criar conta'}
        </Button>
      </div>
    </form>
  )
}

function DialogoConta({ conta }: { conta?: Conta }) {
  const [aberto, setAberto] = useState(false)
  const criar = useCriarConta()
  const atualizar = useAtualizarConta()
  const inicial: Dados = conta
    ? { id: conta.id, nome: conta.nome, idioma: conta.idioma as Dados['idioma'], plataformas: conta.plataformas as P[], tags: conta.tags }
    : { id: '', nome: '', idioma: 'en', plataformas: ['tiktok', 'youtube', 'instagram'], tags: '' }
  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <DialogTrigger asChild>
        {conta ? (
          <Button size="sm" variant="ghost">
            <Pencil /> Editar
          </Button>
        ) : (
          <Button>
            <Plus /> Nova conta
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{conta ? `Editar ${conta.nome}` : 'Nova conta'}</DialogTitle>
          <DialogDescription>
            Uma conta = um perfil do Chrome próprio (logado nas redes dela) + uma pasta de vídeos. Deixe a interface das redes em
            português, mesmo postando em inglês (o script procura os textos em PT).
          </DialogDescription>
        </DialogHeader>
        <FormConta
          key={String(aberto)}
          inicial={inicial}
          editando={!!conta}
          enviando={criar.isPending || atualizar.isPending}
          onEnviar={(d) => {
            const fechar = { onSuccess: () => setAberto(false) }
            if (conta) atualizar.mutate({ id: conta.id, body: { nome: d.nome, idioma: d.idioma, plataformas: d.plataformas, tags: d.tags } }, fechar)
            else criar.mutate({ ...d, tags: d.tags.trim() || null }, fechar)
          }}
        />
      </DialogContent>
    </Dialog>
  )
}

export function PaginaContas() {
  const { contas, conta: atual, setContaId } = useConta()
  const login = useLoginConta()
  return (
    <>
      <Cabecalho titulo="Contas" descricao="Cada conta posta nas próprias redes, com perfil do Chrome e fila separados.">
        <DialogoConta />
      </Cabecalho>
      <div className="grid gap-4 lg:grid-cols-2">
        {contas.map((c) => (
          <Card key={c.id} className={c.id === atual?.id ? 'ring-rosa/60' : undefined}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {c.nome}
                {c.padrao && <Star className="size-4 fill-amarelo text-amarelo" aria-label="conta principal" />}
                <Badge variant="secondary">{c.idioma.toUpperCase()}</Badge>
              </CardTitle>
              <CardDescription>{c.id}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex flex-wrap gap-3">
                {c.plataformas.map((p) => (
                  <Plataforma key={p} p={p} />
                ))}
              </div>
              <dl className="grid grid-cols-[80px_1fr] gap-x-2 gap-y-1 text-xs">
                <dt className="text-muted-foreground">Vídeos</dt>
                <dd className="truncate font-mono" title={c.pasta}>{c.pasta}</dd>
                <dt className="text-muted-foreground">Perfil</dt>
                <dd className="truncate font-mono" title={c.perfil}>{c.perfil}</dd>
                <dt className="text-muted-foreground">Tags</dt>
                <dd className="line-clamp-2">{c.tags || '—'}</dd>
              </dl>
              <div className="flex flex-wrap gap-2 border-t pt-3">
                {c.id !== atual?.id && (
                  <Button size="sm" variant="outline" onClick={() => setContaId(c.id)}>
                    Usar esta conta
                  </Button>
                )}
                <Confirmar
                  titulo={`Abrir o Chrome da conta ${c.nome}?`}
                  descricao="Abre um Chrome normal (sem automação) com as páginas de login. Faça login em cada aba e depois FECHE o Chrome inteiro, senão os envios falham (o perfil só pode ser usado por um processo)."
                  confirmar="Abrir Chrome"
                  onConfirmar={() => login.mutate(c.id)}
                >
                  <Button size="sm" variant="outline">
                    <LogIn /> Login nas redes
                  </Button>
                </Confirmar>
                <DialogoConta conta={c} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  )
}
