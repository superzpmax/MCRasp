# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import struct

counter = 1

async def TwoWayPing(writer):
    count = struct.pack(">H", counter+counter)
    packet = b'\x2B' + b'\x01' + count
    writer.write(packet)
    await writer.drain()