# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import yaml
import os
from Utils.Confloader import conf
from Utils.CheckExtension import CheckExtension

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_FILE = os.path.join(PROJECT_ROOT, "extensions.yaml")
GROUPS_F = os.path.join(PROJECT_ROOT, "db", "groups.yaml")

try:
    with open(EXT_FILE, "r", encoding="utf-8") as f:
        extensions_conf = yaml.safe_load(f) or {}
except FileNotFoundError:
    extensions_conf = {}

extensions = extensions_conf.get("extensions", {})

cpe = conf.get("cpe", False)
cpeblocks = CheckExtension("CustomBlocks")

players = {}
connections = {}
available_ids = []

MAX_ID = 255
next_id = 1

spawnX = 128
spawnY = 128
spawnZ = 128

maps = {}  
default_map = conf.get("main-map", "default")

verifynames = conf.get("verify-names", True)
start_time = None

MAX_PLAYERS = min(conf.get("max-players", 20), MAX_ID)
PROTOCOL = b'\x07'

MAP_FILE = os.path.join("maps", default_map + ".mcr")
PLAYERS_F = "db/players.txt"

SERVER_NAME = conf.get("name", "MCRasp")
SOFTWARE = "MCRasp"
PORT = conf.get("port", 25565)
MOTD = conf.get("motd", "Welcome!")
SALT = 0
stop = False


last_tps_time = 0
tps_counter = 0
current_tps = 0

physics_queue = set()  

prefix = "/"
banned_ips = {}   
banned = {}

fly_enabled = set()
fly_blocks = {}

cpu_usage_percent = 0.0