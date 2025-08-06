import os
import shutil
import sys

default_conf = '''
# MCRasp server configuration

# Basic
name: "[MCRasp] Instance"  # Name of the server that will appear on server list
motd: "Welcome!" #Different flags can change hax for some clients. (eg. -hax will remove hacks like speed or fly for ClassiCube clients)
port: 25566  # Port the server will bind on. Make sure it is not used. Port can range 1-65535
log-console: true
verify-names: false
main-map: main

#Advert
public: false  # Send a server heartbeat to ClassiCube.
public-betacraft: false  # You need a private key in order to advertise your server on BetaCraft.

#Protocol Extensions
cpe: false

# Betacraft Settings
description: "Server Description"  # Description that appears below the server name.
private-key: "insert_private_key"  # NEEDED! Ask Moresteck (Betacraft admin) (or any other betacraft admin) for the private key.

physics: false

# IRC
irc: false
server: "irc.ircnet.com"
irc-port: 6667
username: "MCRaspIRCBridge"
channel: "#mc-rasp"

#Limits
packet-rate-limit: 150 # packets per second
'''
default_commands = '''
# These are built-in commands for MCRasp, just to be displayed in /help or anything else that uses it.

commands:
  - name: "help:? <page>"
    description: "List of all commands."
    category: "server"
    permission: "rasp.server.help"

  - name: "list:players"
    description: "List all players."
    category: "server"
    permission: "rasp.server.playerlist"

  - name: "kick <player> <reason>"
    description: "Kicks a player."
    category: "moderation"
    permission: "rasp.moderation.kick"

  - name: "stats"
    description: "Shows server stats."
    category: "server"
    permission: "rasp.server.stats"

  - name: "me <action>"
    description: "Do a roleplay-ish action."
    category: "player"
    permission: "rasp.player.actionme"

  - name: "tell <string>"
    description: "Tell a raw string into public chat."
    category: "player"
    permission: "rasp.player.tell"

  - name: "tellraw <string>"
    description: "Send a raw message to public chat."
    category: "player"
    permission: "rasp.player.tellraw"

  - name: "tp <x> <y> <z>"
    description: "Teleport to coordinates."
    category: "player"
    permission: "rasp.player.teleport"

  - name: "whereis <player>"
    description: "Tell someone's coordinates."
    category: "player"
    permission: "rasp.player.gps"

  - name: "place <block id>"
    description: "Place a block under your feet."
    category: "builder"
    permission: "rasp.builder.place"

  - name: "tpp <player>"
    description: "Teleport to a player."
    category: "player"
    permission: "rasp.player.tpp"

  - name: "ban-ip <player>"
    description: "Ban a player and their IP."
    category: "moderation"
    permission: "rasp.moderation.banip"

  - name: "pardon-ip <player>"
    description: "Pardon/unban a player's IP."
    category: "moderation"
    permission: "rasp.moderation.pardonip"

  - name: "ban <player>"
    description: "Ban a username."
    category: "moderation"
    permission: "rasp.moderation.ban"

  - name: "pardon <player>"
    description: "Pardon/unban a username."
    category: "moderation"
    permission: "rasp.moderation.pardon"

  - name: "rules"
    description: "See server rules."
    category: "moderation"
    permission: "rasp.moderation.rules"

  - name: "sinfo"
    description: "Server info."
    category: "server"
    permission: "rasp.server.serverinfo"

  - name: "info <player>"
    description: "Information on a player."
    category: "server"
    permission: "rasp.server.playerinfo"

  - name: "msg:w <player> <message>"
    description: "Private message someone."
    category: "player"
    permission: "rasp.player.whisper"

  - name: "fly"
    description: "Toggle fly mode."
    category: "player"
    permission: "rasp.player.fly"

  - name: "map switch <map>"
    description: "Switch to another map."
    category: "level"
    permission: "rasp.level.switch"

  - name: "map create <name> <x> <y> <z>"
    description: "Create a map."
    category: "level"
    permission: "rasp.level.create"

  - name: "map list"
    description: "List maps."
    category: "level"
    permission: "rasp.level.list"

  - name: "map setenv <type> <hex>"
    description: "Change map environment colors."
    category: "level"
    permission: "rasp.level.setenv"

  - name: "group add <player> <group>"
    description: "Add a player to a permission group."
    category: "groups"
    permission: "rasp.groups.add"

  - name: "group remove <player> <group>"
    description: "Remove a player from a permission group."
    category: "groups"
    permission: "rasp.groups.remove"

  - name: "group list"
    description: "List permission groups."
    category: "groups"
    permission: "rasp.groups.list"

  - name: "tps"
    description: "Show current server TPS."
    category: "server"
    permission: "rasp.server.tps"

cpe_commands:
  - name: "clients"
    description: "See who is using what client."
    category: "server"
    permission: "rasp.server.clients"

'''
default_groups = '''
default:
  priority: 0
  prefix: "&7"
  permissions:
   "*": false
   "rasp.server.help": true
   "rasp.server.playerlist": true
   "rasp.server.tps": true
   "rasp.level.switch": true
  #"rasp.player.tpp": true
  #"rasp.player.teleport": true
   "rasp.moderation.rules": true
   "rasp.server.help": true
   "rasp.player.actionme": true
   "rasp.player.whisper": true
   "rasp.server.stats": true
operator:
  priority: 30
  prefix: "&c"
  permissions:
    "*": true

'''
default_extensions='''
extensions:
  EnvColors: 1
  FullCP437: 1
  MessageTypes: 1
  BlockPermissions: 1
  CustomBlocks: 1
  EmoteFix: 1
  EnvMapAspect: 1
  LongerMessages: 1
  HeldBlock: 1
  InstantMOTD: 1
  TextColors: 1
  EmoteFix: 1'''

default_welcome ='''&aWelcome to my server!&f'''
default_rules = '''&aNo rules, yet!&f'''

def get_workdir() -> str:
    if getattr(sys, "frozen", False):  
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.getcwd())


def ResourcePath(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)  
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def EnsureNeededFiles(base_path=None):
    base_path = get_workdir() if base_path is None else os.path.abspath(base_path)

    for folder in ["logs", "bkp", "maps", "plugins", "db"]:
        os.makedirs(os.path.join(base_path, folder), exist_ok=True)

    db_path = os.path.join(base_path, "db")
    extra_path = os.path.join(base_path, "extra")

    os.makedirs(db_path, exist_ok=True)
    os.makedirs(extra_path, exist_ok=True)

    db_files = {
        "commands.yaml": default_commands,
        "groups.yaml": default_groups,
        "players.yml": "",
        "colors.yml": '''colors:
# Color: [R G B A, FALLBACK]''',
        "costumize.yaml": '''message_prefix: "{display_name}&f: "'''
    }

    for filename, content in db_files.items():
        filepath = os.path.join(db_path, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

    extra_files = {
        "welcome.txt": default_welcome,
        "rules.txt": default_rules
    }

    for filename, content in extra_files.items():
        filepath = os.path.join(extra_path, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

    root_files = {
        "conf.yaml": default_conf,
        "extensions.yaml": default_extensions
    }

    for filename, content in root_files.items():
        filepath = os.path.join(base_path, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

    print("All needed files and folders ensured.")