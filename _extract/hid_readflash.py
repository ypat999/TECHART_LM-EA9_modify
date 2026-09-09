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
# 反编译 upx_dectl 实证: ReadFirmwareFromAdapter(0x08005000) / WriteDataToAdapter(0x08005000)
# (见 usbHID_DataReceived4ReadTable/Firmware 里的 ldc.i4 0x8005000) => 固件基址 0x08005000
BASE = 0x08005000
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


# 真正报文头由反编译 upx 得到: field 0x15 / check_tab / spy_tab / state 都是
# 6 字节魔术头 95 27 68 18 XX XX (尾部两字节区分命令)。addr 放在报文 [6..9]。
MAGIC = bytes.fromhex("95276818")
TAILS = [(a, b) for a in (0x00, 0x01, 0x02, 0x03) for b in (0x00, 0x01, 0x02, 0x03)]


def make_report(t0, t1, addr):
    """线格式: [0]=reportID 0, [1..6]=6B 魔术头, [7..10]=addr(LE32)"""
    r = bytearray(65)
    r[1:5] = MAGIC
    r[5] = t0
    r[6] = t1
    r[7:11] = struct.pack("<I", addr)
    return bytes(r)


def make_report2(t0, t1, addr):
    """变体: 无 report-id 前缀, 64 字节报文, 头在 [0..5], addr 在 [6..9]"""
    r = bytearray(64)
    r[0:4] = MAGIC
    r[4] = t0
    r[5] = t1
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
    print("已连接:", dev.get_product_string(), "|", dev.get_serial_number_string())
    addr = BASE
    # 真实候选帧头(反编译 IL 实证): 03 03=spy_tab(读), 01 01=check_tab(握手), 02 02=state
    heads = {
        (0x03, 0x03): "spy_tab(读)",
        (0x01, 0x01): "check_tab(握手)",
        (0x02, 0x02): "state",
        (0x00, 0x00): "0000",
    }
    echo_cnt = 0
    total = 0
    for t0, t1 in heads:
        pkt = make_report(t0, t1, addr)   # Windows 上唯一有效布局: [0]=reportID0 + 64B 载荷
        try:
            dev.write(pkt)
        except Exception as e:
            print("写失败:", e)
            return 3
        total += 1
        try:
            r = dev.read(64, 250)
        except Exception:
            r = None
        if not r:
            continue
        reply = bytes(r)
        if not reply.strip(b"\x00"):
            continue
        tag, off = match_reply(reply, addr)
        payload = pkt[1:65]
        is_echo = reply[:10] == payload[:10]
        if is_echo:
            echo_cnt += 1
        print("  %-14s %s  %s" % (
            heads[(t0, t1)], reply.hex(" ")[:60],
            ("★命中镜像 %s @%d" % (tag, off)) if tag else ("(纯回显)" if is_echo else "(非回显,需细看)")))
        if tag:
            print("  ★读通了! 用: python _extract\\hid_readflash.py --dump")
            return 0
    if total and echo_cnt == total:
        print("\n=> 设备对每条命令都逐字节原样回显 = 环在【应用固件 echo 模式】, "
              "未进入能服务 95 27 68 18 协议的 bootloader 模式。")
        print("   官方升级程序能读回版本, 说明它有一个'把环切进 bootloader'的触发(底座/按键/首包)。")
    else:
        print("\n=> 混合响应(部分非回显), 需抓包核对(%d/%d 回显)。" % (echo_cnt, total))
    return 1


if __name__ == "__main__":
    sys.exit(main())
