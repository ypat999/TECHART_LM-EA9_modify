# upx_dectl2.py - 按字段 token 找所有碰过它的方法, 完整 dump IL(带常量值)
import sys
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBase

_orig_print = print
_LOGF = open(r"d:\work\techart\_extract\dectl_out.txt", "w", encoding="utf-8")


def print(*a, **k):  # noqa: A001 - 同时写控制台与文件(PS5 管道会吞输出)
    _orig_print(*a, **k)
    k2 = dict(k)
    k2["file"] = _LOGF
    _orig_print(*a, **k2)

PATH = r"d:\work\techart\TECHART_Updater(USB).exe"
pe = dnfile.dnPE(PATH)
md = pe.net.mdtables
args = sys.argv[1:]
WANTFLD = [int(x, 16) for x in args if x.lower().startswith("0x04")]
NAMEWANT = [x.lower() for x in args if not x.lower().startswith("0x04")]
if not WANTFLD:
    WANTFLD = [0x04000015]


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


def fldname(tok):
    try:
        return str(md.Field[tok & 0xFFFFFF - 1].Name)
    except Exception:
        return "?"


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
    if NAMEWANT and n.lower() not in NAMEWANT:
        continue
    off = rva_to_off(rva)
    if off is None:
        continue
    try:
        body = CilMethodBody(BR(pe.__data__[off:off + 8192]))
    except Exception:
        continue
    ins_list = list(body.instructions)
    if not NAMEWANT:
        toks = []
        for ins in ins_list:
            o = ins.operand if isinstance(ins.operand, int) else getattr(ins.operand, "value", None)
            if isinstance(o, int) and o in WANTFLD:
                toks.append(ins.opcode.name)
        if not toks:
            continue
    print("\n### %s.%s" % (t, n))
    for idx, ins in enumerate(ins_list):
        o = ins.operand if isinstance(ins.operand, int) else getattr(ins.operand, "value", None)
        mark = ""
        if isinstance(o, int) and o in WANTFLD:
            mark = "   <<<< %s %s" % (ins.opcode.name, fldname(o))
        arg = ""
        if isinstance(o, int) and not (isinstance(o, int) and o in WANTFLD):
            tbl = (o >> 24) & 0xFF
            rid = o & 0xFFFFFF
            if tbl == 0x70:
                try:
                    arg = '"%s"' % str(md.Strings[rid - 1].Value)[:50]
                except Exception:
                    arg = "0x%X" % o
            elif tbl == 0x71:
                try:
                    arg = 'us"%s"' % str(pe.net.user_strings.get(rid)).replace("\n", "\\n")[:50]
                except Exception:
                    arg = "0x%X" % o
            elif tbl == 0x06:
                arg = "M:%s.%s" % meths[rid - 1][:2]
            elif tbl == 0x0A:
                try:
                    arg = "MR:%s" % md.MemberRef[rid - 1].Name
                except Exception:
                    arg = "0x%X" % o
            elif tbl == 0x04:
                arg = "F:%s" % fldname(o)
            else:
                arg = "0x%X" % o if o > 65535 else str(o)
        elif o is not None:
            arg = str(o)[:40]
        print("  %3d %-14s %-38s%s" % (idx, ins.opcode.name, arg, mark))
