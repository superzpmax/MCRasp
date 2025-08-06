import struct

counter = 1

async def TwoWayPing(writer):
    count = struct.pack(">H", counter+counter)
    packet = b'\x2B' + b'\x01' + count
    writer.write(packet)
    await writer.drain()