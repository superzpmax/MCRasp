# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import numpy as np
import Utils.BlockDefs as block
import random
from noise import snoise2, pnoise3
from Utils.Logger import logger

class AdvGen:
    def __init__(self, shape, height, seed):
        self.shape = shape
        self.height = height
        self.seed = seed

    def CalculateTemp(self):
        logger.info("[AdvGen] Calculating temperatures...")
        temp = np.zeros(self.shape, dtype=int)
        width, length = self.shape
        for x in range(width):
            for z in range(length):
                noise_val = snoise2(
                    x / 235,
                    z / 235,
                    octaves=8,
                    persistence=0.5,
                    lacunarity=2.0,
                    base=self.seed
                )
                peak_val = snoise2(
                    x / 235,
                    z / 235,
                    octaves=6,
                    persistence=0.6,
                    lacunarity=2.0,
                    base=self.seed*2
                )
                normalized_peak = (peak_val + 1) / 2

                threshold = 0.75
                if normalized_peak < threshold:
                    peak_contribution = 0
                else:
                    peak_contribution = (normalized_peak - threshold) / (1 - threshold)

                peak_height = int(peak_contribution * 15) / 2
                normalized = (noise_val + 1) / 2
                elevation = int(normalized * self.height) - 2

                if elevation > (63+8):
                    excess = elevation - (63+8)
                    elevation = (63+8) + int(excess * 0.23)

                if elevation < (63):
                    excess = elevation - (63)
                    elevation = (63) + int(excess * 0.45) 


                temp[x, z] = int(elevation + int((peak_height + 1) / 2 * 5))

        return temp
        
    def GenerateTrees(self):
        trunk_height = int(random.uniform(3, 5))
        tree = []

        for y in range(trunk_height):
            tree.append((0, y, 0, block.LOG))

        canopy_radius = 3 
        canopy_center_y = trunk_height

        for dx in range(-canopy_radius, canopy_radius + 1):
            for dy in range(-canopy_radius, canopy_radius + 1):
                for dz in range(-canopy_radius, canopy_radius + 1):
                    if dx**2 + dy**2 + dz**2 <= canopy_radius**2:
                        tree.append((dx, canopy_center_y + dy, dz, block.LEAVES))


        return tree

    def GenerateMap(self):
        waterLevel = 63
        temp = self.CalculateTemp()
        width, length = temp.shape
        max_height = int(max(np.max(temp) + 1, waterLevel + 3))

        logger.info(f"[AdvGen] Generating world...")

        world = np.zeros((width, max_height, length), dtype=int)

        logger.info("[AdvGen] Flooding and making details...")
        for x in range(width):
            for z in range(length):
                h = temp[x, z]
                if h < 0:
                    continue

                if h > 0:
                    dirt_depth = 3
                    stone_top = max(0, h - dirt_depth)
                    world[x, 0:stone_top, z] = block.STONE
                    world[x, stone_top:h, z] = block.DIRT

                world[x, h, z] = block.GRASS
        
                for y in range(h + 1, waterLevel + 1):
                    if world[x, y, z] == block.AIR:
                        world[x, y, z] = block.STATIONARY_WATER

                if h <= 65:
                    if world[x, h, z] == block.GRASS:
                        world[x, h, z] = block.SAND
                    if h > 1 and world[x, h - 1, z] == block.DIRT:
                        world[x, h - 1, z] = block.GRAVEL

                for y in range(0, (waterLevel-5)):
                    if world[x, y, z] == block.SAND:
                        world[x, y, z] = block.GRAVEL

        logger.info("[AdvGen] Carving caves...")
        for x in range(width):
            for y in range(max_height):
                for z in range(length):
                    nx = x / 23
                    ny = y / 8
                    nz = z / 23

                    noise_val = pnoise3(nx, ny, nz, octaves=3, base=self.seed*3)

                    if noise_val > 0.3:
                        if world[x, y, z] not in (block.SAND, block.STATIONARY_WATER, block.GRAVEL):
                            world[x, y, z] = block.AIR
            
        logger.info("[AdvGen] Flooding with lava...")
        for x in range(width):
            for z in range(length):
                h = temp[x, z]
                for y in range(0, 7):
                    if world[x, y, z] == block.AIR:
                        world[x, y, z] = block.STATIONARY_LAVA

        logger.info("[AdvGen] Placing bedrock...")
        for x in range(width):
            for z in range(length):
                world[x, 0, z] = 7
                world[x, 1, z] = 7

        logger.info("[AdvGen] Fixing grass...")
        for x in range(width):
            for y in range(max_height - 1): 
                for z in range(length):
                    if world[x, y+1, z] == block.AIR and world[x, y, z] == block.DIRT:
                        world[x, y, z] = block.GRASS

        logger.info("[AdvGen] Placing trees...")
        tree_density = 0.005  
        for x in range(2, width - 2):
            for z in range(2, length - 2):
                if random.random() < tree_density:
                    y = temp[x, z]
                    if world[x, y, z] == block.GRASS:
                        tree = self.GenerateTrees()
                        for dx, dy, dz, block_id in tree:
                            tx = x + dx
                            ty = y + dy + 1 
                            tz = z + dz

                            if 0 <= tx < width and 0 <= ty < max_height and 0 <= tz < length:
                                if world[tx, ty, tz] in (block.AIR, block.LEAVES):
                                    world[tx, ty, tz] = block_id
        
        logger.info("[AdvGen] Placing ores...")
        for x in range(width):
            for y in range(max_height):
                for z in range(length):
                    nx = x / 8
                    ny = y / 8
                    nz = z / 8

                    noise_val = pnoise3(nx, ny, nz, octaves=3, base=self.seed*3)

                    if world[x, y, z] == block.STONE:
                        if noise_val > 0.38:
                            world[x, y, z] = block.BLUE_CLOTH
                            noise_val = pnoise3(nx, ny, nz, octaves=3, base=self.seed*4)
                        elif noise_val > 0.35:
                            world[x, y, z] = block.GOLD_ORE
                            noise_val = pnoise3(nx, ny, nz, octaves=3, base=self.seed*5)
                        elif noise_val > 0.325:
                            world[x, y, z] = block.IRON_ORE
                            noise_val = pnoise3(nx, ny, nz, octaves=3, base=self.seed*6)
                        elif noise_val > 0.3:
                            world[x, y, z] = block.COAL_ORE



        logger.info("[AdvGen] Finished generating!")
        return world