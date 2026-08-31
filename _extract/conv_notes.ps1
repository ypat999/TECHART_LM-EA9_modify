$dir = 'd:\work\techart\LM-EA9_firmware\releasenotes'
$gb = [Text.Encoding]::GetEncoding('GB18030')
$files = Get-ChildItem $dir -Filter *.txt | Sort-Object Name
foreach ($f in $files) {
    $bytes = [IO.File]::ReadAllBytes($f.FullName)
    $utf8Strict = New-Object Text.UTF8Encoding($false, $true)
    $text = $null
    try { $text = $utf8Strict.GetString($bytes) } catch { $text = $gb.GetString($bytes) }
    $out = Join-Path $dir ($f.BaseName + '_utf8.txt')
    [IO.File]::WriteAllText($out, $text, (New-Object Text.UTF8Encoding($true)))
}
Write-Output 'converted'
