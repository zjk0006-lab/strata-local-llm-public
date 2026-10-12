"""Generate start.ico (green play triangle) and stop.ico (red rounded square).

Pure Python (zlib + struct) - no PIL, no ImageMagick, no network. Uses the
Vista+ PNG-in-ICO container: ICONDIR + one ICONDIRENTRY + an embedded PNG.
Anti-aliasing is done with 4x4 supersampling per pixel.

Sizes: 128x128 RGBA.

Usage:
  python make_icons.py --out "G:\\AI\\models\\Qwen3.8-Flash-Next-IQ3_S\\icons"

Verification tip: this box's local model cannot read images, so verify by parsing
the ICO back, extracting the PNG, decoding the alpha channel and rendering it as
ASCII art (see verify_ascii() at the bottom).
"""
import argparse
import os
import struct
import zlib

SIZE = 128
SS = 4  # supersample factor per axis


def _png(width, height, rgba):
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0
        raw += rgba[y * width * 4:(y + 1) * width * 4]
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def _render(shape):
    """Return RGBA bytes for a SIZE x SIZE icon."""
    px = bytearray(SIZE * SIZE * 4)
    for y in range(SIZE):
        for x in range(SIZE):
            cov = 0
            for dy in range(SS):
                for dx in range(SS):
                    sx = x + (dx + 0.5) / SS
                    sy = y + (dy + 0.5) / SS
                    if shape(sx, sy):
                        cov += 1
            a = (cov * 255) // (SS * SS)
            i = (y * SIZE + x) * 4
            px[i:i + 4] = bytes((0, 0, 0, a))  # colour patched below
    return px


def _paint(px, rgb):
    for i in range(0, len(px), 4):
        if px[i + 3]:
            px[i], px[i + 1], px[i + 2] = rgb
    return bytes(px)


def shape_play(x, y):
    """Right-pointing triangle: full-height left edge tapering to a tip at mid-right."""
    pad = 26
    top, bot = pad, SIZE - pad
    left, right = pad + 4, SIZE - pad - 2
    if y < top or y > bot or x < left or x > right:
        return False
    t = (y - top) / (bot - top)              # 0 at top, 1 at bottom
    half = 1.0 - abs(t - 0.5) * 2.0          # 0 at the ends, 1 in the middle
    edge = left + (right - left) * half
    return x <= edge


def shape_stop(x, y):
    """Rounded square - clean SDF-style test, no corner-branch tangles."""
    pad = 26
    r = 18
    x0, y0, x1, y1 = pad, pad, SIZE - pad, SIZE - pad
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    # corner quadrants: keep only pixels within the corner circle
    if x < x0 + r and y < y0 + r:
        return (x - (x0 + r)) ** 2 + (y - (y0 + r)) ** 2 <= r * r
    if x > x1 - r and y < y0 + r:
        return (x - (x1 - r)) ** 2 + (y - (y0 + r)) ** 2 <= r * r
    if x < x0 + r and y > y1 - r:
        return (x - (x0 + r)) ** 2 + (y - (y1 - r)) ** 2 <= r * r
    if x > x1 - r and y > y1 - r:
        return (x - (x1 - r)) ** 2 + (y - (y1 - r)) ** 2 <= r * r
    return True


def ico(png_bytes):
    n = len(png_bytes)
    head = struct.pack("<HHH", 0, 1, 1)
    # width/height 128 -> stored as 0
    entry = struct.pack("<BBBBHHII", 128, 128, 0, 0, 1, 32, n, 6 + 16)
    return head + entry + png_bytes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    jobs = [("start.ico", shape_play, (34, 178, 90)),     # green
            ("stop.ico", shape_stop, (214, 62, 62))]      # red
    for fn, shape, rgb in jobs:
        px = _paint(_render(shape), rgb)
        png = _png(SIZE, SIZE, px)
        data = ico(png)
        p = os.path.join(a.out, fn)
        with open(p, "wb") as f:
            f.write(data)
        print(f"[ok] {fn}  {len(data)} B (png {len(png)} B)")


def verify_ascii(path):
    """Decode the ICO's embedded PNG alpha channel and print it as ASCII art."""
    raw = open(path, "rb").read()
    i = raw.find(b"\x89PNG\r\n\x1a\n")
    pos = i + 8
    w = h = 0
    idat = b""
    while pos < len(raw):
        ln = struct.unpack(">I", raw[pos:pos + 4])[0]
        typ = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h = struct.unpack(">II", data[:8])
        elif typ == b"IDAT":
            idat += data
        elif typ == b"IEND":
            break
        pos += 12 + ln
    dec = zlib.decompress(idat)
    stride = w * 4
    ramp = " .:-=+*#%@"
    for y in range(0, h, 2):
        row = ""
        base = y * (stride + 1) + 1
        for x in range(0, w, 2):
            a = dec[base + x * 4 + 3]
            row += ramp[min(9, a * 10 // 256)]
        print(row)


if __name__ == "__main__":
    main()
