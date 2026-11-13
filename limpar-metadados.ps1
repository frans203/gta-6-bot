# Remove todos os metadados de videos e gera copias "novas" na pasta .\limpos
# Uso: .\limpar-metadados.ps1 video1.mp4 video2.mp4 ...
#      .\limpar-metadados.ps1 -Rapido video.mp4   (sem recodificar, mais rapido)
[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$Arquivos,
    [switch]$Rapido,
    [string]$Saida,
    [string]$Prefixo = 'gta6'
)

$ErrorActionPreference = 'Stop'
if (-not $Saida) { $Saida = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'limpos' }
New-Item -ItemType Directory -Force $Saida | Out-Null

# Proximo numero livre (gta6_001, gta6_002, ...)
$n = (Get-ChildItem $Saida -Filter "$Prefixo`_*.mp4" -ErrorAction SilentlyContinue |
      ForEach-Object { if ($_.BaseName -match "^$Prefixo`_(\d+)$") { [int]$Matches[1] } } |
      Measure-Object -Maximum).Maximum
$n = [int]$n

foreach ($arq in $Arquivos) {
    if (-not (Test-Path -LiteralPath $arq)) { Write-Warning "Nao encontrado: $arq"; continue }
    $n++
    $destino = Join-Path $Saida ('{0}_{1:D3}.mp4' -f $Prefixo, $n)
    $agora = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.000000Z')

    $comum = @(
        '-map_metadata', '-1',          # apaga metadados globais (comment, vid, md5, localizacao...)
        '-map_metadata:s', '-1',        # apaga metadados por stream
        '-map_chapters', '-1',
        '-map', '0:v:0', '-map', '0:a?', # so video + audio (descarta trilhas de dados/timecode)
        '-dn', '-sn',
        '-fflags', '+bitexact',         # nao grava "encoder=Lavf..."
        '-metadata', "creation_time=$agora",
        '-metadata:s', 'handler_name=',
        '-metadata:s', 'language=und',
        '-movflags', '+faststart'
    )

    if ($Rapido) {
        $codec = @('-c', 'copy', '-bsf:v', 'filter_units=remove_types=6')   # remove SEI do H.264
    } else {
        # Recodifica: arquivo totalmente novo (hash diferente), sem SEI do encoder original
        # Teto de bitrate = 1.4x o do original (min 1.5 Mbps): tamanho proximo do original
        $br = [double](& ffprobe -v error -select_streams v:0 -show_entries stream=bit_rate -of csv=p=0 $arq)
        if (-not $br) { $br = [double](& ffprobe -v error -show_entries format=bit_rate -of csv=p=0 $arq) }
        $teto = [int][math]::Max(1500, [math]::Min(8000, $br * 1.4 / 1000))
        $codec = @('-c:v', 'libx264', '-preset', 'slow', '-crf', '23',
                   '-maxrate', "${teto}k", '-bufsize', "$($teto * 2)k",
                   '-pix_fmt', 'yuv420p',
                   '-flags:v', '+bitexact', '-bsf:v', 'filter_units=remove_types=6',
                   '-c:a', 'aac', '-b:a', '128k', '-flags:a', '+bitexact')
    }

    Write-Host "-> $(Split-Path $arq -Leaf)  =>  $(Split-Path $destino -Leaf)"
    & ffmpeg -hide_banner -loglevel error -y -i $arq @comum @codec $destino
    if ($LASTEXITCODE -ne 0) { Write-Warning "Falhou: $arq"; continue }

    # Datas do arquivo = agora
    $item = Get-Item -LiteralPath $destino
    $item.CreationTime = $item.LastWriteTime = $item.LastAccessTime = Get-Date
}

Write-Host "`nPronto. Videos em: $Saida"
