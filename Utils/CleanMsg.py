from Utils.state import cpe
from Packets.Message import Message as BuildMessage 

async def SendMessage(writer, message):
    if cpe:
        for packet in await BuildMessage(message):
            writer.write(packet)
            await writer.drain()
    else:
        writer.write(await BuildMessage(message))
        await writer.drain()
