# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

from Utils.BlockPerms import permissions

async def SetPermissionsBlocks(writer):
    for block_id, values in permissions.items():
        allow, dele = values[0], values[1]      
        packet = b'\x1C' + bytes([block_id, allow, dele])
        writer.write(packet)
        await writer.drain()
