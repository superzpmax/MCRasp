# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

from Utils.state import SOFTWARE
from Utils.Confloader import extensions
from Utils.String import WriteString
from Utils.Logger import logger
import struct

async def ExtInfo(writer):
    ext_count = len(extensions['extensions'])
    packet = b'\x10' + WriteString(SOFTWARE) + struct.pack(">H", ext_count)
    writer.write(packet)
    await writer.drain()