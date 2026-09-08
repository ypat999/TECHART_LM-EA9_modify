# upx_field_xref.py - 找出"报文头/命令码"到底填了什么:
# 扫全部方法 IL, 打印任何引用了指定字段 token 的方法(stfld/ldsfld/ldfld), 并顺带 dump
# 这些方法里的 ldc.i4 常量序列与 newarr 长度 => 还原 64 字节 HID 报文布局。
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBase

PATH = r"d:\work\techart\TECHART_Updater(USB).exe"
pe = dnfile.dnPE(PATH)
md = pe.net.mdtables
WANTFLD = {0x0400000C, 0x0400000D, 0x04000015, 0x04000012, 0x04000020, 0x04000021,
           0x04000001, 0x04000002, 0x04000003}


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

fname = {k: None for k in WANTFLD}
for ti, (t, n, rva) in enumerate(meths):
    if not rva:
        continue
    off = rva_to_off(rva)
    if off is None:
        continue
    try:
        body = CilMethodBody(BR(pe.__data__[off:off + 4096]))
    except Exception:
        continue
    hits = []
    consts = []
    seq = []
    for ins in body.instructions:
        o = ins.operand
        tok = None
        if isinstance(o, int):
            tok = o
        else:
            tok = getattr(o, "value", None)
        if isinstance(tok, int) and tok in WANTFLD:
            hits.append((ins.opcode.name, "0x%08X" % tok))
        if ins.opcode.name.startswith("ldc.i4") and tok is None:
            try:
                v = int(ins.opcode.name.split(".")[-1], 16) if False else None
            except Exception:
                v = None
        if ins.opcode.name in ("ldc.i4", "ldc.i4.s") and isinstance(tok, int):
            consts.append(tok)
        if ins.opcode.name in ("newarr",):
            consts.append("newarr:%s" % tok)
        seq.append(ins.opcode.name)
    if hits:
        print("\n### %s.%s  引用目标字段: %s" % (t, n, hits))
        print("    常量序列: %s" % [hex(c) if isinstance(c, int) else c for c in consts[:20]])
        # 打印指令流(压缩)
        print("    IL: %s" % " ".join(seq[:70]))
