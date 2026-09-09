# upx_field_blob.py - 抠出 .NET 里用 InitializeArray(FieldRVA) 预存的常量数组字节串
# 目标: TECHART_Updater(USB).exe 中 field 0x04000015 等 6 字节"帧头"数组的真实内容。
import dnfile

PATH = r"d:\work\techart\TECHART_Updater(USB).exe"
pe = dnfile.dnPE(PATH)
md = pe.net.mdtables


def rva_to_off(rva):
    for s in pe.sections:
        if s.PointerToRawData and s.VirtualAddress <= rva < s.VirtualAddress + max(s.SizeOfRawData, s.Misc_VirtualSize):
            return s.PointerToRawData + (rva - s.VirtualAddress)
    return None


for fr in md.FieldRva:
    f = md.Field[fr.Field.row_index - 1]
    fname = str(f.Name)
    try:
        tname = str(md.TypeDef[f.Parent.row_index - 1].TypeName)
    except Exception:
        tname = "?"
    off = rva_to_off(fr.Rva)
    ln = getattr(fr, "length", None) or getattr(fr, "Length", None) or 8
    blob = pe.__data__[off:off + ln] if off else b""
    print("FieldRVA -> %s.%s  rva=0x%X len=%s  bytes=%s" % (tname, fname, fr.Rva, ln, blob.hex(" ")))
