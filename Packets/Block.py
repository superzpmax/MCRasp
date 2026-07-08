# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import struct
from Utils.Logger import logger
from Level.Level import Map
import Utils.state as state
import asyncio


async def SetBlock(x, y, z, block_type, mode, player):
    try:
        if player is not None:
            game_map = player.map 
        else:
            from Utils.state import default_map, maps
            game_map = maps.get(default_map)
            if not game_map:
                raise ValueError("No default map loaded for physics update")

        if mode == 1:  
            await game_map.SetMapBlock(x, y, z, block_type)
            await game_map.QueuePhysics(x, y, z)
        elif mode == 0:  
            await game_map.SetMapBlock(x, y, z, 0)

        b = block_type if mode == 1 else 0
        packet = struct.pack("!BhhhB", 0x06, x, y, z, b)

    except struct.error as e:
        logger.error(f"Packing error: {e}")
        return
    except Exception as e:
        logger.error(f"setBlock error: {e}")
        return

    tasks = []
    for p in list(state.players.values()):
        if p.map == game_map and not p.disconnected:
            try:
                p.writer.write(packet)
                tasks.append(p.writer.drain())
            except (BrokenPipeError, ConnectionResetError) as e:
                logger.warning(f"Player {p.name} disconnected during block update: {e}")
            except Exception as e:
                logger.warning(f"Failed to send block update to {p.name}: {e}")

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
