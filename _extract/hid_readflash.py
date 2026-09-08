# hid_readflash.py - 路线 A: 伪机身审讯环 (读回 flash)
# 依据: 反编译 TECHART_Updater(USB).exe 得到
#   ReadFirmwareFromAdapter(addr): 64B HID output report, [0..5]=预存帧头, [6..9]=addr(LE32),
#                                  守卫 addr <= 0x08014000 (=> 可读回整片 80KB)
#   ReadTableData(addr): 同结构, 守卫 addr <= 0x08006320
#   应答按 curCmd 分派 (静态 0x0C=ReadTable, 0x0D=ReadFirmware)
# 帧头具体字节我们没从 IL 里直接抠到, 但可以用【自校验】暴力试: 我们知道环里现在跑的是哪支
# 固件(V3/K4/Q1/Q6/O5...), 所以"读 0x08006000 应当回什么字节"是已知的 -> 命中即证明读通。
# 用法: 环按平时刷写的接法 USB 连 PC(必要时先按升级程序进入更新模式), 然后:
#   python _extract\hid_readflash.py            # 暴力试帧头
#   python _extract\hid_readflash.py --dump     # 已试通后整片 dump 到 _extract\ringflash.bin
import struct
import sys
import os

import hid

VID, PID = 0x0483, 0x575A
BASE = 0x08006000                      # 我们镜像在 flash 里的假定基址(由 ReadTable 守卫 0x08006320 旁证)
PATCH_DIR = r"d:\work\techart\patches"
OUT = r"d:\work\techart\_extract\ringflash.bin"

IMGS = {}
for n in ("V3", "K4", "Q1", "Q6", "Q7", "Q8", "Q9", "O5", "I7", "ORIG"):
    for d_ in (PATCH_DIR, r"d:\work\techart\flash_kit\product\firmware\LM-EA9"):
        fn = {"ORIG": "EA9-VER-1-8-0.bin"}.get(n, "EA9-%s.bin" % n)
        p = os.path.join(d_, fn)
        if os.path.exists(p):
            IMGS[n] = open(p, "rb").read()
            break


def known_bytes(addr, ln):
    """返回 (标签, 期望字节) 列表: 我们已知的每支固件在该地址处的内容"""
    fo = addr - BASE
    out = []
    if fo < 0:
        return out
    for tag, img in IMGS.items():
        chunk = img[fo:fo + ln]
        if chunk:
            out.append((tag, chunk))
    return out


def make_report(cls, seq, typ, addr, ln=0x0040):
    """[0]=report id 0, [1..5]=帧头(F0,len2,cls,seq,typ) 的候选拼装; addr 放在 [6..9]"""
    r = bytearray(64)
    r[1] = 0xF0
    r[2] = ln & 0xFF
    r[3] = (ln >> 8) & 0xFF
    r[4] = cls
    r[5] = seq
    r[6] = typ
    r[7:11] = struct.pack("<I", addr)
    return bytes(r)


def make_report2(cls, typ, addr, ln=0x0040):
    """变体: 帧头 6 字节直接放 [0..5](无 report id), 地址放 [6..9] —— 与 IL 完全一致"""
    r = bytearray(64)
    r[0] = 0xF0
    r[1] = ln & 0xFF
    r[2] = (ln >> 8) & 0xFF
    r[3] = cls
    r[4] = typ
    r[5] = 0x00
    r[6:10] = struct.pack("<I", addr)
    return bytes(r)


def match_reply(reply, addr):
    """回复里是否出现我们已知的镜像字节?"""
    exp = known_bytes(addr, 8)
    for tag, chunk in exp:
        if chunk and chunk[:6] in reply:
            off = reply.find(chunk[:6])
            return tag, off
    return None, None


def main():
    dev = hid.device()
    try:
        dev.open(VID, PID)
    except OSError as e:
        print("打不开 0483:575A:", e)
        print("请确认: 环已用 USB 连 PC(与平时刷写同样的接法); 必要时先开一次官方升级程序让它进入模式。")
        return 2
    try:
        dev.set_nonblocking(0)
    except Exception:
        pass
    print("已连接:", dev.get_product_string(), "|", dev.get_serial_string())
    addr = BASE
    cands = []
    for cls in (0x01, 0x02, 0x00):
        for typ in range(0x00, 0x100):
            cands.append(("f1", cls, 0x00, typ))
    tried = 0
    for kind, cls, seq, typ in cands:
        pkt = make_report(cls, seq, typ, addr)
        try:
            dev.write(pkt)
        except Exception as e:
            print("写失败:", e)
            return 3
        tried += 1
        try:
            r = dev.read(64, 120)
        except Exception:
            r = None
        if r:
            reply = bytes(r)
            if reply.strip(b"\x00"):
                tag, off = match_reply(reply, addr)
                print("  有回复 cls=%02X typ=%02X  %s  %s" % (
                    cls, typ, reply.hex(" ")[:96], ("<== 命中镜像 %s @%d" % (tag, off)) if tag else ""))
                if tag:
                    print("  ★读通了! 用: python _extract\\hid_readflash.py --dump")
                    return 0
        if tried % 64 == 0:
            print("  ...已试 %d 个帧头组合" % tried)
    # 变体 2
    print("--- 换无 report-id 布局再试 ---")
    for cls in (0x01, 0x02):
        for typ in range(0x00, 0x100):
            dev.write(make_report2(cls, typ, addr))
            r = dev.read(64, 120)
            if r:
                reply = bytes(r)
                if reply.strip(b"\x00"):
                    tag, off = match_reply(reply, addr)
                    print("  有回复 cls=%02X typ=%02X  %s  %s" % (
                        cls, typ, reply.hex(" ")[:96], ("<== 命中镜像 %s @%d" % (tag, off)) if tag else ""))
                    if tag:
                        return 0
    print("全部组合无有效回复 => 环当前不在可审讯模式(或需要先按升级程序的按钮)。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
