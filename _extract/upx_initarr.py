# upx_initarr.py - 找 InitializeArray(ldtoken) 的真实映射: 哪个字段 = 哪段字节
# 并顺带列出这些数组被 CopyTo/stfld 使用的地方, 定位 field 0x04000015 的 6 字节帧头。
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBase

PATH = r"d:\work\techart\TECHART_Updater(USB).exe"
pe = dnfile.dnPE(PATH)
md = pe.net.mdtables


class BR(CilMethodBodyReaderBase):
    def __init__(self, data):
        self.data, self.pos = data, 0

    def read(self, n):
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def tell(self):
        return self.pos

    def seek(self, o):
        self.pos = o
        return o


def rva_to_off(rva):
    for s in pe.sections:
        if s.PointerToRawData and s.VirtualAddress <= rva < s.VirtualAddress + max(s.SizeOfRawData, s.Misc_VirtualSize):
            return s.PointerToRawData + (rva - s.VirtualAddress)
    return None


# FieldRVA 映射: field token -> (rva, len)
fild = {}
for fr in md.FieldRva:
    fidx = fr.Field.row_index
    fild[0x04000000 + fidx] = (fr.Rva, getattr(fr, "length", None) or getattr(fr, "Length", None))

meths = []
cur = ""
for m in md.MethodDef:
    try:
        cur = str(md.TypeDef[m.Class.row_index - 1].TypeName)
    except Exception:
        pass
    meths.append((cur, str(m.Name), m.Rva))

for (t, n, rva) in meths:
    if not rva:
        continue
    off = rva_to_off(rva)
    if off is None:
        continue
    try:
        body = CilMethodBody(BR(pe.__data__[off:off + 4096]))
    except Exception:
        continue
    ins_list = list(body.instructions)
    for i, ins in enumerate(ins_list):
        if ins.opcode.name != "ldtoken":
            continue
        tok = ins.operand if isinstance(ins.operand, int) else getattr(ins.operand, "value", None)
        if not isinstance(tok, int) or tok not in fild:
            continue
        fr, flen = fild[tok]
        o2 = rva_to_off(fr)
        blob = pe.__data__[o2:o2 + (flen or 16)]
        fname = str(md.Field[tok & 0xFFFFFF - 1].Name)
        # 往前后找 newarr 大小 + 存的字段 (dup ldtoken call stfld <fid>)
        nxt = " ".join(x.opcode.name for x in ins_list[i:i + 6])
        prv = " ".join(x.opcode.name for x in ins_list[max(0, i - 4):i])
        stfid = None
        for j, x in enumerate(ins_list[i:i + 8]):
            if x.opcode.name == "stfld":
                op = x.operand if isinstance(x.operand, int) else getattr(x.operand, "value", None)
                if isinstance(op, int) and (op >> 24) == 0x04:
                    stfid = op
        tgt = ""
        if stfid:
            try:
                tgt = " -> %s.%s" % (t, str(md.Field[stfid & 0xFFFFFF - 1].Name))
            except Exception:
                tgt = " -> fid 0x%08X" % stfid
        print("%s.%s: token=0x%08X(%s) len=%s bytes=[%s]%s\n    ctx: ...%s | %s..." % (
            t, n, tok, fname[:12], flen, blob.hex(" "), tgt, prv, nxt))
