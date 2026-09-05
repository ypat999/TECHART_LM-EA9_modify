# mk_synth_exif.py - synthetic TIFF with IFD0 tag0x000D=3.5m and ExifIFD tag0x000D=1.25m (test focus_exif.py)
import struct
rat = struct.pack('<II', 7, 2)          # 3.5 m   (IFD0)
rat_sub = struct.pack('<II', 5, 4)      # 1.25 m  (ExifIFD)
ifd0_off = 8
ifd0_size = 2 + 12 * 2 + 4              # 2 entries
ifdsub_at = ifd0_off + ifd0_size
ifdsub_size = 2 + 12 * 1 + 4
r1_at = ifdsub_at + ifdsub_size         # IFD0 rational
r2_at = r1_at + 8                       # Exif rational
e0 = struct.pack('<HHII', 0x000D, 0x000A, 1, r1_at)
e1 = struct.pack('<HHII', 0x8769, 0x0004, 1, ifdsub_at)
ifd0 = struct.pack('<H', 2) + e0 + e1 + struct.pack('<I', 0)
e2 = struct.pack('<HHII', 0x000D, 0x000A, 1, r2_at)
ifdsub = struct.pack('<H', 1) + e2 + struct.pack('<I', 0)
out = b'II*\x00' + struct.pack('<I', ifd0_off) + ifd0 + ifdsub + rat + rat_sub
open(r'd:\work\techart\_extract\synth_test.tif', 'wb').write(out)
print("ok")
