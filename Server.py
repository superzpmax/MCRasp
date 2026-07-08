# Server.py
# Welcome to MCRasp r1.0!

# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import os
import sys
import time
import asyncio
import secrets
import psutil
import ctypes, sys
import concurrent.futures

def enable_ansi_colors():
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)

enable_ansi_colors()

from Utils.EnsureFiles import EnsureNeededFiles
EnsureNeededFiles()

import Commands.Commands as Commands
from Commands.Commands import banned_ips, banned


from Utils.Confloader import conf
import Utils.state as state
from Utils.state import physics_queue, maps, verifynames
from Utils.Logger import logger
from Utils.IRC import ListenIRC
from Utils.Advert import AdvertHeartbeat, AdvertHeartbeatBCV2
from Utils.PluginLoader import LoadPlugins
from Utils.DisconnectPlayer import Disconnect
from Utils.Console import ListenConsole
from Utils.PlayerSaveLoad import SavePlayers
from Utils.MapIO import MapManager


from Level.Level import Map

from Player import Player
from Client import HandleStream


MAPS_DIR = "maps"
DEFAULT_TPS = 2
MIN_TPS = 1


class Server:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.shutdown_event = asyncio.Event()
        self.map_manager = MapManager(MAPS_DIR)
        self.server = None
        self.tasks = []
        self.tick_time = 1 / DEFAULT_TPS
        self.target_tps = DEFAULT_TPS

        state.start_time = time.time()
        self._init_auth()
        self._init_tps_counter()

    def _init_auth(self):
        if verifynames:
            state.SALT = secrets.token_hex(32)
            logger.info("[Auth] Generated server salt.")
        else:
            logger.warning("**** SERVER IS RUNNING IN OFFLINE/INSECURE MODE! ****")
            logger.warning("The server will NOT authenticate usernames.")
            logger.warning("To change this, set 'verify-names' to 'true' in conf.yaml.")
        logger.info(f"[Auth] Name verification: {verifynames}")

    def _init_tps_counter(self):
        state.tps_counter = 0
        state.last_tps_time = time.time()
        state.current_tps = DEFAULT_TPS

    async def SafeTask(self, name, coro):
        try:
            await coro
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.exception(f"Task '{name}' crashed with error: {e}")
            try:
                await MapManager.SaveMapOnce()
            except Exception as inner:
                logger.error(f"Failed saving maps after crash: {inner}")
            self.request_shutdown()


    async def TickLoop(self):
        last_time = time.time()
        while not state.stop:
            start = time.time()
            await self._run_physics()

            elapsed = time.time() - start
            await asyncio.sleep(max(0, self.tick_time - elapsed))

            now = time.time()
            actual_tps = 1 / (now - last_time) if now != last_time else self.target_tps
            state.current_tps = actual_tps
            last_time = now

            self.target_tps = 10 if actual_tps <= MIN_TPS else DEFAULT_TPS

    async def _run_physics(self):
        try:
            from Utils.Physics import PhysicsComp, Physics_Tick, tntQ, Physics_ExplodeTnt
            coords_to_check = list(physics_queue)
            physics_queue.clear()

            for (map_name, x, y, z) in coords_to_check:
                game_map = maps.get(map_name)
                if game_map:
                    await PhysicsComp(game_map, x, y, z)
                else:
                    logger.warning(f"Physics skipped: {map_name} not loaded")

            for game_map in maps.values():
                await Physics_Tick(game_map)

            while tntQ:
                map_name, x, y, z = tntQ.popleft()
                game_map = maps.get(map_name)
                if game_map:
                    asyncio.create_task(Physics_ExplodeTnt(game_map, x, y, z))

        except Exception as e:
            logger.error(f"Physics step error: {e}")



    async def Start(self):
        os.makedirs(MAPS_DIR, exist_ok=True)
        self._load_maps()

        if state.default_map not in maps:
            logger.info(f"Default level '{state.default_map}' missing. Generating...")
            await MapManager.CreateLevel(256, 128, 256, 256, 64, 256, state.default_map)
            await MapManager.GenerateDefaultMap()

        self._load_plugins()

        self.server = await asyncio.start_server(HandleStream, "0.0.0.0", state.PORT)
        logger.info(f"Server listening on port *:{state.PORT}")

        self._start_background_tasks()

        elapsed = round(time.time() - state.start_time, 3)
        logger.info(f"\033[92mDone ({elapsed}s)! For help, type 'help' or '?'")
        logger.warning("MCRasp is early development: expect crashes and bugs.")

        await self.shutdown_event.wait()
        await self.ShutDown()
        return


    async def ShutDown(self):
        if state.stop:
            return 
        state.stop = True

        logger.info("Server shutting down...")

        for _, player in list(state.connections.items()):
            try:
                await Disconnect(player.writer, "Server closed")
            except Exception as e:
                logger.warning(f"Error disconnecting {player.name}: {e}")

        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

        if self.server:
            self.server.close()
            try:
                await self.server.wait_closed()
            except Exception as e:
                logger.warning(f"Error closing server socket: {e}")

        try:
            logger.info("Saving maps...")
            await MapManager.SaveMapOnce(self)
        except Exception as e:
            logger.error(f"Failed to save maps: {e}")
        loop = asyncio.get_running_loop()
        executor = loop._default_executor
        if isinstance(executor, concurrent.futures.ThreadPoolExecutor):
            executor.shutdown(wait=False, cancel_futures=True)
        logger.info("Shutdown complete.")


    def _load_maps(self):
        for filename in os.listdir(MAPS_DIR):
            if filename.endswith(".mcr"):
                mapname = filename[:-4]
                full_path = os.path.join(MAPS_DIR, filename)
                try:
                    maps[mapname] = Map.LoadFromFile(full_path, name=mapname)
                    logger.info(f"[LevelLoader] Level '{mapname}' loaded.")
                except Exception as e:
                    logger.warning(f"[LevelLoader] Failed to load '{filename}': {e}")

    def _load_plugins(self):
        logger.info("[PluginLoader] Loading plugins...")
        for plugin in LoadPlugins("plugins"):
            try:
                logger.info(f"[PluginLoader] Plugin '{plugin.name()}' loaded")
                plugin.run()
            except Exception as e:
                logger.error(f"[PluginLoader] Plugin '{plugin.name()}' crashed: {e}")

    def _start_background_tasks(self):
        self.tasks = [
            asyncio.create_task(self.SafeTask("ListenConsole", ListenConsole())),
            asyncio.create_task(self.SafeTask("SaveMap", self.map_manager.SaveMaps())),
            asyncio.create_task(self.SafeTask("Server", self.server.serve_forever())),
            asyncio.create_task(self.SafeTask("CPUMonitor", Commands.MonitorCPU())),
            asyncio.create_task(self.SafeTask("UnloadUnusedMaps", self.map_manager.UnloadUnusedMaps())),
            asyncio.create_task(self.SafeTask("TickLoop", self.TickLoop()))
        ]
        self.tasks.append(asyncio.create_task(self.SafeTask("FlyUpdater", Commands.FlyUpdater())))
        if conf.get("irc"):
            self.tasks.append(asyncio.create_task(self.SafeTask("IRC", ListenIRC(Player.Broadcast))))
        if conf.get("public"):
            self.tasks.append(asyncio.create_task(self.SafeTask("AdvertHeartbeat", AdvertHeartbeat())))
        if conf.get("public-betacraft"):
            self.tasks.append(asyncio.create_task(self.SafeTask("AdvertHeartbeatBCV2", AdvertHeartbeatBCV2())))

    def request_shutdown(self):
        if not self.shutdown_event.is_set():
            self.shutdown_event.set()



if __name__ == "__main__":
    try:
        server = Server()
        asyncio.run(server.Start())
    except KeyboardInterrupt:
        try:
            asyncio.run(server.ShutDown())
        except Exception:
            pass
