import asyncio
import yaml
from Utils.Logger import logger
from Utils.Confloader import conf

irc_writer = None

async def ListenIRC(broadcast_fn):
    logger.info("Initialized IRC Bridge.")
    global irc_writer

    if conf['irc']:

        while True:
            try:
                logger.info("Connecting to IRC...")
                reader, writer = await asyncio.open_connection(conf["server"], conf["irc-port"])
                irc_writer = writer

                writer.write(f'NICK {conf["username"]}\r\n'.encode('ascii'))
                writer.write(f'USER {conf["username"]} 0 * :{conf["username"]}\r\n'.encode('ascii'))
                await writer.drain()

                joined = False

                while True:
                    try:
                        data = await asyncio.wait_for(reader.readline(), timeout=300) 
                    except asyncio.TimeoutError:
                        logger.warning("IRC read timeout — reconnecting.")
                        break

                    if not data:
                        logger.warning("IRC disconnected — reconnecting.")
                        break

                    message = data.decode(errors='ignore').strip()

                    if message.startswith("PING"):
                        pong_response = message.replace("PING", "PONG")
                        writer.write(f"{pong_response}\r\n".encode("ascii"))
                        await writer.drain()

                    elif not joined and "001" in message:
                        writer.write(f'JOIN {conf["channel"]}\r\n'.encode('ascii'))
                        await writer.drain()
                        joined = True

                    elif " PRIVMSG " in message:
                        try:
                            user = message.split("!", 1)[0][1:]
                            content = message.split(":", 2)[2]
                            msg = f"&5[IRC] &f<{user}> {content}"
                            await broadcast_fn(msg)
                        except IndexError:
                            logger.warning("IRC PRIVMSG parse error")

            except Exception as e:
                logger.error(f"IRC connection error: {e}")

            logger.info("Reconnecting to IRC in 10 seconds...")
            await asyncio.sleep(10)

async def SendIRC(msg: str):
    global irc_writer
    if conf['irc']:
        if irc_writer:
            irc_writer.write(f"PRIVMSG {conf['channel']} :{msg}\r\n".encode('utf-8'))
            await irc_writer.drain()

