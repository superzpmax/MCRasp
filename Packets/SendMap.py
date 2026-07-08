# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import struct
import gzip
import asyncio
import zlib
import concurrent.futures

from Utils.CheckExtension import CheckExtension
from Utils.Logger import logger


async def LevelInit(writer, raw_data):
    if CheckExtension("FastMap"):
        packet = b'\x02' + struct.pack("!I", len(raw_data))
    else:
        packet = b'\x02'
    writer.write(packet)
    await writer.drain()


async def LevelFin(writer, x, y, z):
    packet = b'\x04' + struct.pack('!HHH', x, y, z)
    writer.write(packet)
    await writer.drain()


def GenerateGZIP_sync(raw_data):
    uncompressed_size = len(raw_data) 
    raw = struct.pack('!I', uncompressed_size) + raw_data
    return gzip.compress(raw)


def GenerateDEFLATE_sync(raw_data):
    compressor = zlib.compressobj(wbits=-15)
    compressed = compressor.compress(raw_data)
    compressed += compressor.flush()
    return compressed

async def SendLevelData(writer, raw_data, x, y, z):
    await LevelInit(writer, raw_data)

    if CheckExtension("FastMap"):
        compressed = await asyncio.to_thread(GenerateDEFLATE_sync, raw_data)
    else:
        compressed = await asyncio.to_thread(GenerateGZIP_sync, raw_data)

    offset = 0
    length = len(compressed)

    while offset < length:
        chunk = compressed[offset:offset + 1024]
        actual_len = len(chunk)
        padded = chunk.ljust(1024, b'\x00')

        sent = offset + actual_len
        percentage = min(100, int((sent / length) * 100) if length else 100)

        writer.write(b'\x03' + struct.pack('!H', actual_len) + padded + bytes([percentage]))
        await writer.drain()
        offset = sent

    expected_len = x * y * z
    if len(raw_data) != expected_len:
        logger.error(f"BAD MAP SIZE: expected {expected_len}, got {len(raw_data)}")

    await LevelFin(writer, x, y, z)