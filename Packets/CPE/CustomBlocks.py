import struct
from Utils.Logger import logger

SERVER_CB_LEVEL = 1


async def CustomBlocksSendOver(writer):
    packet = b"\x13" + struct.pack(">B", SERVER_CB_LEVEL)
    logger.info(f"[CPE] OUT CustomBlockSupportLevel: {packet.hex()}")

    writer.write(packet)
    await writer.drain()