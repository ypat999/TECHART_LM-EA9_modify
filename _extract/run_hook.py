# run_hook.py - 以 frida 启动官方升级程序并记录 HID 读写
import datetime
import os
import sys
import time

import frida

EXE = r"d:\work\techart\TECHART_Updater(USB).exe"
JS = r"d:\work\techart\_extract\hid_hook.js"
LOG = r"d:\work\techart\_extract\hidlog.txt"
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0

logf = open(LOG, "w", encoding="utf-8")


def on_message(msg, data):
    line = "%s %s" % (datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], msg)
    print(line)
    logf.write(line + "\n")
    logf.flush()


js = open(JS, encoding="utf-8").read()
pid = frida.spawn([EXE])
session = frida.attach(pid)
script = session.create_script(js)
script.on("message", on_message)
script.load()
frida.resume(pid)
print("已注入并启动官方程序, 记录中(%.0fs)..." % DUR)
t0 = time.time()
try:
    while time.time() - t0 < DUR:
        time.sleep(0.3)
except KeyboardInterrupt:
    pass
try:
    session.detach()
except Exception:
    pass
logf.close()
print("结束, 日志见", LOG)
