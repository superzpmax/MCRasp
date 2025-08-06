import struct
import asyncio
from Utils.Logger import logger

async def UpdatePosition(player, x, y, z, yaw, pitch, players_dict):
    player.x = x
    player.y = y
    player.z = z
    player.yaw = yaw
    player.pitch = pitch

    try:
        packet = struct.pack(">BBhhhBB", 0x08, player.id, x, y, z, yaw, pitch)
    except struct.error as e:
        logger.error(f"UpdatePosition packing failed: {e}")
        return

    tasks = []
    for other in players_dict.values():
        if other.id != player.id and not other.disconnected:
            try:
                other.writer.write(packet)
                tasks.append(other.writer.drain())
            except Exception as e:
                logger.warning(f"Couldn't queue pos of {player.name} to {other.name}: {e}")

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
