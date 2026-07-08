# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import os, asyncio, struct, zstandard as zstd, random
from Utils import state
from Utils.Logger import logger
from Level.Level import Map
from Level.ClassicGen import ClassicGenerator

ENV_FORMAT = ">IIII7I"
ENV_SIZE   = struct.calcsize(ENV_FORMAT)

def pack_env(env):
    def _to_u32(v):
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            return int(v.strip().lstrip('#'), 16)
        return int(v)

    return struct.pack(
        ENV_FORMAT,
        _to_u32(env[0]), _to_u32(env[1]), _to_u32(env[2]), _to_u32(env[3]),
        _to_u32(env[4]), _to_u32(env[5]), _to_u32(env[6]),
        _to_u32(env[7]), _to_u32(env[8]), _to_u32(env[9]), _to_u32(env[10])
    )


class MapManager:
    def __init__(self, maps_dir="maps"):
        self.maps_dir = maps_dir

    def _save_one(self, game_map, name):
        path = os.path.join(self.maps_dir, f"{name}.mcr")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(struct.pack(">III", game_map.x, game_map.y, game_map.z))
            compressed = zstd.ZstdCompressor().compress(game_map.raw_data)
            f.write(compressed)
            env_bytes = pack_env(game_map.env)
            f.write(env_bytes)
            f.write(struct.pack(">I", ENV_SIZE))

    async def SaveMaps(self):
        while not state.stop:
            try:
                for name, game_map in list(state.maps.items()):
                    if not game_map.dirty:
                        continue
                    self._save_one(game_map, name)
                    game_map.dirty = False
            except Exception as e:
                logger.error(f"Failed to save maps: {e}")
            await asyncio.sleep(0.1)

    async def SaveMapOnce(self):
        try:
            for name, game_map in list(state.maps.items()):
                if not game_map.dirty:
                    continue
                self._save_one(game_map, name)
                game_map.dirty = False
        except Exception as e:
            logger.error(f"Failed to save maps: {e}")

    async def UnloadUnusedMaps(self):
        while not state.stop:
            try:
                active_maps = {p.map.name for p in state.players.values()}
                for map_name in list(state.maps.keys()):
                    if map_name not in active_maps and map_name != state.default_map:
                        logger.info(f"Unloading unused level: {map_name}")
                        try:
                            m = state.maps[map_name]
                            self._save_one(m, map_name)
                        except Exception as e:
                            logger.error(f"Failed to save map {map_name}: {e}")
                        del state.maps[map_name]
            except Exception as e:
                logger.error(f"Error in UnloadUnusedMaps: {e}")
            await asyncio.sleep(30)

    @staticmethod
    async def GenerateDefaultMap():
        game_map = state.maps[state.default_map]
        x_size, y_size, z_size = game_map.x, game_map.y, game_map.z
        generator = ClassicGenerator(x_size, y_size, z_size, seed=random.randint(0, 2147483647))
        world = generator.generate()
        for x in range(x_size):
            for y in range(y_size):
                for z in range(z_size):
                    block_id = world[x][y][z]
                    if block_id != 0:
                        await game_map.SetMapBlock(x, y, z, block_id)

    @staticmethod
    async def CreateLevel(x, y, z, spawnx, spawny, spawnz, name):
        m = Map(int(x), int(y), int(z), name)
        state.maps[name] = m
        state.default_map = name
        state.spawnX, state.spawnY, state.spawnZ = int(spawnx), int(spawny), int(spawnz)
        state.map_name = name
