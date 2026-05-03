import zlib, struct, math, os

def make_png(size):
    def chunk(name, data):
        c = zlib.crc32(name + data) & 0xffffffff
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", c)

    bg  = (10, 45, 110)
    mid = (13, 110, 253)
    wh  = (255, 255, 255)

    cx = cy = size / 2
    ro = size * 0.38
    rw = size * 0.06
    ri = size * 0.20

    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            d = math.hypot(x - cx, y - cy)
            t = y / size
            r0 = int(bg[0] + (mid[0] - bg[0]) * t)
            g0 = int(bg[1] + (mid[1] - bg[1]) * t)
            b0 = int(bg[2] + (mid[2] - bg[2]) * t)
            if abs(d - ro) < rw:
                raw.extend(wh)
            elif d < ri:
                raw.extend(wh)
            else:
                raw.extend([r0, g0, b0])

    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend

base = os.path.dirname(os.path.abspath(__file__))
for s in [192, 512]:
    path = os.path.join(base, f"icon-{s}.png")
    with open(path, "wb") as f:
        f.write(make_png(s))
    print(f"Genere : icon-{s}.png")
