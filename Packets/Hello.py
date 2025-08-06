

from Utils.String import WriteString
from Utils.state import PROTOCOL, SERVER_NAME, MOTD

async def Hello(writer):
    packet = b'\x00' + PROTOCOL + WriteString(SERVER_NAME) + WriteString(MOTD) + b'\x42'
    writer.write(packet)
    await writer.drain()