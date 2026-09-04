# re_sensors.py - hunt for position-sensor evidence in LM-EA9 v1.8.0 firmware
# Hypothesis under test: adapter has NO position sensor; norm06/05 position fields
# are transmitted verbatim from the flash template (open-loop or static).
# Tests:
#  T1: literal scan - any code reference (literal word / halfword combos) into frame
#      table VMA range 0xA9D0..0xAED0  (file 0x49D0..0x4ED0, BASE=0x6000)
#  T2: peripheral inventory - literals in 0x4000_0000..0x4003_FFFF (STM32F0 map)
#      esp. ADC(0x40012400), TIM2(0x40000000,encoder-capable), TIM3, TIM14, EXTI,
#      COMP, DAC - presence/absence of analog/encoder blocks.
#  T3: RAM data-region literals (0x20000000..0x20003000) w/ STR nearby - does any
#      code write a buffer that was copied from the table (dynamic patching)?
import struct
from capstone import *

path = r"d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin"
data = open(path, "rb").read()
n = len(data)
BASE = 0x6000
TBL_LO, TBL_HI = 0xA900, 0xAF00

print("== T1a: 32-bit literal words pointing into frame table ==")
hits = 0
for off in range(0, n - 3):
    w = struct.unpack_from("<I", data, off)[0]
    if TBL_LO <= w <= TBL_HI:
        print("  foff 0x%04X (addr 0x%04X) -> 0x%04X" % (off, BASE + off, w))
        hits += 1
print("  total=%d" % hits)

print("== T1b: halfword pairs (MOVS+LSLS style, imm 0xA9xx..0xAFxx) ==")
hh = 0
for off in range(0, n - 1):
    h = struct.unpack_from("<H", data, off)[0]
    if (h >> 4) in range(0xA90, 0xAF1):   # high nibble-ish trick: imm8<<4 forms
        pass
for off in range(0, n - 1):
    h = struct.unpack_from("<H", data, off)[0]
    if 0xA9D0 <= (h << 4) <= 0xAF00:
        print("  foff 0x%04X half=0x%04X -> *16 = 0x%04X" % (off, h, h << 4))
        hh += 1
print("  total=%d" % hh)

PERIPH = {
    0x40000000: "TIM2", 0x40000400: "TIM3", 0x40000800: "TIM6", 0x40000C00: "TIM7",
    0x40001000: "TIM14", 0x40001400: "TIM15", 0x40001800: "TIM16", 0x40001C00: "TIM17",
    0x40004800: "I2C1", 0x40005400: "I2C1_F0?/USART2", 0x40004C00: "USART2/3",
    0x40005800: "CAN", 0x40006400: "USART3", 0x40010000: "SYSCFG/VCMP",
    0x40011000: "ADC1", 0x40012C00: "TIM1", 0x40013000: "SPI1", 0x40013800: "USART1",
    0x40018000: "DAC", 0x40020000: "UNKNOWN(F0?)", 0x40021000: "RCR/PWR(F0?)",
    0x40010800: "TIM15?", 0x40002800: "BB/FMC?",
}
print("== T2: peripheral-range literals (0x4000_0000..0x4004_FFFF) ==")
import collections
periph_hits = collections.Counter()
for off in range(0, n - 3):
    w = struct.unpack_from("<I", data, off)[0]
    if 0x40000000 <= w <= 0x4004FFFF:
        # bucket to 0x400-aligned base
        base = w & 0xFFFF0000 | (w & 0xF000)
        periph_hits["0x%08X" % w] += 0  # keep exact
        periph_hits[("base", base)] += 1
agg = collections.Counter()
for off in range(0, n - 3):
    w = struct.unpack_from("<I", data, off)[0]
    if 0x40000000 <= w <= 0x4004FFFF:
        agg[w >> 10] += 1
if not agg:
    print("  NONE at all")
for k, c in sorted(agg.items()):
    print("  addr-ish 0x%04X000  count=%d" % (k, c))

print("== T2b: exact 32-bit peripheral words (first 40) ==")
shown = 0
for off in range(0, n - 3):
    w = struct.unpack_from("<I", data, off)[0]
    if 0x40000000 <= w <= 0x4004FFFF:
        print("  foff 0x%04X -> 0x%08X" % (off, w))
        shown += 1
        if shown >= 40: break
print("  shown=%d" % shown)

print("== T3: RAM literals 0x20000000..0x20003000 (candidate frame buffers) ==")
rams = {}
for off in range(0, n - 3):
    w = struct.unpack_from("<I", data, off)[0]
    if 0x20000000 <= w <= 0x20003000:
        rams.setdefault(w, []).append(BASE + off)
for w in sorted(rams):
    print("  RAM 0x%08X referenced %dx from: %s" % (w, len(rams[w]), [format(a, "X") for a in rams[w][:8]]))

print("== T3b: STR instructions touching small offsets of loaded regs (coarse) ==")
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
md.detail = True
code_lo, code_hi = BASE, 0xA900
str_cnt = 0
str_targets = collections.Counter()
for off in range(0, n - 4, 2):
    a = BASE + off
    if a >= 0xA900: break
    for ins in list(md.disasm(data[off:off + 4], a, 1)):
        if ins.mnemonic in ("str", "strb", "strh"):
            str_cnt += 1
print("  total STR-family insns in code: %d" % str_cnt)
