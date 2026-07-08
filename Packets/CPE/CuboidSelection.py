# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

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