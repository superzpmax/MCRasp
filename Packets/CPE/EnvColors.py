# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import struct
from Utils.String import WriteString
from Packets.Message import Message
import Utils.state as state
from Utils.Logger import logger

ENV_COLOR_PROPS = {
    'sky': 0,
    'cloud': 1,       
    'clouds': 1,
    'fog': 2,
    'ambient': 3,      
    'shadow': 3,      
    'sunlight': 4
}

async def SetEnvColor(writer, prop, r, g, b, players, glob):
    if isinstance(prop, str):
        prop = ENV_COLOR_PROPS.get(prop.lower())

    if prop is None or prop > 4:
        err_msg = await Message("Invalid env property!")
        writer.write(err_msg)
        await writer.drain()
        return


    colors = struct.pack("!HHH", r, g, b)
    packet = b'\x19' + struct.pack("!b", prop) + colors
    if glob:
        for p in list(players.values()):
            try:
                p.writer.write(packet)
                await p.writer.drain()
            except (BrokenPipeError, ConnectionResetError) as e:
                logger.warning(f"Player {p.name} disconnected during block update: {e}")
            except Exception as e:
                logger.warning(f"Failed to send block update to {p.name}: {e}")
    else:
        writer.write(packet)
        await writer.drain()
