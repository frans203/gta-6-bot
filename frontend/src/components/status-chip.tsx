import { Badge } from '@/components/ui/badge'
import { corStatus, rotuloStatus } from '@/lib/status'
import { cn } from '@/lib/utils'

/** Etiqueta colorida de status (post, job, corte, fonte). */
export function StatusChip({ status, className }: { status: string; className?: string }) {
  return (
    <Badge variant="outline" className={cn('font-medium whitespace-nowrap', corStatus(status), className)}>
      {rotuloStatus(status)}
    </Badge>
  )
}
