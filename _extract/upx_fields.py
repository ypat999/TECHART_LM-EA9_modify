# upx_fields.py - 列 Field 表(名字+token), 并对带 FieldRVA 的标出 blob 内容
import dnfile

PATH = r"d:\work\techart\TECHART_Updater(USB).exe"
pe = dnfile.dnPE(PATH)
md = pe.net.mdtables


def rva_to_off(rva):
    for s in pe.sections:
        if s.PointerToRawData and s.VirtualAddress <= rva < s.VirtualAddress + max(s.SizeOfRawData, s.Misc_VirtualSize):
            return s.PointerToRawData + (rva - s.VirtualAddress)
    return None


blobs = {}
for fr in md.FieldRva:
    tok = 0x04000000 + fr.Field.row_index
    ln = getattr(fr, "length", None) or 32
    off = rva_to_off(fr.Rva)
    blobs[tok] = pe.__data__[off:off + ln]

import sys

want = sys.argv[1:]  # 例: python upx_fields.py 15 20 21 76 77 78 79
for i, f in enumerate(md.Field):
    tok = 0x04000000 + i + 1
    rid = "%X" % (i + 1)
    if want and rid.upper() not in [w.upper() for w in want]:
        continue
    try:
        tname = str(md.TypeDef[f.Parent.row_index - 1].TypeName)
    except Exception:
        tname = "?"
    extra = ""
    if tok in blobs:
        extra = "  blob=%s" % blobs[tok].hex(" ")
    print("0x%08X %-28s %s%s" % (tok, str(f.Name), tname, extra))
