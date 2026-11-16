import type { ReactNode } from 'react'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'

interface Props {
  titulo: string
  descricao?: ReactNode
  confirmar?: string
  perigoso?: boolean
  onConfirmar: () => void
  /** Elemento que abre a confirmação (botão). */
  children: ReactNode
}

/** Pede confirmação antes de ações com efeito real (postar, agendar, apagar). */
export function Confirmar({ titulo, descricao, confirmar = 'Confirmar', perigoso, onConfirmar, children }: Props) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>{children}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{titulo}</AlertDialogTitle>
          {descricao && <AlertDialogDescription asChild><div>{descricao}</div></AlertDialogDescription>}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction variant={perigoso ? 'destructive' : 'default'} onClick={onConfirmar}>
            {confirmar}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
