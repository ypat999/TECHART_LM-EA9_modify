$base = "d:\work\techart"
$dst  = "d:\work\techart\_extract"

$files = Get-ChildItem $base -Filter *.html | Sort-Object Name
$i = 0
foreach ($file in $files) {
  if ($file.Name -like "*LM-EA9*") { continue }
  $i++
  $html = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
  $html = [regex]::Replace($html, '(?is)<script.*?</script>', ' ')
  $html = [regex]::Replace($html, '(?is)<style.*?</style>', ' ')
  $html = [regex]::Replace($html, '(?i)<(br|/p|/div|/li|/h[1-6]|/section|/tr)[^>]*>', "`n")
  $html = [regex]::Replace($html, '(?s)<[^>]+>', ' ')
  $html = $html -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&lt;', '<' -replace '&gt;', '>' -replace '&quot;', '"' -replace '&#39;', "'"
  $html = [regex]::Replace($html, '[ \t\f\v]+', ' ')
  $html = [regex]::Replace($html, '(\r?\n){3,}', "`n`n")
  $html = $html.Trim()
  $out = "$dst\part$i.txt"
  [System.IO.File]::WriteAllText($out, $html, (New-Object System.Text.UTF8Encoding $false))
  Write-Output ("part{0}  {1} chars  <=  {2}" -f $i, $html.Length, $file.Name)
}
