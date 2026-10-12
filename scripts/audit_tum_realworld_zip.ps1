# Read-only TUM CAN archive inventory.
# Windows PowerShell 5.1; no Python, no extraction and no external dependencies.
[CmdletBinding()]
param(
  [string]$Archive = (Join-Path $HOME 'Downloads\m1774217_001.zip'),
  [string]$Output = (Join-Path $HOME 'Downloads\TUM_RealWorld_Audit'),
  [int]$MaxHeaderExamples = 8
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

if (-not (Test-Path -LiteralPath $Archive -PathType Leaf)) {
  throw "ZIP nao encontrado: $Archive"
}
$archiveFile = (Resolve-Path -LiteralPath $Archive).ProviderPath
$dest = [IO.Path]::GetFullPath($Output)
$repo = [IO.Path]::GetFullPath((Join-Path $HOME 'Downloads\Project-Taycan')).TrimEnd([char]'\', [char]'/')
if ($dest.Equals($repo, [StringComparison]::OrdinalIgnoreCase) -or
  $dest.StartsWith($repo+[IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
  throw 'Escolha uma pasta de saida fora do repositorio GitHub.'
}
if (-not (Test-Path -LiteralPath $dest)) {
  New-Item -ItemType Directory -Path $dest -Force | Out-Null
}
$checksum = (Get-FileHash -LiteralPath $archiveFile -Algorithm SHA256).Hash
$zip = [IO.Compression.ZipFile]::OpenRead($archiveFile)
$files = New-Object 'System.Collections.Generic.List[object]'
$headers = New-Object 'System.Collections.Generic.List[object]'
$failedHeaders = 0
try {
  foreach ($e in $zip.Entries) {
    if ($e.Name -eq '') { continue }
    $ext = [IO.Path]::GetExtension($e.FullName).ToLowerInvariant()
    $files.Add([pscustomobject]@{
      path_in_zip = $e.FullName
      extension = $ext
      uncompressed_bytes = $e.Length
      compressed_bytes = $e.CompressedLength
      last_write_time = $e.LastWriteTime.ToString('o')
    })
    if ($headers.Count -ge $MaxHeaderExamples) { continue }
    if (@('.csv','.tsv','.txt') -notcontains $ext) { continue }
    if ($e.Length -eq 0) { continue }
    $s=$null; $r=$null
    try {
      $s=$e.Open()
      $r=New-Object System.IO.StreamReader($s)
      $first=$r.ReadLine()
      $second=$r.ReadLine()
      if ($null -ne $first -and $first.Length -gt 500) { $first=$first.Substring(0,500) }
      if ($null -ne $second -and $second.Length -gt 500) { $second=$second.Substring(0,500) }
      $headers.Add([pscustomobject]@{
        path_in_zip=$e.FullName
        first_line=$first
        second_line=$second
      })
    } catch {
      $failedHeaders++
      Write-Warning "Leitura de amostra falhou: $($e.FullName)"
    } finally {
      if ($null -ne $r) { $r.Dispose() }
      elseif ($null -ne $s) { $s.Dispose() }
    }
  }
} finally {
  $zip.Dispose()
}
$manifest=Join-Path $dest 'TUM_ZIP_ENTRIES.csv'
$files | Export-Csv -LiteralPath $manifest -NoTypeInformation -Encoding UTF8
$headerFile=Join-Path $dest 'TUM_SAMPLE_HEADERS.csv'
$headers | Export-Csv -LiteralPath $headerFile -NoTypeInformation -Encoding UTF8
$extensions = @($files | Group-Object extension | Sort-Object Count -Descending |
  ForEach-Object { [pscustomobject]@{ extension = $_.Name; count = $_.Count } })
$summary=[ordered]@{
  source_filename = [IO.Path]::GetFileName($archiveFile)
  size_bytes = (Get-Item -LiteralPath $archiveFile).Length
  sha256 = $checksum
  entries = $files.Count
  total_uncompressed_bytes = [long](($files | Measure-Object -Property uncompressed_bytes -Sum).Sum)
  types = $extensions
  sample_headers_read = $headers.Count
  sample_header_errors = $failedHeaders
  integrity_note = 'ZIP directory and selected text previews read successfully; full-entry CRC test NOT performed.'
  source = 'https://mediatum.ub.tum.de/1774217'
  provenance = 'TUM real-world driving CAN data; exact vehicle is RWD + 93.4 kWh battery, NOT 2022 Taycan 4S 79.2 kWh.'
}
$summary | ConvertTo-Json -Depth 6 | Out-File -LiteralPath (Join-Path $dest 'TUM_ZIP_SUMMARY.json') -Encoding UTF8
Write-Host "Entradas: $($files.Count)"
Write-Host "SHA256: $checksum"
$extensions | Format-Table -AutoSize | Out-Host
Write-Host "Resultado em: $dest"
Write-Host "Envie no chat TUM_ZIP_SUMMARY.json, TUM_ZIP_ENTRIES.csv e TUM_SAMPLE_HEADERS.csv."
Write-Host 'Nao publique a telemetria bruta antes de conferir metadados e direitos.'
