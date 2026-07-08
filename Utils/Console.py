# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import asyncio
import re

from Commands.Commands import HandleCommand
import Utils.state as state
from Utils.DisconnectPlayer import Disconnect
from Utils.ConsoleColors import COLORS, RESET_COLOR
from Utils.Confloader import conf
from Utils.Logger import logger
def ColorizeConsoleText(msg: str) -> str:
    parts = re.split(r'(&[0-9a-fA-F])', msg)
    result = ''
    current_color = COLORS.get('&f', '')

    for part in parts:
        if part.lower() in COLORS:
            current_color = COLORS[part.lower()]
        else:
            result += f"{current_color}{part}"

    result += RESET_COLOR 
    return result

CONSOLE_BLOCKED_COMMANDS = {"tp", "tpp", "place", "cuboid"} 

async def ListenConsole():
    loop = asyncio.get_event_loop()
    while not state.stop:
        try:
            cmd_text = await loop.run_in_executor(None, input, "> ")
            if not cmd_text.strip():
                continue
            if not cmd_text.startswith("/"):
                cmd_text = "/" + cmd_text 

            cmd_name = cmd_text[1:].split()[0].lower()
            if cmd_name in CONSOLE_BLOCKED_COMMANDS:
                logger.warning(f"Console command '{cmd_name}' is blocked.")
                continue
            class DummyWriter:
                def write(self, data):
                    try:
                        text = data.decode(errors="ignore") if isinstance(data, bytes) else str(data)
                    except Exception:
                        text = str(data)
                    logger.info(f"[Console Writer] {ColorizeConsoleText(text)}")

                async def drain(self):
                    pass

                def close(self):
                    pass

                async def wait_closed(self):
                    pass

            class ConsolePlayer:
                name = "Console"
                writer = DummyWriter()
                Disconnected = False
                permissions = {"*": True}
                IsConsole = True 
                def has_permission(self, node: str) -> bool:
                    if getattr(self, "IsConsole", False):
                        return True
                    return self.permissions.get(node, self.permissions.get("*", False))





            console_player = ConsolePlayer()

            result = await HandleCommand(console_player, cmd_text, state.players, Disconnect)

            if isinstance(result, str):
                logger.info(result)
                # await Player.Broadcast(result)

        except EOFError:
            break
        except Exception as e:
            logger.error(f"Error in console input: {e}")
