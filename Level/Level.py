import struct
import zstandard as zstd
from Utils.Confloader import conf
from Utils.Logger import logger
import Utils.state as state
from Packets.SendMap import SendLevelData
from Utils.state import physics_queue

ENV_FORMAT = ">IIII7I"
ENV_SIZE   = struct.calcsize(ENV_FORMAT)

class Map:
    ENV_KEYS = [
        "fog", "sky", "sunlight", "shadow",
        "weather", "weatherspeed", "cloudspeed", "clouds",
        "waterlevel", "horizon", "border"
    ]

    def __init__(self, x, y, z, name=None, client=None, env=None):
        self.x, self.y, self.z = x, y, z
        self.name = name
        self.client = client
        self.block_count = x * y * z
        self.raw_data = bytearray(b'\x00' * self.block_count)
        self.dirty = False
        self.env = env or conf.get("default-env", [0] * 11)

    def set_env(self, key, value):
        if key not in self.ENV_KEYS:
            raise KeyError(f"Invalid env key: {key}")
        idx = self.ENV_KEYS.index(key)
        self.env[idx] = int(value)

    def get_env(self, key):
        if key not in self.ENV_KEYS:
            raise KeyError(f"Invalid env key: {key}")
        return self.env[self.ENV_KEYS.index(key)]

    async def index(self, x, y, z):
        return y * self.z * self.x + z * self.x + x

    async def SetMapBlock(self, x, y, z, block_type):
        if 0 <= x < self.x and 0 <= y < self.y and 0 <= z < self.z:
            self.raw_data[await self.index(x, y, z)] = block_type
            self.dirty = True

    async def QueuePhysics(self, x, y, z):
        physics_queue.add((self.name, x, y, z))
        physics_queue.add((self.name, x, y - 1, z))


    async def GetMapBlock(self, x, y, z):
        if 0 <= x < self.x and 0 <= y < self.y and 0 <= z < self.z:
            return self.raw_data[await self.index(x, y, z)]
        return 0  


    async def SendLevel(self, writer):
        await SendLevelData(writer, self.raw_data, self.block_count, self.x, self.y, self.z)

    def SaveToFile(self, path: str):
        with open(path, "wb") as f:
            f.write(struct.pack(">III", self.x, self.y, self.z))
            compressed = zstd.ZstdCompressor().compress(self.raw_data)
            f.write(compressed)
            env_bytes = struct.pack(
                ENV_FORMAT,
                int(self.env[0]), int(self.env[1]), int(self.env[2]), int(self.env[3]),
                int(self.env[4]), int(self.env[5]), int(self.env[6]),
                int(self.env[7]), int(self.env[8]), int(self.env[9]), int(self.env[10])
            )
            f.write(env_bytes)
            f.write(struct.pack(">I", ENV_SIZE))

    @staticmethod
    def LoadFromFile(path: str, name="unknown", client=None):
        with open(path, "rb") as f:
            data = f.read()

        if len(data) < 12 + ENV_SIZE + 4:
            raise ValueError("Map file too short")

        x, y, z = struct.unpack_from(">III", data, 0)

        env_len = struct.unpack_from(">I", data, len(data) - 4)[0]
        if env_len != ENV_SIZE:
            raise ValueError(f"Invalid environment length (got {env_len}, expected {ENV_SIZE})")

        env_start = len(data) - 4 - ENV_SIZE
        env_bytes = data[env_start:env_start+ENV_SIZE]
        env = list(struct.unpack(ENV_FORMAT, env_bytes))

        blocks_region = data[12:env_start]
        raw_blocks = zstd.ZstdDecompressor().decompress(blocks_region)

        expected = x * y * z
        if len(raw_blocks) != expected:
            raise ValueError(f"Block size mismatch: got {len(raw_blocks)} expected {expected}")

        if not name:
            import os
            name = os.path.splitext(os.path.basename(path))[0]

        m = Map(x, y, z, name, client, env)
        m.raw_data[:] = raw_blocks
        m.dirty = False
        return m
