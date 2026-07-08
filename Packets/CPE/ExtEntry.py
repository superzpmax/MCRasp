# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import struct
from Utils.String import WriteString
from Utils.Confloader import extensions 
from Utils.Logger import logger

async def ExtEntry(writer):
    for ext_name, version in extensions['extensions'].items():
        name_bytes = WriteString(ext_name).ljust(64, b'\x00')[:64]
        version_bytes = struct.pack(">I", version)
        packet = b'\x11' + name_bytes + version_bytes
        writer.write(packet)
        await writer.drain()