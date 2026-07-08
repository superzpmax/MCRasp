# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import struct
from Utils.Logger import logger

SERVER_CB_LEVEL = 1


async def CustomBlocksSendOver(writer):
    packet = b"\x13" + struct.pack(">B", SERVER_CB_LEVEL)
    logger.info(f"[CPE] OUT CustomBlockSupportLevel: {packet.hex()}")

    writer.write(packet)
    await writer.drain()