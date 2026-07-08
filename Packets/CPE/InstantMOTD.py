# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

from Utils.String import WriteString
from Utils.state import PROTOCOL, SERVER_NAME

async def ChangeMOTD(writer, motd):
    packet = b'\x00' + PROTOCOL + WriteString(SERVER_NAME) + WriteString(motd) + b'\x42'
    writer.write(packet)
    await writer.drain()