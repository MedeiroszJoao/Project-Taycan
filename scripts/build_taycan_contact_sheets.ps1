# Generate numbered image contact sheets LOCALLY, without uploading Porsche images.
# Windows PowerShell 5.1 or PowerShell 7 on Windows. No Python required.
[CmdletBinding()]
param(
    [string]$Source = (Join-Path $HOME 'Downloads\Taycan_Images'),
    [string]$Output = (Join-Path $HOME 'Downloads\Taycan_ContactSheets'),
    [ValidateRange(2,10)][int]$Columns = 5,
    [ValidateRange(2,10)][int]$Rows = 5
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
if (-not (Test-Path -LiteralPath $Source -PathType Container)) { throw "Pasta nao encontrada: $Source" }
$root = (Resolve-Path -LiteralPath $Source).ProviderPath.TrimEnd([char]'\', [char]'/')
$dest = [IO.Path]::GetFullPath($Output)
$repoPath = [IO.Path]::GetFullPath((Join-Path $HOME 'Downloads\Project-Taycan')).TrimEnd([char]'\', [char]'/')
if ($dest.Equals($repoPath,[StringComparison]::OrdinalIgnoreCase) -or
    $dest.StartsWith($repoPath+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Nao grave miniaturas dentro do repositorio publico.'
}
if (-not (Test-Path -LiteralPath $dest)) { New-Item -ItemType Directory -Force -Path $dest | Out-Null }
if (@(Get-ChildItem -LiteralPath $dest -File -Filter 'taycan_sheet_*.jpg').Count -gt 0) {
    throw 'Ja existem pranchas no destino. Escolha outro caminho com -Output.'
}
$exts = @('.jpg','.jpeg','.png','.bmp','.gif','.tif','.tiff')
$files = @(Get-ChildItem -LiteralPath $root -Recurse -File |
    Where-Object { $exts -contains $_.Extension.ToLowerInvariant() } | Sort-Object FullName)
if ($files.Count -eq 0) { throw 'Nenhuma imagem suportada encontrada.' }
$allCount = @(Get-ChildItem -LiteralPath $root -Recurse -File).Count
if ($allCount -ne $files.Count) { Write-Warning "Encontrados $allCount arquivos e $($files.Count) imagens suportadas." }
$cellW=290; $cellH=225; $margin=16; $headerH=48
$pageCount=$Columns*$Rows
$sheetW=$cellW*$Columns+$margin*2
$sheetH=$cellH*$Rows+$margin*2+$headerH
$pages=[int][Math]::Ceiling($files.Count/[double]$pageCount)
$font=[System.Drawing.Font]::new('Arial',[single]9)
$headerFont=[System.Drawing.Font]::new('Arial',[single]13,[System.Drawing.FontStyle]::Bold)
$records=New-Object 'System.Collections.Generic.List[object]'
$failures=0
try {
    for ($page=1; $page -le $pages; $page++) {
        $bmp=[System.Drawing.Bitmap]::new($sheetW,$sheetH)
        $gfx=[System.Drawing.Graphics]::FromImage($bmp)
        try {
            $gfx.Clear([System.Drawing.Color]::White)
            $gfx.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $gfx.DrawString(("TAYCAN | PRANCHA {0:D3}/{1:D3}" -f $page,$pages),
                $headerFont,[System.Drawing.Brushes]::Black,[single]16,[single]10)
            for ($cell=0; $cell -lt $pageCount; $cell++) {
                $idx=($page-1)*$pageCount+$cell
                if ($idx -ge $files.Count) { break }
                $f=$files[$idx]
                $x=$margin+($cell%$Columns)*$cellW
                $y=$margin+$headerH+[int][Math]::Floor($cell/[double]$Columns)*$cellH
                $gfx.DrawRectangle([System.Drawing.Pens]::LightGray,[int]$x,[int]$y,[int]($cellW-8),[int]($cellH-8))
                $label=("#{0:D4} {1}" -f ($idx+1),$f.Name)
                if ($label.Length -gt 37) { $label=$label.Substring(0,34)+'...' }
                $gfx.DrawString($label,$font,[System.Drawing.Brushes]::Black,
                    [single]($x+6),[single]($y+$cellH-34))
                $img=$null; $w=$null; $h=$null; $status='OK'
                try {
                    $img=[System.Drawing.Image]::FromFile($f.FullName)
                    $w=$img.Width; $h=$img.Height
                    $scale=[Math]::Min(($cellW-26)/[double]$w,($cellH-48)/[double]$h)
                    $dw=[Math]::Max(1,[int][Math]::Round($w*$scale))
                    $dh=[Math]::Max(1,[int][Math]::Round($h*$scale))
                    $dx=$x+[int][Math]::Floor(($cellW-8-$dw)/2)
                    $dy=$y+[int][Math]::Floor(($cellH-44-$dh)/2)+5
                    $rect=[System.Drawing.Rectangle]::new([int]$dx,[int]$dy,[int]$dw,[int]$dh)
                    $gfx.DrawImage($img,$rect)
                } catch {
                    $failures++; $status='READ_ERROR'
                    $gfx.DrawString('IMAGE READ ERROR',$font,[System.Drawing.Brushes]::DarkRed,
                        [single]($x+10),[single]($y+70))
                    Write-Warning ("Falha na imagem #{0}: {1}" -f ($idx+1),$f.FullName)
                } finally {
                    if ($null -ne $img) { $img.Dispose() }
                }
                $relative=$f.FullName.Substring($root.Length).TrimStart([char]'\',[char]'/')
                $records.Add([PSCustomObject]@{
                    index=$idx+1; sheet=$page; cell=$cell+1
                    sheet_file=("taycan_sheet_{0:D3}.jpg" -f $page)
                    filename=$f.Name; relative_path=$relative
                    width_px=$w; height_px=$h; bytes=$f.Length; status=$status
                })
            }
            $outFile=Join-Path $dest ("taycan_sheet_{0:D3}.jpg" -f $page)
            $bmp.Save($outFile,[System.Drawing.Imaging.ImageFormat]::Jpeg)
            Write-Host ("Prancha {0}/{1} concluida." -f $page,$pages)
        } finally {
            $gfx.Dispose(); $bmp.Dispose()
        }
    }
} finally {
    $font.Dispose(); $headerFont.Dispose()
}
$index=Join-Path $dest 'taycan_sheets_index.csv'
$records | Export-Csv -LiteralPath $index -NoTypeInformation -Encoding UTF8
$jpgs=@(Get-ChildItem -LiteralPath $dest -File -Filter 'taycan_sheet_*.jpg' |
    Sort-Object Name | Select-Object -ExpandProperty FullName)
$zip=Join-Path $dest 'taycan_contact_sheets.zip'
Compress-Archive -LiteralPath ($jpgs+@($index)) -DestinationPath $zip -CompressionLevel Optimal -Force
Write-Host "Imagens catalogadas: $($files.Count) | Pranchas: $pages | Erros: $failures"
Write-Host "Anexe ao chat: $zip"
Write-Host 'Nao publique miniaturas ou originais no GitHub publico.'
