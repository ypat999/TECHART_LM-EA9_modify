param()
$exe = 'd:\work\techart\TECHART_Updater(USB-WIN).exe'
$bin = 'd:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin'
$outFile = 'd:\work\techart\_extract\updater_strings.txt'

$bytes = [IO.File]::ReadAllBytes($exe)
Write-Output ('EXE size: ' + $bytes.Length)

# --- strings: UTF-16LE both alignments + ASCII ---
$found = New-Object System.Collections.Generic.HashSet[string]

$textE = [Text.Encoding]::Unicode.GetString($bytes)
$textO = [Text.Encoding]::Unicode.GetString($bytes, 1, $bytes.Length - 1)
$textA = [Text.Encoding]::ASCII.GetString($bytes)

$re = New-Object Text.RegularExpressions.Regex('[\u0020-\u007E\u4E00-\u9FFF]{5,}')
foreach ($t in @($textE, $textO, $textA)) {
    foreach ($m in $re.Matches($t)) {
        [void]$found.Add($m.Value)
    }
}
# keep only entries with at least 3 printable ASCII chars (drop pure-CJK noise is not wanted; keep all readable)
$lines = $found | Sort-Object
[IO.File]::WriteAllLines($outFile, $lines, [Text.Encoding]::UTF8)
Write-Output ('strings written: ' + $lines.Count)

# --- referenced assemblies (reflection-only, no execution) ---
try {
    $asm = [Reflection.Assembly]::ReflectionOnlyLoadFrom($exe)
    Write-Output 'REF-ASSEMBLIES:'
    foreach ($r in $asm.GetReferencedAssemblies()) {
        Write-Output ('  ' + $r.FullName)
    }
    Write-Output 'MODULE-TYPE: ' $asm.Module.FullyImportedModuleType 2>$null
} catch {
    Write-Output ('reflection failed: ' + $_.Exception.Message)
}

# --- firmware header hexdump (Cortex-M vector table check) ---
$fb = [IO.File]::ReadAllBytes($bin)
Write-Output ('BIN size: ' + $fb.Length)
$hex = ($fb[0..63] | ForEach-Object { $_.ToString('X2') }) -join ' '
Write-Output ('BIN first 64 bytes: ' + $hex)
$sp = [BitConverter]::ToUInt32($fb, 0)
$rst = [BitConverter]::ToUInt32($fb, 4)
Write-Output ('initial SP = 0x' + $sp.ToString('X8') + '  reset vector = 0x' + $rst.ToString('X8'))
