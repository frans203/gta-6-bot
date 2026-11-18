import { Send } from 'lucide-react'
import { type ReactNode, useState } from 'react'

import { useEnviar } from '@/api/hooks/postagem'
import type { Conta, Plataforma } from '@/api/tipos'
import { EscolherPlataformas } from '@/components/escolher-plataformas'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

/** "Postar agora": um vídeo específico ou o próximo pendente de cada plataforma. Sempre pede confirmação. */
export function DialogoPostar({ conta, video, children }: { conta: Conta; video?: string; children: ReactNode }) {
  const [aberto, setAberto] = useState(false)
  const [plats, setPlats] = useState<Plataforma[]>(conta.plataformas as Plataforma[])
  const [revisar, setRevisar] = useState(false)
  const enviar = useEnviar(conta.id)

  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Postar agora</DialogTitle>
          <DialogDescription>
            {video ? (
              <>
                Vídeo <b className="text-foreground">{video}</b> na conta <b className="text-foreground">{conta.nome}</b>.
              </>
            ) : (
              <>
                O <b className="text-foreground">próximo pendente</b> de cada plataforma na conta{' '}
                <b className="text-foreground">{conta.nome}</b>.
              </>
            )}{' '}
            O Chrome do script abre e publica de verdade.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <EscolherPlataformas valor={plats} onChange={setPlats} disponiveis={conta.plataformas} />
          <Label className="flex cursor-pointer items-start gap-3 font-normal leading-snug">
            <Switch checked={revisar} onCheckedChange={setRevisar} className="mt-0.5 shrink-0" />
            <span>
              <b className="block font-semibold">Só revisar</b>
              <span className="text-xs text-muted-foreground">Preenche tudo e não publica. Feche o Chrome quando terminar.</span>
            </span>
          </Label>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setAberto(false)}>
            Cancelar
          </Button>
          <Button
            disabled={!plats.length || enviar.isPending}
            onClick={() =>
              enviar.mutate({ plataformas: plats, video: video ?? null, revisar }, { onSuccess: () => setAberto(false) })
            }
          >
            <Send /> {revisar ? 'Abrir para revisar' : 'Publicar agora'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
