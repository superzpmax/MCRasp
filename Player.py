# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import os
import struct
import asyncio
import datetime
import yaml

from Utils.Logger import logger
from Utils.state import (
    players, connections, SOFTWARE, SERVER_NAME, PORT, PROTOCOL,
    next_id, MAX_ID, MOTD, spawnX, spawnY, spawnZ,
    available_ids, cpe, maps, default_map, PROJECT_ROOT, GROUPS_F
)
import Utils.state as state
from Utils.Confloader import conf
from Utils.PlayerSaveLoad import LoadPlayers, SavePlayers
from Utils.CheckExtension import CheckExtension

from Packets.Hello import Hello
from Packets.SendMap import SendLevelData
from Packets.Message import Message
from Packets.Spawn import SpawnPlayer
from Packets.Despawn import DespawnPlayer
from Packets.CPE.EnvColors import SetEnvColor
from Packets.CPE.BlockPermissions import SetPermissionsBlocks
from Packets.CPE.TwoWayPing import TwoWayPing
from Packets.CPE.HoldThis import HoldThis
from Packets.CPE.InstantMOTD import ChangeMOTD
from Packets.CPE.CuboidSelection import WorldSelection


ENV_COLOR_KEYS = {
    "sky": 1,
    "cloud": 7,
    "fog": 0,
    "sunlight": 2,
    "ambient": 3,
}


def resource_path(relative_path: str) -> str:
    return os.path.join(PROJECT_ROOT, relative_path)


def load_groups():
    try:
        with open(GROUPS_F, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed loading groups: {e}")
        return {}


GROUPS = load_groups()


def GetPermissionsFromGroup(group_list):
    merged, prioritized = {}, []
    for group in group_list:
        data = GROUPS.get(group)
        if isinstance(data, dict):
            prioritized.append((data.get("priority", 0), group))
    for _, group in sorted(prioritized):
        merged.update(GROUPS[group].get("permissions", {}))
    return merged

class Player:
    def __init__(self, conn_key, name, addr, writer, client):
        self.session_started_at = datetime.datetime.now()
        self._stats_committed = False
        self._write_lock = asyncio.Lock()
        self.disconnected = False
        self.IsConsole = False
        self.is_authenticated = not conf.get("require_registration", False)

        self.conn_key = conn_key
        self.name = name
        self.addr = addr
        self.writer = writer
        self.client = client 

        self.spawnX, self.spawnY, self.spawnZ = spawnX, spawnY, spawnZ
        self.x, self.y, self.z = spawnX * 32, spawnY * 32, spawnZ * 32
        self.yaw, self.pitch = 0, 0
        self.ready = False
        self.map = state.maps[state.default_map]

        self.id = self._assign_player_id()

        players[self.id] = self
        connections[self.conn_key] = self
        logger.info(f"{self.name} [{self.addr[0]}] connected.")

    @property
    def display_name(self):
        return f"{self.prefix}{self.name}"
    def _assign_player_id(self):
        global next_id
        if available_ids:
            return available_ids.pop(0)
        assigned = next_id
        next_id = 1 if next_id >= MAX_ID else next_id + 1
        while next_id in players:
            next_id = 1 if next_id >= MAX_ID else next_id + 1
        return assigned

    async def switch_map(self, new_map):
        old_map = self.map
        for p in list(players.values()):
            if p != self and p.map == old_map:
                try:
                    packet = b"\x0c" + struct.pack("b", self.id)
                    p.writer.write(packet)
                    await p.writer.drain()
                except Exception as e:
                    logger.warning(f"Failed to despawn {self.name} from {p.name}: {e}")

        self.map = new_map
        self.x, self.y, self.z = new_map.spawnX * 32, new_map.spawnY * 32, new_map.spawnZ * 32
        await self.level()
        await SpawnPlayer(players, self.writer, self.display_name, self.id)

    async def welcome_msg(self):
        path = resource_path("extra/welcome.txt")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as wel:
                    for line in wel:
                        self.writer.write(await Message(line.strip()))
            except Exception as e:
                logger.warning(f"Failed sending welcome.txt to {self.name}: {e}")

    async def Start(self):
        await Hello(self.writer)
        await self.level()
        if (
            cpe
            and getattr(self, "client_extensions", {}).get("BlockPermissions", 0) >= 1
        ):
            await SetPermissionsBlocks(self.writer)

        await self.register_player()
        await SpawnPlayer(players, self.writer, self.display_name, self.id)
        await self.welcome_msg()
        await Player.Broadcast(f"&e{self.display_name}&e joined the game.")
        self.ready = True

        if cpe:
            await TwoWayPing(self.writer)

        if conf.get("require_registration", False):
            players_data = LoadPlayers()
            pdata = players_data.get(self.name, {})
            if pdata.get("registered"):
                self.is_authenticated = False
                self.writer.write(await Message("&ePlease /login with your password."))
            else:
                self.is_authenticated = False
                self.writer.write(await Message("&eYou must /register <password> to play."))
        else:
            self.is_authenticated = True
    async def level(self):

        await SendLevelData(self.writer, self.map.raw_data, self.map.x, self.map.y, self.map.z)

        env = getattr(self.map, "env", None)
        if CheckExtension("EnvColors") and cpe:
            if isinstance(env, list) and len(env) >= 8:
                try:
                    for prop_name, index in ENV_COLOR_KEYS.items():
                        hex_color = env[index]
                        if isinstance(hex_color, str):
                            r, g, b = self.hex_to_rgb(hex_color)
                            await SetEnvColor(self.writer, prop_name, r, g, b, players=state.players, glob=False)
                except Exception as e:
                    logger.warning(f"Failed to send env colors to {self.name}: {e}")

    async def register_player(self):
       
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        players_data = LoadPlayers()

        pdata = players_data.get(self.name)
        if not pdata:
            pdata = {
                "join_date": now,
                "last_seen": now,
                "permission_groups": ["default"],
                "custom_permissions": {},
                "ip": self.addr[0],
                "attributes": {},
                "banned": False,
                "ipbanned": False,
                "timesjoined": 1,
                "timespent": 0,
                "registered": False,     
                "password": None,        
            }
            players_data[self.name] = pdata
        else:
            pdata["last_seen"] = now
            pdata["ip"] = self.addr[0]
            pdata["timesjoined"] = max(0, int(pdata.get("timesjoined", 0))) + 1
            pdata["timespent"] = max(0, int(pdata.get("timespent", 0)))

        SavePlayers(players_data)

        groups_val = pdata.get("permission_groups", ["default"])
        self.groups = groups_val if isinstance(groups_val, list) else [groups_val]

        group_perms = GetPermissionsFromGroup(self.groups)
        group_perms.update(pdata.get("custom_permissions", {}))
        self.permissions = group_perms

        highest = max(
            (GROUPS[g]["priority"], GROUPS[g].get("prefix", "")) 
            for g in self.groups if g in GROUPS
        )
        self.prefix = highest[1]
        group_perms = GetPermissionsFromGroup(self.groups)
        group_perms.update(pdata.get("custom_permissions", {}))
        self.permissions = group_perms

    @staticmethod
    def hex_to_rgb(hex_str):
        hex_str = hex_str.lstrip("#")
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    async def Broadcast(message: str):
        
        try:
            packet = await Message(message)
        except Exception:
            return

        tasks = []
        for p in list(players.values()):
            if p.disconnected:
                continue
            try:
                async with p._write_lock:
                    p.writer.write(packet)
                    tasks.append(p.writer.drain())
            except Exception as e:
                logger.warning(f"Broadcast error to {p.name}: {e}")
                asyncio.create_task(p.cleanup())

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"[Broadcast] drain exception: {r}")

    async def CleanUp(self):
        try:
            if not self._stats_committed:
                players_data = LoadPlayers()
                if self.name in players_data:
                    session_seconds = int((datetime.datetime.now() - self.session_started_at).total_seconds())
                    pdata = players_data[self.name]
                    pdata["timespent"] = max(0, int(pdata.get("timespent", 0))) + session_seconds
                    pdata["last_seen"] = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    SavePlayers(players_data)
                self._stats_committed = True
        except Exception as e:
            logger.warning(f"Failed updating playtime stats for {self.name}: {e}")

        try:
            await DespawnPlayer(self.writer, self.id, players, self.display_name)
        except Exception as e:
            logger.warning(f"Error during despawn for {self.name}: {e}")

        players.pop(self.id, None)
        connections.pop(self.conn_key, None)
        if self.id not in available_ids:
            available_ids.append(self.id)
            available_ids.sort()

        if not self.disconnected:
            self.disconnected = True
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except (ConnectionResetError, OSError):
                pass 
