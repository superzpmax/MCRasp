import struct
from Utils.String import WriteString
def WorldSelection(id, label, sx, sy, sz, ex, ey, ez, r, g, b, a):
    return b'\x1A' + struct.pack(
        "!B64s10h",
        id,
        WriteString(label),
        sx, sy, sz,
        ex, ey, ez,
        r, g, b, a
    )

def RemoveSelection(id):
    return b'\x1B' + bytes(id)