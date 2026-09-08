# upx_dectl.py - 反编译 TECHART_Updater(USB).exe(.NET/C#) 的 HID 协议相关方法 IL。
# 已定位的符号: ReadUSBHID / WriteUSBHID / Find_HID / OpenUSBHid / CreateDeviceFile /
#   READ_FAID / WRITE_FAID / BASE_ADDR_OF_FIRMWARE / MAX_FIRMWARE_SIZE / reportID /
#   ReadTableData + usbHID_DataReceived4ReadTable + isReadTable /
#   readfirmware + usbHID_DataReceived4ReadFirmware + isReadFirmware / usbHID_DataReceived4WriteFirmware
# 目的: 拿到 HID 报文封装(报告 ID、命令字节、地址/长度字段布局), 从而自己写"伪机身"审讯工具。
import sys
import dnfile
from dncil.cil.body import CilMethodBody
from dncil.cil.body.reader import CilMethodBodyReaderBase

PATH = r"d:\work\techart\TECHART_Updater(USB).exe"
pe = dnfile.dnPE(PATH)
pe.parse_data_directories(directories=[dnfile.dnpe.LoadedPEDirectory.RESOURCE] if False else None)
md = pe.net.mdtables


class BR(CilMethodBodyReaderBase):
    def __init__(self, data):
        self.data = data
        self.pos = 0

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


def type_name(row):
    try:
        return str(row.TypeName)
    except Exception:
        return "?"


# 索引: MethodDef -> (类名, 方法名, RVA)
methods = []
cur_type = ""
for i, m in enumerate(md.MethodDef):
    try:
        clsidx = m.Class.row_index - 1
        cur_type = str(md.TypeDef[clsidx].TypeName)
    except Exception:
        pass
    methods.append((cur_type, str(m.Name), m.Rva, m.Flags))

KEY = ("hid", "usb", "firmware", "table", "read", "write", "send", "faid", "open", "find", "report")
sel = [(t, n, r) for (t, n, r, f) in methods if r and any(k in (t + "." + n).lower() for k in KEY)]
print("匹配方法 %d 个" % len(sel))


def resolve(tok):
    """把 metadata token 解析成可读名字"""
    tbl = (tok >> 24) & 0xFF
    rid = tok & 0x00FFFFFF
    try:
        if tbl == 0x0A:   # MemberRef
            r = md.MemberRef[rid - 1]
            return "MemberRef %s" % r.Name
        if tbl == 0x06:   # MethodDef
            return "MethodDef %s.%s" % methods[rid - 1][:2] + (" " if False else "")
        if tbl == 0x70:   # String
            return 'str "%s"' % str(md.Strings[rid - 1].Value)[:60]
        if tbl == 0x71:   # US (user string)
            try:
                return 'us "%s"' % str(pe.net.user_strings.get(rid)).replace("\n", "\\n")[:60]
            except Exception:
                return "us#%d" % rid
        if tbl == 0x11:   # TypeRef
            return "TypeRef %s" % md.TypeRef[rid - 1].TypeName
        if tbl == 0x1B:   # TypeSpec
            return "TypeSpec"
        if tbl == 0x20:   # Field
            r = md.Field[rid - 1]
            return "Field %s" % r.Name
        if tbl == 0x28:   # (in opcode position, method call) handled above
            pass
    except Exception:
        pass
    return "0x%08X" % tok


WANT = sys.argv[1:] or [t + "." + n for (t, n, r) in sel]
for (t, n, rva) in sel:
    if WANT and (t + "." + n) not in WANT and n not in WANT:
        continue
    off = rva_to_off(rva)
    if off is None:
        continue
    data = pe.__data__[off:off + 4096]
    try:
        body = CilMethodBody(BR(data))
    except Exception as e:
        print("\n### %s.%s 解析失败: %s" % (t, n, e))
        continue
    print("\n### %s.%s  (rva 0x%X, %d 条)" % (t, n, rva, len(body.instructions)))
    for ins in body.instructions:
        op = ins.opcode.name
        o = ins.operand
        arg = ""
        if o is not None:
            if isinstance(o, int):
                arg = resolve(o) if o > 0x00FFFFFF else "%d(0x%X)" % (o, o)
            else:
                nm = getattr(o, "name", None)
                val = getattr(o, "value", None)
                row = getattr(o, "row", None)
                rn = getattr(row, "Name", None) if row is not None else None
                if nm:
                    arg = "%s:%s" % (type(o).__name__, nm)
                elif rn:
                    arg = "%s:%s" % (type(o).__name__, rn)
                elif val is not None:
                    arg = resolve(val) if (isinstance(val, int) and val > 0x00FFFFFF) else \
                        "%s:%s" % (type(o).__name__, val)
                else:
                    arg = type(o).__name__
        print("   %-14s %s" % (op, arg))
