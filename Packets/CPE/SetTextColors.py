# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import struct

async def TextColor(writer, r, g, blue, a, c):
    packet_id = b'\x27'
    payload = struct.pack("!BBBBB", r, g, blue, a, c)

    writer.write(packet_id + payload) 
    await writer.drain()               