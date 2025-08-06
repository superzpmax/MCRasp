import struct

async def HoldThis(writer, block, allowchange):
    packet = b'\x14' + struct.pack("!BB", block, allowchange)
    writer.write(packet)
    await writer.drain()