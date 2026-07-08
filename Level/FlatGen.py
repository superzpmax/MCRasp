# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.
from Utils.BlockDefs import *

class FlatGenerator:
    def __init__(self, width, height, depth):
        self.W, self.H, self.D = width, height, depth
        self.water_level = height // 2 - 1

        self.blocks = [[[0 for _ in range(depth)] 
                           for _ in range(height)] 
                           for _ in range(width)]
        
    def generate(self):
        for x in range(self.W):
            for z in range(self.D):
                self.blocks[x][self.water_level][z] = GRASS

        for x in range(self.W):
            for y in range(self.water_level):   
                for z in range(self.D):         
                    self.blocks[x][y][z] = DIRT

        for x in range(self.W):
            for y in range(self.water_level - 5):
                for z in range(self.D):        
                    self.blocks[x][y][z] = STONE

        return self.blocks
