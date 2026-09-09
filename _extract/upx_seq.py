# upx_seq.py - 打印指定方法完整 IL(带字段/方法/字符串名), 用于还原报文发送时序
import sys
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


meths = []
cur = ""
for m in md.MethodDef:
    try:
        cur = str(md.TypeDef[m.Class.row_index - 1].TypeName)
    except Exception:
        pass
    meths.append((cur, str(m.Name), m.Rva))


def resolve(o):
    if not isinstance(o, int):
        return str(o)[:30]
    tbl = (o >> 24) & 0xFF
    rid = o & 0xFFFFFF
    try:
        if tbl == 0x04:
            return "F:" + str(md.Field[rid - 1].Name)
        if tbl == 0x06:
            return "M:%s.%s" % meths[rid - 1][:2]
        if tbl == 0x0A:
            return "MR:" + str(md.MemberRef[rid - 1].Name)
        if tbl == 0x71:
            return 'us"%s"' % str(pe.net.user_strings.get(rid)).replace("\n", "\\n")[:40]
        if tbl == 0x70:
            return '"%s"' % str(md.Strings[rid - 1].Value)[:40]
    except Exception:
        pass
    return "0x%X" % o


want = sys.argv[1:]
for (t, n, rva) in meths:
    if n not in want:
        continue
    off = rva_to_off(rva)
    if off is None:
        continue
    try:
        body = CilMethodBody(BR(pe.__data__[off:off + 8192]))
    except Exception:
        continue
    print("\n### %s.%s" % (t, n))
    for idx, ins in enumerate(body.instructions):
        print("  %3d %-14s %s" % (idx, ins.opcode.name, resolve(ins.operand if isinstance(ins.operand, int) else getattr(ins.operand, "value", None))))
