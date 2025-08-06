from Utils.String import WriteString
from Utils.state import PROTOCOL, SERVER_NAME

async def ChangeMOTD(writer, motd):
    packet = b'\x00' + PROTOCOL + WriteString(SERVER_NAME) + WriteString(motd) + b'\x42'
    writer.write(packet)
    await writer.drain()