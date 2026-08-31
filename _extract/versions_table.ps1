$bins = Get-ChildItem 'd:\work\techart\LM-EA9_firmware\bin\*.bin' | Sort-Object Name
function FindBytes([byte[]]$arr,[byte[]]$pat){
  for($i=0;$i -le $arr.Length-$pat.Length;$i++){
    $ok=$true
    for($j=0;$j -lt $pat.Length;$j++){ if($arr[$i+$j] -ne $pat[$j]){$ok=$false;break} }
    if($ok){return $i}
  }
  return -1
}
function Hex([byte[]]$arr,$off,$len){
  if($off -lt 0){return '?'}
  ($arr[$off..($off+$len-1)] | ForEach-Object {'{0:X2}' -f $_}) -join ' '
}
foreach($f in $bins){
  $b=[IO.File]::ReadAllBytes($f.FullName)
  Write-Output ('===== {0}  size={1}' -f $f.Name,$b.Length)
  # norm05: F0 69 00 01 64 05 (class01 seq64 type05)
  $p=FindBytes $b @(0xF0,0x69,0x00,0x01,0x64,0x05)
  if($p -ge 0){ $bd=$p+6
    Write-Output ('norm05 @0x{0:X} body[0..31]  {1}' -f $p,(Hex $b $bd 32))
    Write-Output ('norm05 body[32..63] {0}' -f (Hex $b ($bd+32) 32))
  } else { Write-Output 'norm05 header NOT FOUND' }
  # init08: F0 D2 00 02 00 08
  $p=FindBytes $b @(0xF0,0xD2,0x00,0x02,0x00,0x08)
  if($p -ge 0){ $bd=$p+6
    Write-Output ('init08 @0x{0:X} body[0..39]  {1}' -f $p,(Hex $b $bd 40))
    Write-Output ('init08 body[40..71] {0}' -f (Hex $b ($bd+40) 32))
  } else { Write-Output 'init08 header NOT FOUND' }
  # init01: F0 29 00 02 00 01
  $p=FindBytes $b @(0xF0,0x29,0x00,0x02,0x00,0x01)
  if($p -ge 0){ Write-Output ('init01 @0x{0:X} body[0..15]  {1}' -f $p,(Hex $b ($p+6) 16)) }
  else { Write-Output 'init01 header NOT FOUND' }
  # init07 (version): F0 2B 00 02 00 07
  $p=FindBytes $b @(0xF0,0x2B,0x00,0x02,0x00,0x07)
  if($p -ge 0){ Write-Output ('init07 @0x{0:X} body[0..15]  {1}' -f $p,(Hex $b ($p+6) 16)) }
  else { Write-Output 'init07 header NOT FOUND' }
  # init3F (name): F0 4A 00 02 00 3F
  $p=FindBytes $b @(0xF0,0x4A,0x00,0x02,0x00,0x3F)
  if($p -ge 0){
    $s=''; for($i=$p+7;$i -lt $p+40;$i++){ $c=$b[$i]; if($c -eq 0){break}; $s+=[char]$c }
    Write-Output ('init3F @0x{0:X} name="{1}"  body[0..3]={2}' -f $p,$s,(Hex $b ($p+6) 4))
  } else { Write-Output 'init3F header NOT FOUND' }
}
