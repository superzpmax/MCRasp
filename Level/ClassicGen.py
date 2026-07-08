# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import math
import random

from Utils.BlockDefs import *
from Utils.Logger import logger

def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(a, b, t):
    return a + (b - a) * t


def _grad(h, x, y):
    u = x if h < 8 else y
    v = y if h < 4 else (x if h in (12, 14) else 0.0)
    return ((u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v))


class Perlin2D:
    def __init__(self, seed: int):
        rnd = random.Random(seed)
        p = list(range(256))
        rnd.shuffle(p)
        self.perm = p + p

    def compute(self, x: float, z: float) -> float:
        X, Y = math.floor(x) & 255, math.floor(z) & 255
        xf, yf = x - math.floor(x), z - math.floor(z)
        u, v = _fade(xf), _fade(yf)
        p = self.perm
        aa = p[p[X] + Y]
        ab = p[p[X] + Y + 1]
        ba = p[p[X + 1] + Y]
        bb = p[p[X + 1] + Y + 1]
        x1 = _lerp(_grad(aa, xf, yf), _grad(ba, xf - 1, yf), u)
        x2 = _lerp(_grad(ab, xf, yf - 1), _grad(bb, xf - 1, yf - 1), u)
        return _lerp(x1, x2, v)


class OctaveNoise2D:
    def __init__(self, seed: int, octaves: int):
        self.noises = [Perlin2D(seed + i * 131) for i in range(octaves)]

    def compute(self, x: float, z: float) -> float:
        total, amp, div = 0.0, 1.0, 1.0
        for n in self.noises:
            total += n.compute(x / div, z / div) * amp
            amp *= 2.0
            div *= 2.0
        return total


class CombinedNoise2D:
    def __init__(self, n1: OctaveNoise2D, n2: OctaveNoise2D):
        self.n1, self.n2 = n1, n2

    def compute(self, x: float, z: float) -> float:
        return self.n1.compute(x + self.n2.compute(x, z), z)

class ClassicGenerator:
    def __init__(self, width: int, height: int, depth: int, seed: int):
        self.W, self.H, self.D = width, height, depth
        self.seed = seed
        self.rng = random.Random(seed)
        self.water_level = height // 2 - 1

        self.hn1 = CombinedNoise2D(OctaveNoise2D(seed + 0, 8), OctaveNoise2D(seed + 1, 8))
        self.hn2 = CombinedNoise2D(OctaveNoise2D(seed + 2, 8), OctaveNoise2D(seed + 3, 8))
        self.hn3 = OctaveNoise2D(seed + 4, 6)
        self.dirtN = OctaveNoise2D(seed + 5, 8)
        self.flowerN = OctaveNoise2D(seed + 7, 3)

        self.surfaceN = OctaveNoise2D(seed + 6, 4)

        logger.info(f"[ClassicGen] Generating a world with seed: {self.seed}")

    def create_heightmap(self):
        hm = [[0] * self.D for _ in range(self.W)]
        wl = self.water_level
        for x in range(self.W):
            for z in range(self.D):
                hLow = self.hn1.compute(x * 1.3, z * 1.3) / 6 - 4
                hHigh = self.hn2.compute(x * 1.3, z * 1.3) / 5 + 6
                hRes = hLow if self.hn3.compute(x, z) / 8 > 0 else max(hLow, hHigh)
                hRes *= 0.5
                if hRes < 0:
                    hRes *= 0.8
                hm[x][z] = int(hRes + wl)
        return hm

    def create_strata(self, hm):
        blocks = [[[AIR for _ in range(self.D)] for _ in range(self.H)] for _ in range(self.W)]
        for x in range(self.W):
            for z in range(self.D):
                dirtT = self.dirtN.compute(x, z) / 24 - 4
                dirtTr = hm[x][z]
                stoneTr = dirtTr + dirtT
                for y in range(self.H):
                    if y == 0:
                        b = LAVA
                    elif y <= stoneTr:
                        b = STONE
                    elif y <= dirtTr:
                        b = DIRT
                    else:
                        b = AIR
                    blocks[x][y][z] = b
        return blocks

    def grow_tree(self, blocks, treeX, treeY, treeZ, height):
        W, H, D = self.W, self.H, self.D
        topStart = treeY + (height - 2)

        for y in range(treeY + (height - 4), topStart):
            if y < 0 or y >= H:
                continue
            for zz in range(-2, 3):
                for xx in range(-2, 3):
                    x, z = treeX + xx, treeZ + zz
                    if 0 <= x < W and 0 <= z < D:
                        if abs(xx) == 2 and abs(zz) == 2:
                            if self.rng.random() >= 0.5:
                                blocks[x][y][z] = LEAVES
                        else:
                            blocks[x][y][z] = LEAVES

        y = topStart
        while y < treeY + height and y < H:
            for zz in range(-1, 2):
                for xx in range(-1, 2):
                    x, z = treeX + xx, treeZ + zz
                    if 0 <= x < W and 0 <= z < D:
                        if xx == 0 or zz == 0:
                            blocks[x][y][z] = LEAVES
                        elif y == topStart and self.rng.random() >= 0.5:
                            blocks[x][y][z] = LEAVES
            y += 1

        for y in range(height - 1):
            yy = treeY + y
            if 0 <= treeX < W and 0 <= yy < H and 0 <= treeZ < D:
                blocks[treeX][yy][treeZ] = LOG

    def plant_trees(self, blocks, height_map):
        logger.info("[ClassicGen] Planting Trees...")
        W, H, D = self.W, self.H, self.D
        rnd = self.rng

        numPatches = (W * D) // 4000
        for _ in range(numPatches):
            patchX = rnd.randrange(W)
            patchZ = rnd.randrange(D)

            for _j in range(20):
                treeX = patchX
                treeZ = patchZ

                for _k in range(20):
                    treeX += rnd.randrange(6) - rnd.randrange(6)
                    treeZ += rnd.randrange(6) - rnd.randrange(6)

                    if not (0 <= treeX < W and 0 <= treeZ < D):
                        continue
                    if rnd.random() >= 0.25:
                        continue

                    treeY = height_map[treeX][treeZ] + 1
                    if treeY >= H:
                        continue

                    treeHeight = 5 + rnd.randrange(3)

                    under = blocks[treeX][treeY - 1][treeZ] if treeY > 0 else AIR

                    if under == GRASS and self.tree_can_grow(blocks, treeX, treeY, treeZ, treeHeight):
                        placements = self.tree_grow_coords(treeX, treeY, treeZ, treeHeight)
                        for (px, py, pz, block_id) in placements:
                            if 0 <= px < W and 0 <= py < H and 0 <= pz < D:
                                blocks[px][py][pz] = block_id

    def tree_grow_coords(self, treeX, treeY, treeZ, height):
        W, H, D = self.W, self.H, self.D
        rnd = self.rng
        topStart = treeY + (height - 2)
        out = []

        for y in range(treeY + (height - 4), topStart):
            if y < 0 or y >= H:
                continue
            for zz in range(-2, 3):
                for xx in range(-2, 3):
                    x, z = treeX + xx, treeZ + zz
                    if 0 <= x < W and 0 <= z < D:
                        if abs(xx) == 2 and abs(zz) == 2:
                            if rnd.random() >= 0.5:
                                out.append((x, y, z, LEAVES))
                        else:
                            out.append((x, y, z, LEAVES))

        y = topStart
        while y < treeY + height:
            if 0 <= y < H:
                for zz in range(-1, 2):
                    for xx in range(-1, 2):
                        x, z = treeX + xx, treeZ + zz
                        if 0 <= x < W and 0 <= z < D:
                            if xx == 0 or zz == 0:
                                out.append((x, y, z, LEAVES))
                            elif y == topStart and rnd.random() >= 0.5:
                                out.append((x, y, z, LEAVES))
            y += 1

        for y in range(height - 1):
            yy = treeY + y
            if 0 <= yy < H:
                out.append((treeX, yy, treeZ, LOG))

        return out

    def tree_can_grow(self, blocks, treeX, treeY, treeZ, height):
        W, H, D = self.W, self.H, self.D
        topStart = treeY + (height - 2)

        for y in range(height - 1):
            yy = treeY + y
            if not (0 <= treeX < W and 0 <= yy < H and 0 <= treeZ < D):
                return False
            b = blocks[treeX][yy][treeZ]
            if b not in (AIR, LEAVES):
                return False

        for y in range(treeY + (height - 4), topStart):
            if not (0 <= y < H):
                return False
            for zz in range(-2, 3):
                for xx in range(-2, 3):
                    x, z = treeX + xx, treeZ + zz
                    if not (0 <= x < W and 0 <= z < D):
                        return False
                    b = blocks[x][y][z]
                    if b not in (AIR, LEAVES):
                        return False

        for y in range(topStart, treeY + height):
            if not (0 <= y < H):
                return False
            for zz in range(-1, 2):
                for xx in range(-1, 2):
                    x, z = treeX + xx, treeZ + zz
                    if not (0 <= x < W and 0 <= z < D):
                        return False
                    b = blocks[x][y][z]
                    if b not in (AIR, LEAVES):
                        return False

        return True
    def carve_caves(self, blocks, num_caves=10, path_length=60):
        logger.info("[ClassicGen] Carving caves...")
        W, H, D = self.W, self.H, self.D
        rnd = self.rng

        for _ in range(num_caves):
            x = rnd.randrange(W)
            y = rnd.randrange(10, H // 2)  

            z = rnd.randrange(D)

            dx = rnd.uniform(-1, 1)
            dy = rnd.uniform(-0.3, 0.3)
            dz = rnd.uniform(-1, 1)

            for step in range(path_length):
                t = step / (path_length - 1)  
                radius = int(1 + (1 - abs(0.5 - t) * 2) * 3) 

                self._carve_sphere(blocks, int(x), int(y), int(z), radius)

                x += dx
                y += dy
                z += dz

                dx += rnd.uniform(-0.2, 0.2)
                dy += rnd.uniform(-0.05, 0.05)
                dz += rnd.uniform(-0.2, 0.2)

                mag = math.sqrt(dx * dx + dy * dy + dz * dz)
                dx, dy, dz = dx / mag, dy / mag, dz / mag

                if not (2 < x < W - 2 and 2 < y < H - 2 and 2 < z < D - 2):
                    break

    def _carve_sphere(self, blocks, cx, cy, cz, radius):
      
        W, H, D = self.W, self.H, self.D
        r2 = radius * radius
        for x in range(cx - radius, cx + radius + 1):
            if not (0 <= x < W): continue
            for y in range(cy - radius, cy + radius + 1):
                if not (0 <= y < H): continue
                for z in range(cz - radius, cz + radius + 1):
                    if not (0 <= z < D): continue
                    dx, dy, dz = x - cx, y - cy, z - cz
                    if dx * dx + dy * dy + dz * dz <= r2:
                        if blocks[x][y][z] in (STONE, DIRT, GRAVEL):
                            blocks[x][y][z] = AIR
    def carve_ores(self, blocks):
        logger.info("[ClassicGen] Carving ores...")
        W, H, D = self.W, self.H, self.D
        rnd = self.rng
        ores = [
            (COAL_ORE, 40, 25, 2, (5, H - 5)), 
            (IRON_ORE, 25, 20, 2, (5, H // 2)),  
            (GOLD_ORE, 8, 15, 2, (5, H // 3)),    
        ]

        for block_id, num_veins, path_length, max_r, (minY, maxY) in ores:
            for _ in range(num_veins):
                x = rnd.randrange(W)
                y = rnd.randrange(minY, maxY)
                z = rnd.randrange(D)

                dx = rnd.uniform(-1, 1)
                dy = rnd.uniform(-0.3, 0.3)
                dz = rnd.uniform(-1, 1)

                for step in range(path_length):
                    t = step / (path_length - 1)
                    radius = int(1 + (1 - abs(0.5 - t) * 2) * (max_r - 1))

                    self._carve_ore_sphere(blocks, int(x), int(y), int(z), radius, block_id)

                    x += dx
                    y += dy
                    z += dz

                    dx += rnd.uniform(-0.2, 0.2)
                    dy += rnd.uniform(-0.05, 0.05)
                    dz += rnd.uniform(-0.2, 0.2)

                    mag = math.sqrt(dx * dx + dy * dy + dz * dz)
                    dx, dy, dz = dx / mag, dy / mag, dz / mag

                    if not (2 < x < W - 2 and 2 < y < H - 2 and 2 < z < D - 2):
                        break

    def _carve_ore_sphere(self, blocks, cx, cy, cz, radius, ore_block):
    
        W, H, D = self.W, self.H, self.D
        r2 = radius * radius
        for x in range(cx - radius, cx + radius + 1):
            if not (0 <= x < W): continue
            for y in range(cy - radius, cy + radius + 1):
                if not (0 <= y < H): continue
                for z in range(cz - radius, cz + radius + 1):
                    if not (0 <= z < D): continue
                    dx, dy, dz = x - cx, y - cy, z - cz
                    if dx * dx + dy * dy + dz * dz <= r2:
                        if blocks[x][y][z] == STONE:
                            blocks[x][y][z] = ore_block

    def generate(self):
        hm = self.create_heightmap()
        blocks = self.create_strata(hm)

        wl = self.water_level

        for x in range(self.W):
            for z in range(self.D):
                y = hm[x][z]
                if 0 <= y < self.H and blocks[x][y][z] == DIRT:
                    if 63 <= y <= 64:
                        n = self.surfaceN.compute(x * 0.1, z * 0.1)
                        blocks[x][y][z] = SAND if n > 0 else GRASS
                    else:
                        blocks[x][y][z] = GRASS

                for yy in range(min(self.H, wl + 1)):
                    if blocks[x][yy][z] == AIR:
                        blocks[x][yy][z] = WATER

                if y < 63 and blocks[x][y][z] == GRASS:
                    blocks[x][y][z] = GRAVEL

                if blocks[x][y][z] == GRASS:
                    fn = self.flowerN.compute(x * 0.75, z * 0.86)
                    if fn > 0.5 and y + 1 < self.H:
                        if fn > 0.7:
                            blocks[x][y + 1][z] = ROSE
                        else:
                            blocks[x][y + 1][z] = FLOWER

        self.plant_trees(blocks, hm)

        self.carve_caves(blocks, num_caves=32, path_length=80)
        self.carve_ores(blocks)
        logger.info("[ClassicGen] Finished!")
        return blocks

