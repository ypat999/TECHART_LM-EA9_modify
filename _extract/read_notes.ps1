$dir = 'd:\work\techart\LM-EA9_firmware\releasenotes'
if (-not (Test-Path $dir)) {
    $dir = 'd:\work\techart\LM-EA9_firmware'
}
$files = Get-ChildItem $dir -Filter *.txt | Sort-Object Name
foreach ($f in $files) {
    Write-Output ('--- ' + $f.Name + ' (' + $f.Length + ' bytes)')
    $bytes = [IO.File]::ReadAllBytes($f.FullName)
    # try UTF8 first
    $text = [Text.Encoding]::UTF8.GetString($bytes)
    Write-Output $text
    Write-Output ''
}
