from Utils.Logger import logger
from Utils.String import WriteString

async def Disconnect(writer, reason: str):
    try:
        writer.write(b'\x0e' + WriteString(reason))
        await writer.drain()
        logger.info(f"Disconnected for: {reason}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except (ConnectionResetError, OSError):
            pass
