import struct

async def TextColor(writer, r, g, blue, a, c):
    packet_id = b'\x27'
    payload = struct.pack("!BBBBB", r, g, blue, a, c)

    writer.write(packet_id + payload) 
    await writer.drain()               