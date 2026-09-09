// hid_hook.js v3 - 只记 HID 相关: W/R 长度∈{64,65}, DeviceIoControl device-type=0x0B
function hexp(ptr, n) {
  try {
    var ab = ptr.readByteArray(n);
    var u8 = new Uint8Array(ab);
    var out = [];
    for (var i = 0; i < u8.length; i++) out.push(("0" + u8[i].toString(16)).slice(-2));
    return out.join(" ");
  } catch (e) { return "<err:" + e + ">"; }
}
function isHidSize(n) { return n === 64 || n === 65; }

var k32 = Process.getModuleByName("kernel32.dll");
var pending = {};
var hidHandles = {};   // 收到过 95 27 68 18 写的句柄

Interceptor.attach(k32.findExportByName("WriteFile"), {
  onEnter: function (a) {
    var buf = a[1], n = a[2].toInt32();
    if (isHidSize(n) && !buf.isNull()) {
      var d = hexp(buf, n);
      var h = a[0].toString();
      // 载荷里出现魔术头 => 这是环的 HID 句柄
      if (d.indexOf("95 27 68 18") >= 0) hidHandles[h] = 1;
      send({ t: "W", h: h, n: n, d: d });
    }
  }
});
Interceptor.attach(k32.findExportByName("ReadFile"), {
  onEnter: function (a) { this.h = a[0].toString(); this.buf = a[1]; this.n = a[2].toInt32(); this.pRead = a[3]; this.ov = a[4]; },
  onLeave: function (r) {
    if (isHidSize(this.n) && !this.buf.isNull()) {
      var got = this.pRead.isNull() ? 0 : this.pRead.readU32();
      if (got > 0) send({ t: "R", h: this.h + "/rf", n: got, d: hexp(this.buf, got) });
    }
    if (!this.ov.isNull() && isHidSize(this.n)) pending[this.ov.toString()] = [this.buf, this.h];
  }
});
Interceptor.attach(k32.findExportByName("GetOverlappedResult"), {
  onEnter: function (a) { this.ov = a[1]; this.pGot = a[2]; },
  onLeave: function (r) {
    if (r.toInt32() && !this.ov.isNull()) {
      var rec = pending[this.ov.toString()];
      var got = this.pGot.isNull() ? 0 : this.pGot.readU32();
      if (rec && got > 0 && isHidSize(got))
        send({ t: "R", h: rec[1] + "/ovl", n: got, d: hexp(rec[0], got) });
    }
  }
});
Interceptor.attach(k32.findExportByName("DeviceIoControl"), {
  onEnter: function (a) {
    this.code = a[1].toUInt32();
    if (((this.code >>> 16) & 0x3fff) !== 0x0B) { this.skip = true; return; }
    this.skip = false;
    this.in = a[2]; this.inLen = a[3].toInt32(); this.out = a[4]; this.outLen = a[5].toInt32();
  },
  onLeave: function (r) {
    if (this.skip) return;
    var c = "0x" + (this.code >>> 0).toString(16);
    if (this.inLen > 0 && this.inLen <= 66 && !this.in.isNull()) send({ t: "IOin", c: c, n: this.inLen, d: hexp(this.in, this.inLen) });
    if (this.outLen > 0 && this.outLen <= 66 && !this.out.isNull()) send({ t: "IOout", c: c, n: this.outLen, d: hexp(this.out, this.outLen) });
  }
});
send({ t: "ready" });
