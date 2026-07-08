# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import asyncio
import time
import hashlib
import struct
from collections import defaultdict, deque

from Player import Player
import Commands.Commands as Commands
from Commands.Commands import banned_ips, banned
from Utils.Event import events

from Utils.Logger import logger
import Utils.state as state
from Utils.String import ReadString
from Utils.Confloader import conf, cosm
from Utils.DisconnectPlayer import Disconnect
from Utils.Console import ColorizeConsoleText
from Utils.CheckExtension import CheckExtension
from Packets.Position import UpdatePosition
from Packets.Message import Message
from Packets.Block import SetBlock
from Packets.Despawn import DespawnPlayer
from Packets.CPE.ExtEntry import ExtEntry
from Packets.CPE.ExtInfo import ExtInfo
from Packets.CPE.TwoWayPing import TwoWayPing
from Packets.CPE.CustomBlocks import SERVER_CB_LEVEL, CustomBlocksSendOver
from Packets.CPE.SetTextColors import TextColor
from Utils.PlayerSaveLoad import LoadPlayers

from Utils.Physics import tntQ
import Utils.BlockDefs as block_defs

block_spam = defaultdict(lambda: deque())
chat_spam = defaultdict(lambda: deque())
packet_spam = defaultdict(lambda: deque())

extinfo_temp = {}
ENABLE_LONGER_MESSAGES = True

from Utils.BlockPerms import permissions
class Packet(struct.Struct):
    def __init__(self, fmt: str, id: int):
        super().__init__("!" + fmt)
        self.id = bytes((id,))

    def pack(self, *args):
        return self.id + super().pack(*args)

    def unpack(self, data: bytes):
        return super().unpack(data)


HelloPacket          = Packet('B64s64sB', 0x00)
ClientSetBlockPacket = Packet('3h2B', 0x05)
MoveEntityPacket     = Packet('b3h2B', 0x08)
MessagePacket        = Packet('b64s', 0x0D)
ExtInfoPacket        = Packet('64sh', 0x10)
ExtEntryPacket       = Packet('64sI', 0x11)
TwoWayPingPacket     = Packet('3s', 0x2B)
CustomBlockLvl       = Packet('B', 0x13)


async def filter_recv(reader, length):
    data = b''
    while len(data) < length:
        chunk = await reader.read(length - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def _check_spam(spam_dict, key, limit, window):
    now = time.time()
    dq = spam_dict[key]
    while dq and now - dq[0] > window:
        dq.popleft()
    dq.append(now)
    return len(dq) > limit

async def _finish_cpe_join(player):

    if getattr(player, "ready", False):
        return

    await player.Start()
    await events.fire("player_join", player)

    if CheckExtension("TextColors") and state.cpe:
        try:
            from Utils.Confloader import custcolor

            for cname, vals in custcolor.get("colors", {}).items():
                r, g, b, a, ccode = vals

                if isinstance(ccode, str):
                    ccode = ord(ccode[0])

                await TextColor(player.writer, r, g, b, a, ccode)

        except Exception as e:
            logger.warning(f"[TextColors] setup failed: {e}") 
async def _handle_customblock_level(reader, writer, conn_id):
    data = await reader.readexactly(CustomBlockLvl.size)
    client_level, = CustomBlockLvl.unpack(data)

    player = state.connections.get(conn_id)

    if not player:
        return True

    player.custom_block_level = min(client_level, SERVER_CB_LEVEL)

    logger.debug(
        f"[CPE] {player.name} CustomBlocks support level: "
        f"client={client_level}, negotiated={player.custom_block_level}"
    )

    if getattr(player, "awaiting_customblocks", False):
        player.awaiting_customblocks = False
        await _finish_cpe_join(player)

    return True
async def HandleStream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    conn_id = f"{addr[0]}:{addr[1]}"
    player = state.connections.get(conn_id)

    try:
        while not state.stop:
            try:
                packet_id = await reader.read(1)

                if not packet_id:
                    break

                if _check_spam(packet_spam, conn_id, conf.get("packet-rate-limit", 200), 1):
                    await Disconnect(writer, "Too many packets!")
                    break

                if packet_id == HelloPacket.id:
                    if not await _handle_hello(reader, writer, conn_id, addr):
                        break

                elif packet_id == MessagePacket.id:
                    if not await _handle_message(reader, writer, conn_id):
                        break

                elif packet_id == ClientSetBlockPacket.id:
                    if not await _handle_block(reader, writer, conn_id):
                        break

                elif packet_id == MoveEntityPacket.id:
                    if not await _handle_move(reader, writer, conn_id, addr):
                        break

                elif packet_id == ExtInfoPacket.id:
                    await _handle_extinfo(reader, writer, conn_id)

                elif packet_id == ExtEntryPacket.id:
                    if not await _handle_extentry(reader, writer, conn_id):
                        break

                elif packet_id == TwoWayPingPacket.id:
                    await reader.readexactly(TwoWayPingPacket.size)
                    await TwoWayPing(writer)

                elif packet_id == CustomBlockLvl.id:
                    if not await _handle_customblock_level(reader, writer, conn_id):
                        break

                else:
                    logger.warning(f"Unknown packet {packet_id.hex()} from {addr}")
                    await Disconnect(writer, f"Unknown packet {packet_id.hex()}")
                    break

            except (ConnectionResetError, asyncio.IncompleteReadError):
                logger.debug(f"Connection reset by {addr}")
                break

    finally:
        await _cleanup_connection(writer, conn_id, addr)

async def _handle_hello(reader, writer, conn_id, addr):
    data = await reader.readexactly(HelloPacket.size)
    version, username_raw, mppass_raw, magic = HelloPacket.unpack(data)
    username = ReadString(username_raw)
    mppass   = ReadString(mppass_raw)

    if len(state.connections) >= state.MAX_PLAYERS:
        await Disconnect(writer, "Server full!")
        return False

    player_db = LoadPlayers()
    pdata = player_db.get(username)
    if pdata and pdata.get("banned"):
        await Disconnect(writer, "You are banned from this server.")
        return False

    if username in [p.name for p in state.players.values()]:
        await Disconnect(writer, "Username already in use.")
        return False

    if state.verifynames:
        expected = hashlib.md5((state.SALT + username).encode()).hexdigest()
        if mppass != expected:
            await Disconnect(writer, "No/Incorrect MPPass")
            return False

    player = Player(conn_id, username, addr, writer, "Minecraft Classic")
    state.connections[conn_id] = player

    if state.cpe and magic == 0x42:
        extinfo_temp[conn_id] = {
            "player": player, "expected": 0, "received": 0,
            "extensions": {}, "client": "Undefined"
        }
        await ExtInfo(writer)
        await asyncio.sleep(1)
        await ExtEntry(writer)
    else:
        await player.Start()
        await events.fire("player_join", player)
    return True

def sanitize_chat(msg: str) -> str:
    msg = msg.replace("\r\n", "\n").replace("\r", "\n")
    return msg.rstrip()

async def _handle_message(reader, writer, conn_id):
    data = await reader.readexactly(MessagePacket.size)

    player = state.connections.get(conn_id)
    if not player or not getattr(player, "ready", False):
        return True

    if state.cpe and CheckExtension("LongerMessages"):
        continues, msg_raw = MessagePacket.unpack(data)
        msg = ReadString(msg_raw)

        if ENABLE_LONGER_MESSAGES:
            if not hasattr(player, "partial_message"):
                player.partial_message = ""
            if continues:
                player.partial_message += msg
                return True
            msg = player.partial_message + msg
            player.partial_message = ""
    else:
        pid, msg_raw = MessagePacket.unpack(data)
        msg = ReadString(msg_raw)
        msg = msg.replace("\n", " ").replace("\r", "")

    if _check_spam(chat_spam, player.id, 75, 5):
        await Disconnect(player.writer, "Suspected spam! Cool-down!")
        return False
    if conf.get("require_registration", False) and not player.is_authenticated:
        if msg.startswith("/"):
            if msg.startswith("/register") or msg.startswith("/login"):
                result = await Commands.HandleCommand(player, msg, state.players, Disconnect)
                if isinstance(result, str):
                    await Player.Broadcast(result)
            else:
                player.writer.write(await Message("&cYou must /login or /register first."))
        else:
            player.writer.write(await Message("&cYou must /login or /register before chatting."))
        return True

    if msg.startswith("/"):
        result = await Commands.HandleCommand(player, msg, state.players, Disconnect)
        if isinstance(result, str):
            await Player.Broadcast(result)
    else:
        for line in msg.splitlines():
            clean = sanitize_chat(line)
            if clean:
                await _broadcast_chat(player, clean)
                await events.fire("chat_message", player, clean)

    return True




async def _broadcast_chat(player, msg):
    fmt = {
        "name": player.name,                             
        "prefix": getattr(player, "prefix", ""),          
        "display_name": f"{getattr(player, 'prefix', '')}{player.name}"  
    }

    prefix = cosm["message_prefix"].format_map(fmt)
    prefix_len = len(prefix)
    max_len = max(1, 64 - prefix_len)

    words, lines, current = msg.strip().split(), [], ""
    for word in words:
        if len(current) + len(word) + (1 if current else 0) > max_len:
            lines.append(current)
            current = word
        else:
            current += (" " if current else "") + word
    if current:
        lines.append(current)

    for i, line in enumerate(lines):
        formatted = (prefix if i == 0 else " ") + line.replace("%", "&")

        if not CheckExtension("EmoteFix"):
            formatted = formatted.replace("☺", "☺ ").replace("):", "): ")

        await Player.Broadcast(formatted)
        logger.chat(ColorizeConsoleText(formatted))



async def _handle_block(reader, writer, conn_id):
    data = await reader.readexactly(ClientSetBlockPacket.size)
    x, y, z, mode, block_type = ClientSetBlockPacket.unpack(data)

    player = state.connections.get(conn_id)

    if not player:
        return True

    if conf.get("require_registration", False) and not player.is_authenticated:
        player.writer.write(await Message("&cYou must /login or /register before building."))
        return True

    if _check_spam(block_spam, conn_id, 200, 5):
        await Disconnect(writer, "Suspected griefing! Cool-down!")
        return False

    if block_type > 49 and getattr(player, "custom_block_level", 0) < 1:
        await Disconnect(
            writer,
            f"Bad block id ({block_type})! CustomBlocks was not negotiated."
        )
        return False

    perms = permissions.get(block_type, [1, 1])

    if mode == 1 and not perms[0]:
        await Disconnect(writer, f"Not allowed to place {block_type}!")
        return False

    if mode == 0 and not perms[1]:
        await Disconnect(writer, f"Not allowed to break {block_type}!")
        return False

    if mode == 0:
        current = await player.map.GetMapBlock(x, y, z)

        if current == block_defs.TNT:
            tntQ.append((player.map.name, x, y, z))

    if not state.cpe and block_type > 49:
        await Disconnect(
            writer,
            f"Bad block id ({block_type})! (Are you using CPE? This server does not.)"
        )
        return False

    await SetBlock(x, y, z, block_type, mode, player)

    return True


async def _handle_move(reader, writer, conn_id, addr):
    try:
        data = await reader.readexactly(MoveEntityPacket.size)
        pid, x, y, z, yaw, pitch = MoveEntityPacket.unpack(data)
    except asyncio.IncompleteReadError:
        await Disconnect(writer, "Connection lost while reading MoveEntity")
        return False
    except Exception as e:
        logger.warning(f"Failed to unpack MoveEntity from {addr}: {e}")
        await Disconnect(writer, "Bad MoveEntity packet")
        return False

    player = state.connections.get(conn_id)
    if not player:
        return True

    if conf.get("require_registration", False) and not player.is_authenticated:
        spawn_x = player.map.x // 2 * 32
        spawn_y = player.map.y // 2 * 32
        spawn_z = player.map.z // 2 * 32

        player.x, player.y, player.z = spawn_x, spawn_y, spawn_z
        await UpdatePosition(player, spawn_x, spawn_y, spawn_z, 0, 0, state.players)
        return True


    player.held_block = (pid + 256) % 256



    await UpdatePosition(player, x, y, z, yaw, pitch, state.players)
    return True




async def _handle_extinfo(reader, writer, conn_id):
    data = await reader.readexactly(ExtInfoPacket.size)
    client, ext_count = ExtInfoPacket.unpack(data)
    client = client.strip(b"\x00").decode("cp437", "ignore")
    if conn_id in extinfo_temp:
        extinfo_temp[conn_id]["client"] = client
        extinfo_temp[conn_id]["expected"] = ext_count
    else:
        await Disconnect(writer, "Unexpected ExtInfo received.")


async def _handle_extentry(reader, writer, conn_id):
    data = await reader.readexactly(ExtEntryPacket.size)
    name_raw, version = ExtEntryPacket.unpack(data)

    name = name_raw.strip(b"\x00").decode("cp437", "ignore").strip()

    temp = extinfo_temp.get(conn_id)

    if not temp:
        await Disconnect(writer, "Unexpected ExtEntry received.")
        return False

    temp["extensions"][name] = version
    temp["received"] += 1

    if temp["received"] < temp["expected"]:
        return True

    player = temp["player"]
    player.client = temp.get("client", "UnknownClient")
    player.client_extensions = temp.get("extensions", {})

    del extinfo_temp[conn_id]

    client_supports_customblocks = (
        player.client_extensions.get("CustomBlocks", 0) >= 1
    )
    logger.info(f"[CPE] client_extensions={player.client_extensions}")
    logger.info(
        f"[CPE] cpe={state.cpe}, cpeblocks={state.cpeblocks}, "
        f"client_customblocks={player.client_extensions.get('CustomBlocks', 0)}"
    )
    should_use_customblocks = (
        state.cpe
        and state.cpeblocks
        and client_supports_customblocks
    )

    if should_use_customblocks:
        logger.info(f"[CPE] {player.name} supports CustomBlocks. Sending support level.")

        player.custom_block_level = 0
        player.awaiting_customblocks = True

        await CustomBlocksSendOver(writer)

        return True

    player.custom_block_level = 0
    player.awaiting_customblocks = False

    if state.cpeblocks and not client_supports_customblocks:
        logger.info(f"[CPE] {player.name} does not support CustomBlocks.")

    await _finish_cpe_join(player)

    return True

async def _cleanup_connection(writer, conn_id, addr):
    username = "Unknown"
    if conn_id in extinfo_temp:
        username = extinfo_temp[conn_id].get("username", "Unknown")
    elif conn_id in state.connections:
        username = state.connections[conn_id].name
    logger.info(f"{username} [{addr[0]}] disconnected.")

    extinfo_temp.pop(conn_id, None)
    if conn_id in state.connections:
        player = state.connections.pop(conn_id)
        await player.CleanUp()
        if player.id in state.players:
            state.players.pop(player.id)
        if player.id not in state.available_ids:
            state.available_ids.append(player.id)
            state.available_ids.sort()
        try:
            await Player.Broadcast(f"&e{player.name} left the game.")
            await DespawnPlayer(writer, player.id, state.players, player.name)
        except Exception:
            logger.exception("Error despawning player")

    try:
        writer.close()
        await writer.wait_closed()
    except (ConnectionResetError, OSError):
        pass
    except Exception:
        logger.exception("Unexpected error during writer cleanup")
