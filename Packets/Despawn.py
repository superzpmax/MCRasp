import struct
import asyncio
from Utils.Logger import logger

async def DespawnPlayer(writer, player_id, players, name):
    packet = b'\x0c' + struct.pack('b', player_id)
    this_player = players.get(player_id)

    if not this_player:
        return

    tasks = []
    for p in players.values():
        if p.id != player_id and p.map == this_player.map and not p.disconnected:
            try:
                p.writer.write(packet)
                tasks.append(p.writer.drain())
            except Exception as e:
                logger.warning(f"Failed to queue DespawnPlayer for {name} to {p.name}: {e}")

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
