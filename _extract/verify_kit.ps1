# Verify every URL referenced by every LST in flash_kit resolves against the
# corrected HTTP root (flash_kit = document root, same as serve.bat).
$kit = "d:\work\techart\flash_kit"
$port = 8099
$proc = Start-Process -WindowStyle Hidden -FilePath python -PassThru `
    -ArgumentList '-m','http.server',"$port" -WorkingDirectory $kit
Start-Sleep -Seconds 2
try {
    $lstFiles = @((Join-Path $kit "product\TECHART_LST.txt")) + (Get-ChildItem (Join-Path $kit "lsts") -Filter *.txt | ForEach-Object { $_.FullName })
    $bad = 0
    foreach ($lst in $lstFiles) {
        Write-Output ("==== " + (Split-Path $lst -Leaf))
        foreach ($line in [System.IO.File]::ReadAllLines($lst)) {
            if ($line.Trim().Length -eq 0) { continue }
            $cols = $line.Split(';')
            Write-Output ("     " + $cols[0] + "  " + $cols[3])
            for ($i = 5; $i -le 6; $i++) {
                $url = $cols[$i] -replace 'http://www\.techart-logic\.com', "http://127.0.0.1:$port"
                try {
                    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -Method Head -TimeoutSec 8
                    Write-Output ("       OK   " + $r.StatusCode + "  " + $r.Headers['Content-Length'] + "  " + (Split-Path $url -Leaf))
                } catch {
                    $bad++
                    Write-Output ("       FAIL " + $url + "  " + $_.Exception.Message)
                }
            }
        }
    }
    Write-Output ("bad = " + $bad)
} finally {
    Stop-Process -Id $proc.Id -Force
}
