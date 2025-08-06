import os
import psutil
import struct
import time
from datetime import datetime
import platform
import asyncio
import importlib
import time
import yaml
from collections import defaultdict

from Utils.Logger import logger

from Utils.state import *
from Packets.Message import Message
from Packets.Position import UpdatePosition
from Packets.CPE.EnvColors import SetEnvColor
from Packets.Despawn import DespawnPlayer
from Utils.Chatter import ErrorChat
from Packets.Block import SetBlock
from Utils.Confloader import extensions
from Player import GetPermissionsFromGroup
from Packets.Spawn import SpawnPlayer
from Utils.MapIO import *
from Utils.Password import hash_password, verify_password
from Utils.Confloader import conf
from Utils.PlayerSaveLoad import SavePlayers, LoadPlayers
from Level.ClassicGen import ClassicGenerator
from Level.FlatGen import FlatGenerator
from Utils.Permissions import MatchPermission, RequirePermission, HasPermission
from Utils.BlockPerms import permissions
COMMANDS = {}
with open("db/commands.yaml", "r") as f:
    _cmd_data = yaml.safe_load(f) or {}

BASE_COMMANDS = _cmd_data.get("commands", [])

CPE_COMMANDS = []

async def FlyUpdater():
    while True:
        try:
            for p in list(state.players.values()):
                if p.name in fly_enabled and not p.disconnected:
                    x = p.x // 32
                    y = max(0, (p.y // 32) - 2)
                    z = p.z // 32
                    current_map = p.map

                    if not (0 <= x < current_map.x and 0 <= y < current_map.y and 0 <= z < current_map.z):
                        continue

                    new_platform = set()
                    block_id = 20
                    for dx in range(-2, 3):
                        for dz in range(-2, 3):
                            nx, nz = x + dx, z + dz
                            if 0 <= nx < current_map.x and 0 <= nz < current_map.z:
                                idx = (y * current_map.z + nz) * current_map.x + nx
                                if current_map.raw_data[idx] == 0:
                                    await SetBlock(nx, y, nz, block_id, mode=1, player=p)
                                    new_platform.add((nx, y, nz))
                                elif (nx, y, nz) in fly_blocks.get(p.name, set()):
                                    new_platform.add((nx, y, nz))

                    for (ox, oy, oz) in fly_blocks.get(p.name, set()) - new_platform:
                        idx = (oy * current_map.z + oz) * current_map.x + ox
                        if current_map.raw_data[idx] == block_id: 
                            await SetBlock(ox, oy, oz, 0, mode=1, player=p)

                    fly_blocks[p.name] = new_platform
        except Exception as e:
            logger.error(f"[FlyUpdater] error: {e}")

        await asyncio.sleep(0.015)



async def MonitorCPU():
    global cpu_usage_percent
    process.cpu_percent(None)
    cpu_count = psutil.cpu_count(logical=True)

    while True:
        usage_samples = []
        for _ in range(10):
            usage = process.cpu_percent(interval=None) / cpu_count
            usage_samples.append(usage)
            await asyncio.sleep(0.1)
        cpu_usage_percent = sum(usage_samples) / len(usage_samples)


if os.path.exists(MAP_FILE):
    try:
        map_size = os.path.getsize(MAP_FILE) / (1024 * 1024)
    except Exception as e:
        logger.error(f"Error reading map file size: {e}")
else:
    map_size = 0.0
    logger.warning(f"Map file not found: {MAP_FILE}")



with open("db/commands.yaml", "r") as f:
    _cmd_data = yaml.safe_load(f)

try:
    import distro
except ImportError:
    distro = None
def FindOnlinePlayer(name: str):
    name = (name or "").lower()
    return next(
        (p for p in state.players.values() if p.name.lower() == name),
        None
    )


def FindYamlKey(data: dict, name: str):
    wanted = (name or "").lower()
    for key in data.keys():
        if key.lower() == wanted:
            return key
    return None


def GetPrefixFromGroups(group_names):
    try:
        with open("db/groups.yaml", "r", encoding="utf-8") as f:
            group_data = yaml.safe_load(f) or {}
    except Exception:
        return ""

    best_prefix = ""
    best_priority = -999999

    for group_name in group_names:
        info = group_data.get(group_name, {})
        priority = int(info.get("priority", 0))
        prefix_value = info.get("prefix", "")

        if priority >= best_priority:
            best_priority = priority
            best_prefix = prefix_value

    return best_prefix


def RefreshOnlinePlayerGroups(target, groups):
    groups = list(groups or [])

    if not groups:
        groups = ["default"]

    target.groups = groups
    target.permissions = GetPermissionsFromGroup(groups)
    target.prefix = GetPrefixFromGroups(groups)

    return target
def FormatUT(seconds):
    seconds = int(seconds)
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days:
        parts.append(f"{days} d")
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} m")
    if secs or not parts:  
        parts.append(f"{secs} s")

    return ", ".join(parts)
    
def CleanPlat():
    system = platform.system()
    
    if system == "Windows":
        release = platform.release()
        return f"windows-{release}"
    
    elif system == "Linux":
        if distro:
            name = distro.id().lower()
            version = distro.version()
            return f"{name}-{version}"
        else:
            try:
                with open("/etc/os-release") as f:
                    lines = f.readlines()
                name = version = ""
                for line in lines:
                    if line.startswith("ID="):
                        name = line.strip().split("=")[1].strip('"')
                    elif line.startswith("VERSION_ID="):
                        version = line.strip().split("=")[1].strip('"')
                return f"{name}-{version}"
            except:
                return "linux-unknown"

    else:
        release = platform.release()
        return f"{system.lower()}-{release}"

operatingsys = CleanPlat()

process = psutil.Process(os.getpid())

def _pick_generator(gen_name: str, x: int, y: int, z: int, seed: int):
    name = (gen_name or "classic").strip().lower()
    if name in ("flat", "flatgen", "flatgenerator"):
        return FlatGenerator(x, y, z)
    return ClassicGenerator(x, y, z, seed=seed)

async def HandleCommand(player, message, players, disconnect):
    if player.name != "Console":
        safe_msg = message
        if message.lower().startswith(("/register", "/login")):
            safe_msg = message.split()[0] + " ***"
        logger.info(f"{player.name} issued server command {safe_msg}")

    parts = message.strip().split(" ", 1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    if command in (f"{prefix}help", f"{prefix}?"):
        if not await RequirePermission(player, "rasp.server.help", "/help"):
            return

        commands_per_page = 7
        all_cmds = BASE_COMMANDS + (CPE_COMMANDS if getattr(state, "cpe", False) else [])

        parts = args.strip().split() if args else []
        arg = parts[0].lower() if parts else ""
        page_arg = parts[1] if len(parts) > 1 else ""

        all_categories = sorted({cmd.get("category", "Uncategorized").title() for cmd in all_cmds})
        visible_counts = {cat: 0 for cat in all_categories}

        for cmd in all_cmds:
            cat = cmd.get("category", "Uncategorized").title()
            if HasPermission(player, cmd.get("permission", "")):
                visible_counts[cat] += 1

        if not arg:
            player.writer.write(await Message("&2--- Available Command Categories ---"))
            for cat in all_categories:
                count = visible_counts.get(cat, 0)
                if count > 0:
                    player.writer.write(await Message(f" &7- &f{cat} &7({count} commands)"))
                else:
                    player.writer.write(await Message(f" &8- {cat} &7(hidden)"))
            player.writer.write(await Message(" &fUse &a/help <category> [page]"))
            player.writer.write(await Message(" &fUse &a/help all [page]"))
            return

        if arg == "all":
            visible_cmds = [cmd for cmd in all_cmds if HasPermission(player, cmd.get("permission", ""))]
        else:
            visible_cmds = [
                cmd for cmd in all_cmds
                if cmd.get("category", "Uncategorized").lower() == arg
                and HasPermission(player, cmd.get("permission", ""))
            ]

        if not visible_cmds:
            await ErrorChat(player, player.writer, f"No accessible commands for '{arg}'.")
            return

        total_commands = len(visible_cmds)
        total_pages = (total_commands + commands_per_page - 1) // commands_per_page
        try:
            page = int(page_arg) if page_arg else 1
        except ValueError:
            page = 1
        page = max(1, min(page, total_pages))

        start_index = (page - 1) * commands_per_page
        end_index = min(start_index + commands_per_page, total_commands)

        player.writer.write(await Message(f"&2--- Showing help page {page} of {total_pages} ---"))
        for cmd in visible_cmds[start_index:end_index]:
            name = cmd.get("name", "<unnamed>")
            desc = cmd.get("description", "")
            player.writer.write(await Message(f" &f/{name}&7 {desc}"))

    elif command == f"{prefix}list" or command == f"{prefix}players":
        if not await RequirePermission(player, "rasp.server.playerlist", command):
            return


        entries = [f"{p.name} &7(ID: {p.id})&f" for p in state.players.values()]

        player.writer.write(await Message(f"&fPlayers online ({len(entries)}/{state.MAX_PLAYERS}):"))

        line = ""
        for entry in entries:
            if line == "":
                line = entry
            else:
                test_line = line + ", " + entry
                if len(test_line) > 60: 
                    player.writer.write(await Message(f"&f{line}"))
                    line = entry
                else:
                    line = test_line

        if line:
            player.writer.write(await Message(f"&f{line}"))


    elif command == f"{prefix}kick":
        if not await RequirePermission(player, "rasp.moderation.kick", command):
            return


        if not args or len(args.split(" ", 1)) < 2:
            player.writer.write(await Message("&cUsage: /kick <player> <reason>"))
            return

        target_name, reason = args.split(" ", 1)
        target = next((p for p in state.players.values() if p.name.lower() == target_name.lower()), None)


        if not target:
            player.writer.write(await Message("&cPlayer not found."))
            return

        await disconnect(target.writer, f"You were kicked from the server for: {reason}")
        player.writer.write(await Message(f"&eKicked {target.name} for: {reason}"))
        logger.info(f"{player.name} kicked {target.name} for: {reason}")
        return
    
    elif command == f"{prefix}group":
        args_list = args.strip().split()

        if not args_list:
            player.writer.write(await Message("&cUsage: /group <add|remove|list> <player> [group]"))
            await player.writer.drain()
            return

        subcmd = args_list[0].lower()
        data = LoadPlayers()

        try:
            with open("db/groups.yaml", "r", encoding="utf-8") as f:
                group_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            player.writer.write(await Message("&cCould not find db/groups.yaml."))
            await player.writer.drain()
            return

        if subcmd == "add":
            if not HasPermission(player, "rasp.groups.add"):
                player.writer.write(await Message("&cNo permission to add group."))
                await player.writer.drain()
                return

            if len(args_list) != 3:
                player.writer.write(await Message("&cUsage: /group add <player> <group>"))
                await player.writer.drain()
                return

            target_name = args_list[1]
            group_to_add = args_list[2]

            target_key = FindYamlKey(data, target_name)
            group_key = FindYamlKey(group_data, group_to_add)

            if not group_key:
                player.writer.write(await Message(f"&cGroup '{group_to_add}' does not exist."))
                await player.writer.drain()
                return

            if not target_key:
                player.writer.write(await Message("&cPlayer not found in player records."))
                await player.writer.drain()
                return

            data[target_key].setdefault("permission_groups", [])

            if group_key not in data[target_key]["permission_groups"]:
                data[target_key]["permission_groups"].append(group_key)

            SavePlayers(data)

            target = FindOnlinePlayer(target_key)

            if target:
                RefreshOnlinePlayerGroups(target, data[target_key]["permission_groups"])

                target.writer.write(await Message(
                    f"&aYour permissions were updated. You were added to group: &e{group_key}&a."
                ))
                await target.writer.drain()

            player.writer.write(await Message(
                f"&aAdded &e{target_key} &ato group &e{group_key}&a."
            ))
            await player.writer.drain()
            return

        elif subcmd == "remove":
            if not HasPermission(player, "rasp.groups.remove"):
                player.writer.write(await Message("&cNo permission to remove group."))
                await player.writer.drain()
                return

            if len(args_list) != 3:
                player.writer.write(await Message("&cUsage: /group remove <player> <group>"))
                await player.writer.drain()
                return

            target_name = args_list[1]
            group_to_remove = args_list[2]

            target_key = FindYamlKey(data, target_name)
            group_key = FindYamlKey(group_data, group_to_remove)

            if not target_key:
                player.writer.write(await Message("&cPlayer not found."))
                await player.writer.drain()
                return

            if not group_key:
                player.writer.write(await Message(f"&cGroup '{group_to_remove}' does not exist."))
                await player.writer.drain()
                return

            data[target_key].setdefault("permission_groups", [])

            groups = data[target_key]["permission_groups"]

            if group_key in groups:
                groups.remove(group_key)
            else:
                player.writer.write(await Message(
                    f"&c{target_key} is not in group '{group_key}'."
                ))
                await player.writer.drain()
                return

            if not groups:
                groups.append("default")

            SavePlayers(data)

            target = FindOnlinePlayer(target_key)

            if target:
                RefreshOnlinePlayerGroups(target, groups)

                target.writer.write(await Message(
                    f"&cYou were removed from group: &7{group_key}&c."
                ))
                await target.writer.drain()

            player.writer.write(await Message(
                f"&aRemoved &e{group_key} &afrom &e{target_key}&a."
            ))
            await player.writer.drain()
            return

        elif subcmd == "list":
            if not HasPermission(player, "rasp.groups.list"):
                player.writer.write(await Message("&cNo permission to list groups."))
                await player.writer.drain()
                return

            player.writer.write(await Message("&fGroups available:"))

            for group_name in group_data:
                player.writer.write(await Message(f"&7* {group_name}"))

            await player.writer.drain()
            return

        else:
            player.writer.write(await Message("&cUsage: /group <add|remove|list> <player> [group]"))
            await player.writer.drain()
            return



    elif command == f"{prefix}stats":
        if not await RequirePermission(player, "rasp.server.stats", command):
            return

        uptime_seconds = time.time() - state.start_time
        cpu = cpu_usage_percent
        mem_info = process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024
        tasks = asyncio.all_tasks()
        task_count = len(tasks)
        msg = (
            f"&eVersion: &a{state.SOFTWARE}\n"
            f"&a{state.SERVER_NAME} &erunning on &a{operatingsys}\n"
            f"&eUsing &a{cpu_usage_percent:.2f}% &eof CPU, with using &a{mem_mb:.2f} MB&e of memory,\n"
            f"&ewith &a{task_count}&e active tasks (asyncio).\n"
            f"&eProtocol Extensions: &a{state.cpe} &e(&a{len(extensions)} &eloaded).\n"
            f"&eUptime: &a{FormatUT(uptime_seconds)}"
        )

        for line in msg.split("\n"):
            player.writer.write(await Message(line))
        return


    elif command == f"{prefix}me":
        if not await RequirePermission(player, "rasp.player.actionme", command):
            return

        if not args:
            player.writer.write(await Message("&cUsage: /me <action>"))
            return

        action = args.strip()
        return f"* {player.name} {action}"
    
    elif command == f"{prefix}tell":
        if not await RequirePermission(player, "rasp.player.tell", command):
            return

            
        string = args

        if not string:
            player.writer.write(await Message("&cUsage: /tell <string>"))
            return
        
        for p in state.players.values():
            p.writer.write(await Message(f"[{player.name}] {string}"))
            return
            
        return f"[{player.name}] {string}"

    elif command == f"{prefix}tellraw":
        if not await RequirePermission(player, "rasp.player.tellraw", command):
            return

            
        string = args
        if not string:
            player.writer.write(await Message("&cUsage: /tellraw <string>"))
            return
        
        for p in state.players.values():
            p.writer.write(await Message(string))
        return

    
    elif command == f"{prefix}tp":
        if not await RequirePermission(player, "rasp.player.teleport", command):
            return

        coords = args.strip().split()
        if len(coords) != 3:
            player.writer.write(await Message("&cUsage: /tp <x> <y> <z>"))
            return

        try:
            x, y, z = map(int, coords)
        except ValueError:
            player.writer.write(await Message("&cCoordinates must be integers."))
            return

        fx, fy, fz = x * 32, y * 32, z * 32
        player.x = fx
        player.y = fy
        player.z = fz

        packet = struct.pack(">BBhhhBB", 0x08, 255, fx, fy, fz, 0, 0)
        player.writer.write(packet)
        await player.writer.drain()


        player.writer.write(await Message(f"&aTeleported to ({x}, {y}, {z})"))
        return




    elif command == f"{prefix}whereis":
        if not await RequirePermission(player, "rasp.player.gps", command):
            return

        if not args:
            player.writer.write(await Message("&cUsage: /whereis <player>"))
            return
        
        target_name = args.strip()

        target = next((p for p in state.players.values() if p.name.lower() == target_name.lower()), None)

        if not target:
            player.writer.write(await Message("&cPlayer not found."))
            return

        player.writer.write(await Message(
            f"&f{target.name} is at X={target.x//32}, Y={target.y//32}, Z={target.z//32}"
        ))
        return

    elif command == f"{prefix}place":
        if not HasPermission(player, "rasp.builder.place"):
            player.writer.write(await Message(f"&cInsufficient permissions to run {command}."))
            await player.writer.drain()
            return

        if not args:
            player.writer.write(await Message("&cUsage: /place <block_id>"))
            await player.writer.drain()
            return

        try:
            block_id = int(args.strip())
        except ValueError:
            player.writer.write(await Message("&cBlock ID must be a number."))
            await player.writer.drain()
            return

        if not (0 <= block_id <= 255):
            player.writer.write(await Message("&cInvalid block ID! Must be between 0 and 255."))
            await player.writer.drain()
            return

        perms = permissions.get(block_id, [1, 1])
        if not perms[0]:
            player.writer.write(await Message(f"&cPlacement of block {block_id} is prohibited!"))
            await player.writer.drain()
            return

        x = player.x // 32
        y = max(0, (player.y // 32) - 2)
        z = player.z // 32

        current_map = player.map
        if not (0 <= x < current_map.x and 0 <= y < current_map.y and 0 <= z < current_map.z):
            player.writer.write(await Message("&cYou're outside the map bounds!"))
            await player.writer.drain()
            return

        try:
            await SetBlock(x, y, z, block_id, mode=1, player=player)
            player.writer.write(await Message(f"&aPlaced block ID {block_id} at your feet."))
            await player.writer.drain()
        except Exception as e:
            logger.error(f"Error placing block: {e}")
            player.writer.write(await Message("&cFailed to place block."))
            await player.writer.drain()



    elif command == f"{prefix}tpp":
        if not await RequirePermission(player, "rasp.player.tpp", command):
            return

        if not args:
            player.writer.write(await Message("&cUsage: /tpp <player>"))
            return

        target_name = args.strip()
        target = next((p for p in state.players.values() if p.name.lower() == target_name.lower()), None)

        if not target:
            player.writer.write(await Message("&cPlayer not found."))
            return

        tx, ty, tz = target.x // 32, target.y // 32 - 1, target.z // 32
        fx, fy, fz = tx * 32, ty * 32, tz * 32

        player.x = fx
        player.y = fy
        player.z = fz

        packet = struct.pack(">BBhhhBB", 0x08, 255, fx, fy, fz, 0, 0)
        player.writer.write(packet)
        await player.writer.drain()


        player.writer.write(await Message(f"&aTeleported to &e{target.name}"))
        return




    elif command == f"{prefix}rules":
        if not await RequirePermission(player, "rasp.moderation.rules", command):
            return

        with open("extra/rules.txt", "r") as wel:
            if not wel:
                pass
            else:
                for line in wel:
                    clean_line = line.strip()
                    player.writer.write(await Message(clean_line))
        return
    
    elif command == f"{prefix}ban":
        data = LoadPlayers()
        if not await RequirePermission(player, "rasp.moderation.ban", command):
            return

        target_name = args.strip()
        if not target_name:
            player.writer.write(await Message("&cUsage: /ban <player>"))
            return
        if target_name in data:
            data[target_name]["banned"] = True
            SavePlayers(data)
            target = next((p for p in state.players.values() if p.name.lower() == target_name.lower()), None)
            if target:
                await disconnect(target.writer, "You were banned from this server.")
            player.writer.write(await Message(f"&eBanned {target_name}."))
        else:
            player.writer.write(await Message("&cPlayer not found."))
        return

    elif command == f"{prefix}pardon":
        data = LoadPlayers()
        if not await RequirePermission(player, "rasp.moderation.pardon", command):
            return

        target_name = args.strip()
        if not target_name:
            player.writer.write(await Message("&cUsage: /pardon <player>"))
            return
        if target_name in data and data[target_name].get("banned"):
            data[target_name]["banned"] = False
            SavePlayers(data)
            player.writer.write(await Message(f"&aUnbanned {target_name}"))
        else:
            player.writer.write(await Message("&cThat player is not banned."))
        return

    elif command == f"{prefix}ban-ip":
        data = LoadPlayers()
        if not await RequirePermission(player, "rasp.moderation.banip", command):
            return

        target_name = args.strip()
        if not target_name:
            player.writer.write(await Message("&cUsage: /ban-ip <player>"))
            return
        target = next((p for p in state.players.values() if p.name.lower() == target_name.lower()), None)
        if not target:
            player.writer.write(await Message("&cPlayer not found."))
            return
        if target.name in data:
            data[target.name]["ipbanned"] = True
            data[target.name]["banned"] = True
            SavePlayers(data)
        player.writer.write(await Message(f"&eBanned {target.name} (IP: {target.addr[0]})"))
        await disconnect(target.writer, "You were banned from this server.")
        return

    elif command == f"{prefix}pardon-ip":
        data = LoadPlayers()
        if not await RequirePermission(player, "rasp.moderation.pardonip", command):
            return

        target_name = args.strip()
        if not target_name:
            player.writer.write(await Message("&cUsage: /pardon-ip <player>"))
            return
        if target_name in data and data[target_name].get("ipbanned"):
            data[target_name]["ipbanned"] = False
            SavePlayers(data)
            player.writer.write(await Message(f"&aUnbanned {target_name} (IP Ban Removed)"))
        else:
            player.writer.write(await Message("&cThat player is not IP banned."))
        return

    elif command == f"{prefix}sinfo":
        if not await RequirePermission(player, "rasp.server.serverinfo", command):
            return

        data = LoadPlayers()
        total_players = len(data)
        ipbanned_count = sum(1 for p in data.values() if p.get("ipbanned"))
        banned_count = sum(1 for p in data.values() if p.get("banned"))
        player.writer.write(await Message(f"&aPlayers of the server:"))
        player.writer.write(await Message(f"&3{total_players} &6unique players,"))
        player.writer.write(await Message(f"&3{ipbanned_count} &6players IP Banned,"))
        player.writer.write(await Message(f"&3{banned_count} &6players banned,"))
        return

    elif command in ("/info", "/i"):
        if not await RequirePermission(player, "rasp.server.playerinfo", command):
            return

        target_name = args.strip()
        if not target_name:
            player.writer.write(await Message(f"&cUsage: {command} <player>"))
            return
        data = LoadPlayers()
        if target_name in data:
            pdata = data[target_name]
            try:
                firstseen = datetime.strptime(pdata["join_date"], "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
                lastseen_dt = datetime.strptime(pdata["last_seen"], "%Y%m%d%H%M%S")
                lastseen = lastseen_dt.strftime("%Y-%m-%d %H:%M:%S")
                seen = FormatUT((datetime.now() - lastseen_dt).total_seconds())
            except ValueError as e:
                player.writer.write(await Message(f"&cDate parse error: {e}"))
                return
            player.writer.write(await Message(f"&eInfo on &a{target_name}:"))
            player.writer.write(await Message(f"&eFirst seen on: &3{firstseen} {time.tzname[1]}"))
            player.writer.write(await Message(f"&eLast seen on: &3{lastseen} {time.tzname[1]}"))
            player.writer.write(await Message(f"&eSeen &3{seen}&e ago."))
            if pdata.get("ipbanned"):
                player.writer.write(await Message(f"&cPlayer is &8IP-banned"))
            if pdata.get("banned"):
                player.writer.write(await Message(f"&cPlayer is &8banned"))
        else:
            player.writer.write(await Message("&cPlayer not found."))
        return
    
    elif command == f"{prefix}msg" or command == "/w":
        if not await RequirePermission(player, "rasp.player.whisper", command):
            return

        if not args or len(args.split(" ", 1)) < 2:
            player.writer.write(await Message(f"&cUsage: {command} <player> <message>"))
            return

        target_name, pm = args.split(" ", 1)
        target = next((p for p in state.players.values() if p.name.lower() == target_name.lower()), None)

        if not target:
            player.writer.write(await Message("&cPlayer not found."))
            return

        player.writer.write(await Message(f"&7[To {target.name}]&f {pm}"))
        target.writer.write(await Message(f"&7[From {player.name}]&f {pm}"))
        return
    elif command == f"{prefix}fly":
        if not await RequirePermission(player, "rasp.player.fly", command):
            return


        if player.name in fly_enabled:
            fly_enabled.remove(player.name)
            for (x, y, z) in fly_blocks.get(player.name, set()):
                try:
                    idx = (y * player.map.z + z) * player.map.x + x
                    if player.map.raw_data[idx] == 20:
                        await SetBlock(x, y, z, 0, mode=1, player=player)
                except Exception:
                    pass
            fly_blocks.pop(player.name, None)
            player.writer.write(await Message("&eFly mode disabled."))
        else:
            fly_enabled.add(player.name)
            fly_blocks[player.name] = set()
            player.writer.write(await Message("&aFly mode enabled."))
        return
    elif command == f"{prefix}map":
        args_list = args.strip().split()

        async def send_message(text: str):
            player.writer.write(await Message(text))
            await player.writer.drain()

        def load_map(mapname: str):
            map_path = os.path.join("maps", f"{mapname}.mcr")
            if not os.path.exists(map_path):
                return None
            from Level.Level import Map
            return Map.LoadFromFile(map_path, name=mapname)

        if not args_list:
            await send_message("&cUsage: /map <switch|create|list|setenv> ...")
            return

        subcommand = args_list[0].lower()

        if subcommand == "switch":
            if not HasPermission(player, "rasp.level.switch"):
                await send_message("&cYou do not have permission to switch maps.")
                return
            if len(args_list) != 2:
                await send_message("&cUsage: /map switch <mapname>")
                return

            mapname = args_list[1]
            if mapname not in state.maps:
                loaded = load_map(mapname)
                if not loaded:
                    await send_message(f"&cMap '{mapname}' not found.")
                    return
                state.maps[mapname] = loaded
                logger.info(f"Reloaded map '{mapname}' from disk on demand.")

            old_map = player.map
            new_map = state.maps[mapname]

            if old_map == new_map:
                await send_message("&cYou're already on that map!")
                return

            for p in state.players.values():
                if p != player and p.map == old_map:
                    try:
                        packet = b'\x0c' + struct.pack('b', player.id)
                        p.writer.write(packet)
                        await p.writer.drain()
                    except Exception as e:
                        logger.info(f"Failed to DespawnPlayer {player.name} from {p.name}: {e}")

            player.map = new_map
            player.x = new_map.x // 2 * 32
            player.y = new_map.y // 2 * 32
            player.z = new_map.z // 2 * 32

            await player.level()

            teleport = struct.pack(">BBhhhBB", 0x08, 255, player.x, player.y, player.z, 0, 0)
            player.writer.write(teleport)
            await player.writer.drain()

            await SpawnPlayer(state.players, player.writer, player.name, player.id)

            return f"&f{player.name} &7went to &f'{mapname}'"

        elif subcommand == "create":
            if not HasPermission(player, "rasp.level.create"):
                await send_message("&cYou do not have permission to create maps.")
                return

            parts = args_list
            if len(parts) < 5:
                await send_message("&cUsage: /map create <name> <x> <y> <z> [classic|flat] [seed]")
                return

            mapname = parts[1]
            try:
                x, y, z = map(int, parts[2:5])
            except ValueError:
                await send_message("&cCoordinates must be integers.")
                return

            gen_name = parts[5] if len(parts) >= 6 else "classic"
            try:
                seed = int(parts[6]) if len(parts) >= 7 else random.randint(0, 2147483647)
            except ValueError:
                await send_message("&cSeed must be an integer.")
                return

            if mapname in state.maps:
                await send_message("&cA map with that name already exists.")
                return

            from Level.Level import Map
            new_map = Map(x, y, z, mapname, client=None)
            state.maps[mapname] = new_map

            try:
                generator = _pick_generator(gen_name, x, y, z, seed)
                world = generator.generate()

                set_count = 0
                for xx in range(x):
                    for yy in range(y):
                        for zz in range(z):
                            block_id = world[xx][yy][zz]
                            if block_id:
                                await new_map.SetMapBlock(xx, yy, zz, int(block_id))
                                set_count += 1
                    if xx % 8 == 0:
                        await asyncio.sleep(0)

                os.makedirs("maps", exist_ok=True)
                path = os.path.join("maps", f"{mapname}.mcr")
                with open(path, "wb") as f:
                    f.write(struct.pack(">III", new_map.x, new_map.y, new_map.z))
                    compressed_data = zstd.ZstdCompressor().compress(new_map.raw_data)
                    f.write(compressed_data)
                    env_bytes = pack_env(new_map.env)
                    f.write(env_bytes)
                    f.write(struct.pack(">I", ENV_SIZE))

                new_map.dirty = False

                await send_message(f"&7Map &f'{mapname}' &7created with &f{gen_name}&7 (seed &f{seed}&7), "
                                   f"set &f{set_count}&7 blocks and saved.")
                return f"&f{player.name} &7created map &f'{mapname}' &7using &f{gen_name}&7 (seed &f{seed}&7)"

            except Exception as e:
                await send_message(f"&cFailed to generate/save map: {e}")
                try:
                    del state.maps[mapname]
                except Exception:
                    pass
                return


        elif subcommand == "list":
            if not HasPermission(player, "rasp.level.list"):
                await send_message("&cYou do not have permission to list maps.")
                return
            names = ", ".join(state.maps.keys())
            await send_message(f"&7Available maps: &f{names}")
            return

        elif subcommand == "setenv":
            if not HasPermission(player, "rasp.level.setenv"):
                await send_message("&cYou do not have permission to change map environment.")
                return

            if len(args_list) != 3:
                await send_message("&cUsage: /map setenv <fog|sky|sunlight|shadow|cloud> <hex>")
                return

            prop = args_list[1].lower()
            hex_color = args_list[2].lstrip('#').upper()

            if len(hex_color) != 6 or any(c not in "0123456789ABCDEF" for c in hex_color):
                await send_message("&cInvalid hex color. Use format like FFFFFF")
                return

            env_map_indices = {"fog": 0, "sky": 1, "sunlight": 2, "shadow": 3, "cloud": 7}
            if prop not in env_map_indices:
                await send_message("&cInvalid env type. Use fog, sky, sunlight, shadow, or cloud.")
                return

            idx = env_map_indices[prop]
            player.map.env[idx] = hex_color

            try:
                os.makedirs("maps", exist_ok=True)
                path = os.path.join("maps", f"{player.map.name}.mcr")

                with open(path, "wb") as f:
                    f.write(struct.pack(">III", player.map.x, player.map.y, player.map.z))

                    compressed_data = zstd.ZstdCompressor().compress(player.map.raw_data)
                    f.write(compressed_data)

                    env_bytes = pack_env(player.map.env)
                    f.write(env_bytes)
                    f.write(struct.pack(">I", ENV_SIZE)) 

                player.map.dirty = False

                await send_message(f"&7Updated {prop} color to &f#{hex_color}&7 for map &f{player.map.name}&7.")
            except Exception as e:
                await send_message(f"&cFailed to save updated environment: {e}")
                return

            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            for p in state.players.values():
                if p.map == player.map:
                    await SetEnvColor(p.writer, prop, r, g, b, state.players, glob=False)

            return


        else:
            await send_message("&cUsage: /map <switch|create|list|setenv> ...")
            return

    elif command == f"{prefix}tps":
        if not await RequirePermission(player, "rasp.server.tps", command):
            return


        tps_value = getattr(state, "current_tps", 0.0)
        color = "&2" if tps_value == 20 else "&a" if tps_value >= 18 else "&e" if tps_value >= 15 else "&c" if tps_value >= 5 else "&4"
        player.writer.write(await Message(f"&eCurrent TPS: {color}{tps_value:.2f}&e / 20.00"))
        return



    elif command == "/register":
        if not conf.get("require_registration", False):
            player.writer.write(await Message("&eRegister system is disabled."))
            return
        players_data = LoadPlayers()
        pdata = players_data[player.name]

        if pdata.get("registered"):
            player.writer.write(await Message("&cYou are already registered. Use /login."))
            return

        if not args:
            player.writer.write(await Message("&cUsage: /register <password>"))
            return

        pdata["password"] = hash_password(args.strip())
        pdata["registered"] = True
        SavePlayers(players_data)

        player.is_authenticated = True  
        player.writer.write(await Message("&aRegistration complete! You are now logged in."))

    elif command == "/login":
        if not conf.get("require_registration", False):
            player.writer.write(await Message("&cLogin system is disabled."))
            return
        players_data = LoadPlayers()
        pdata = players_data.get(player.name)

        if not pdata or not pdata.get("registered"):
            player.writer.write(await Message("&cYou are not registered. Use /register."))
            return

        if not args:
            player.writer.write(await Message("&cUsage: /login <password>"))
            return

        if verify_password(pdata["password"], args.strip()):
            player.is_authenticated = True
            player.writer.write(await Message("&aLogin successful!"))
        else:
            player.writer.write(await Message("&cInvalid password."))


    # CPE COMMAND
    elif command == f"{prefix}clients" or command == "/clients":
        grouped = defaultdict(list)

        for p in players.values():  
            client = getattr(p, "client", "Unknown").strip()
            name   = getattr(p, "name", "Unknown")
            if name:
                grouped[client].append(name)

        if not grouped:
            player.writer.write(await Message("&eNo clients connected."))
            return

        for client in sorted(grouped.keys(), key=lambda s: s.lower()):
            names = ", ".join(sorted(grouped[client], key=lambda s: s.lower()))
            line = f"&e{client}: &f{names}"
            player.writer.write(await Message(line))
        return




        
    else:
        await ErrorChat(player, player.writer, f"Unknown command '{command}', try using /help.")
        await player.writer.drain()
        return