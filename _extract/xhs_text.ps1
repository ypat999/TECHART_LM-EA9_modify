param([string]$In, [string]$Out)

$html = [System.IO.File]::ReadAllText($In, [System.Text.Encoding]::UTF8)

# remove script/style blocks
$html = [regex]::Replace($html, '(?is)<script.*?</script>', ' ')
$html = [regex]::Replace($html, '(?is)<style.*?</style>', ' ')
# br / block ends -> newline
$html = [regex]::Replace($html, '(?i)<(br|/p|/div|/li|/h[1-6]|/section|/tr)[^>]*>', "`n")
# strip remaining tags
$html = [regex]::Replace($html, '(?s)<[^>]+>', ' ')
# decode common entities
$html = $html -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&lt;', '<' -replace '&gt;', '>' -replace '&quot;', '"' -replace '&#39;', "'" -replace '&apos;', "'"
# normalise whitespace
$html = [regex]::Replace($html, '[ \t\f\v]+', ' ')
$html = [regex]::Replace($html, '(?m)^ *. *$', '')
$html = [regex]::Replace($html, '(\r?\n){3,}', "`n`n")

[System.IO.File]::WriteAllText($Out, $html.Trim(), (New-Object System.Text.UTF8Encoding $false))
Write-Output "$([System.IO.Path]::GetFileName($In)) -> $((Get-Item $Out).Length) chars"
