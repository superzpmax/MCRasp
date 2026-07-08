# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

from Utils.state import cpe
from Packets.Message import Message as BuildMessage 

async def SendMessage(writer, message):
    if cpe:
        for packet in await BuildMessage(message):
            writer.write(packet)
            await writer.drain()
    else:
        writer.write(await BuildMessage(message))
        await writer.drain()
