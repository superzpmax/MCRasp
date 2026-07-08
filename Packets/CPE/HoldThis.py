# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import struct

async def HoldThis(writer, block, allowchange):
    packet = b'\x14' + struct.pack("!BB", block, allowchange)
    writer.write(packet)
    await writer.drain()