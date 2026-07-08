# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import struct
import asyncio
from Utils.String import WriteString
from Utils.Logger import logger

async def SpawnPlayer(players, writer, name, player_id):
    this_player = players[player_id]
    this_map = this_player.map

    tasks = []
    for p in players.values():
        if p.id != player_id and p.map == this_map and not p.disconnected:
            try:
                packet = (
                    b'\x07' + struct.pack('B', p.id) + WriteString(p.display_name) +
                    struct.pack('!hhh', p.x, p.y, p.z) + b'\x00\x00'
                )
                writer.write(packet)
                tasks.append(writer.drain())
            except Exception as e:
                logger.warning(f"Failed to send SpawnPlayer of {p.name} to {name}: {e}")

    packet = (
        b'\x07' + struct.pack('B', player_id) + WriteString(name) +
        struct.pack('!hhh', this_player.x, this_player.y, this_player.z) + b'\x00\x00'
    )
    for p in players.values():
        if p.id != player_id and p.map == this_map and not p.disconnected:
            try:
                p.writer.write(packet)
                tasks.append(p.writer.drain())
            except Exception as e:
                logger.warning(f"Failed to send SpawnPlayer of {name} to {p.name}: {e}")
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    try:
        writer.write(
            b'\x07' + struct.pack('B', 255) + WriteString(name) +
            struct.pack('!hhh', this_player.x, this_player.y, this_player.z) + b'\x00\x00'
        )
        await writer.drain()
    except Exception as e:
        logger.warning(f"Failed to send self-SpawnPlayer to {name}: {e}")

    try:
        pos_packet = struct.pack("!BBhhhBB", 0x08, 255,
                                 this_player.x, this_player.y, this_player.z,
                                 this_player.yaw, this_player.pitch)
        writer.write(pos_packet)
        await writer.drain()
    except Exception as e:
        logger.warning(f"Failed to send initial position to {name}: {e}")
