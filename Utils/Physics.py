import asyncio
from collections import deque
import random
import Utils.BlockDefs as block_defs
from Packets.Block import SetBlock
from Utils.state import physics_queue
import Utils.state as state

class TickQueue:
    def __init__(self): self.entries = deque()
    def clear(self): self.entries.clear()
    def enqueue(self, item): self.entries.append(item)
    def dequeue(self): return self.entries.popleft()
    def __len__(self): return len(self.entries)

lavaQ, waterQ = TickQueue(), TickQueue()
LAVA_DELAY, WATER_DELAY = 2, 1
tntQ = deque()
active_tnt = set()
fusing_tnt = set()
async def BlockUpdate(game_map, x, y, z, block_id):
    for p in state.players.values():
        if p.map == game_map:
            await SetBlock(x, y, z, block_id, 1, p)

async def Physics_ExplodeTnt(game_map, x, y, z):
    pos = (game_map.name, x, y, z)
    if pos in active_tnt:
        return

    fusing_tnt.add(pos)
    active_tnt.add(pos)
    try:
        for _ in range(6):
            await game_map.SetMapBlock(x, y, z, block_defs.WHITE_CLOTH)
            await BlockUpdate(game_map, x, y, z, block_defs.WHITE_CLOTH)
            await asyncio.sleep(0.3)

            await game_map.SetMapBlock(x, y, z, block_defs.TNT)
            await BlockUpdate(game_map, x, y, z, block_defs.TNT)
            await asyncio.sleep(0.3)

        radius = 4
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if dx*dx + dy*dy + dz*dz <= radius*radius:
                        if random.random() < 0.75:
                            nx, ny, nz = x + dx, y + dy, z + dz
                            if 0 <= nx < game_map.x and 0 <= ny < game_map.y and 0 <= nz < game_map.z:
                                block = await game_map.GetMapBlock(nx, ny, nz)
                                if block == block_defs.TNT:
                                    await game_map.SetMapBlock(nx, ny, nz, block_defs.AIR)
                                    await BlockUpdate(game_map, nx, ny, nz, block_defs.AIR)
                                else:
                                    await game_map.SetMapBlock(nx, ny, nz, block_defs.AIR)
                                    await BlockUpdate(game_map, nx, ny, nz, block_defs.AIR)
    finally:
        active_tnt.remove(pos)


async def Physics_PlaceLava(game_map, x, y, z):
    lavaQ.enqueue((x, y, z, LAVA_DELAY))

async def Physics_PlaceWater(game_map, x, y, z):
    waterQ.enqueue((x, y, z, WATER_DELAY))

async def Physics_PropagateLava(game_map, x, y, z):
    bid = await game_map.GetMapBlock(x, y, z)
    if bid in (block_defs.WATER, block_defs.STATIONARY_WATER):
        await game_map.SetMapBlock(x, y, z, block_defs.STONE)
        await BlockUpdate(game_map, x, y, z, block_defs.STONE)
    elif bid == block_defs.AIR:
        await game_map.SetMapBlock(x, y, z, block_defs.LAVA)
        await BlockUpdate(game_map, x, y, z, block_defs.LAVA)
        lavaQ.enqueue((x, y, z, LAVA_DELAY))

async def Physics_PropagateWater(game_map, x, y, z):
    bid = await game_map.GetMapBlock(x, y, z)
    if bid in (block_defs.LAVA, block_defs.STATIONARY_LAVA):
        await game_map.SetMapBlock(x, y, z, block_defs.STONE)
        await BlockUpdate(game_map, x, y, z, block_defs.STONE)
    elif bid == block_defs.AIR:
        await game_map.SetMapBlock(x, y, z, block_defs.WATER)
        await BlockUpdate(game_map, x, y, z, block_defs.WATER)
        waterQ.enqueue((x, y, z, WATER_DELAY))

async def Physics_ActivateLava(game_map, x, y, z):
    if x > 0: await Physics_PropagateLava(game_map, x - 1, y, z)
    if x < game_map.x - 1: await Physics_PropagateLava(game_map, x + 1, y, z)
    if z > 0: await Physics_PropagateLava(game_map, x, y, z - 1)
    if z < game_map.z - 1: await Physics_PropagateLava(game_map, x, y, z + 1)
    if y > 0: await Physics_PropagateLava(game_map, x, y - 1, z)

async def Physics_ActivateWater(game_map, x, y, z):
    if x > 0: await Physics_PropagateWater(game_map, x - 1, y, z)
    if x < game_map.x - 1: await Physics_PropagateWater(game_map, x + 1, y, z)
    if z > 0: await Physics_PropagateWater(game_map, x, y, z - 1)
    if z < game_map.z - 1: await Physics_PropagateWater(game_map, x, y, z + 1)
    if y > 0: await Physics_PropagateWater(game_map, x, y - 1, z)

async def Physics_DoFalling(game_map, x, y, z, block_id):
    if y == 0: return
    ny = y
    while ny > 0:
        below = await game_map.GetMapBlock(x, ny - 1, z)
        if below == block_defs.AIR or below in (
            block_defs.WATER, block_defs.STATIONARY_WATER,
            block_defs.LAVA, block_defs.STATIONARY_LAVA
        ):
            ny -= 1
        else: break
    if ny != y:
        await game_map.SetMapBlock(x, ny, z, block_id)
        await BlockUpdate(game_map, x, ny, z, block_id)
        await game_map.SetMapBlock(x, y, z, block_defs.AIR)
        await BlockUpdate(game_map, x, y, z, block_defs.AIR)

async def PhysicsComp(game_map, x, y, z):
    bid = await game_map.GetMapBlock(x, y, z)

    if bid == block_defs.LAVA:
        await Physics_PlaceLava(game_map, x, y, z)

    elif bid == block_defs.WATER:
        await Physics_PlaceWater(game_map, x, y, z)

    elif bid in (block_defs.SAND, block_defs.GRAVEL):
        await Physics_DoFalling(game_map, x, y, z, bid)


async def Physics_Tick(game_map):
    for _ in range(len(lavaQ)):
        x, y, z, delay = lavaQ.dequeue()
        if delay > 0: lavaQ.enqueue((x, y, z, delay - 1))
        else:
            bid = await game_map.GetMapBlock(x, y, z)
            if bid in (block_defs.LAVA, block_defs.STATIONARY_LAVA):
                await Physics_ActivateLava(game_map, x, y, z)

    for _ in range(len(waterQ)):
        x, y, z, delay = waterQ.dequeue()
        if delay > 0: waterQ.enqueue((x, y, z, delay - 1))
        else:
            bid = await game_map.GetMapBlock(x, y, z)
            if bid in (block_defs.WATER, block_defs.STATIONARY_WATER):
                await Physics_ActivateWater(game_map, x, y, z)

    for _ in range(len(physics_queue)):
        mapname, qx, qy, qz = physics_queue.pop()
        if game_map.name == mapname:
            await PhysicsComp(game_map, qx, qy, qz)

