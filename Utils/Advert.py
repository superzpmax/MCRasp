import asyncio
import urllib.parse
import urllib.request

from Utils.Logger import logger
from Utils.Confloader import conf
import Utils.state as state

async def AdvertHeartbeatBCV2():
    logger.info("Initialized Betacraft (v2) Heartbeat")

    import json
    full_sent = False
    private_key = conf["private-key"]
    connect_address = f"{conf['address']}:{state.PORT}"

    while not state.stop:
        try:
            unique_ips = set(p.addr[0] for p in state.players.values())
            online_players = len(unique_ips)
            players_list = [{"username": p.name} for p in state.players.values() if p.addr[0] in unique_ips]
            base_data = {
                "private_key": private_key,
                "socket": connect_address,
                "online_players": online_players,
                "players": players_list,
            }

            if not full_sent:
                full_sent = True
                data = {
                    **base_data,
                    "name": conf["name"],
                    "icon": "",
                    "game_version": "c0.30-c-1900",
                    "v1_version": "c0.30-c-1900",
                    "protocol": "classic_7",
                    "category": "classic",
                    "description": conf["description"],
                    "is_public": "true",
                    "max_players": 127,
                    "software": {"name": state.SOFTWARE.replace("&", ""), "version": "1.0.0"},
                    "online_mode": "true"
                }
                url = "https://api.betacraft.uk/v2/server_update"
            else:
                data = base_data
                url = "https://api.betacraft.uk/v2/server_update_ping"

            headers = {"Content-Type": "application/json"}
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
            with urllib.request.urlopen(req) as res:
                logger.info(f"BCV2 Heartbeat response: {res.read().decode()}")

        except Exception as e:
            logger.error(f"BCV2 Heartbeat error: {e}")

        await asyncio.sleep(45)

async def AdvertHeartbeat():
    logger.info("Initialized ClassiCube Heartbeat")
    while not state.stop:
        try:
            name_list = list(p.name for p in state.players.values())
            data = {
                'name': state.SERVER_NAME,
                'port': state.PORT,
                'users': len(name_list),
                'max': 127,
                'salt': state.SALT,
                'software': state.SOFTWARE,
                'web': 'false',
                'public': 'true'
            }
            url = 'https://www.classicube.net/server/heartbeat/?' + urllib.parse.urlencode(data)
            with urllib.request.urlopen(url) as response:
                result = response.read().decode()
                
                import json
                try:
                    parsed = json.loads(result)
                    if parsed.get("status") == "fail":
                        errors = parsed.get("errors", [])
                        for error in errors:
                            logger.error(f"ClassiCube error: {error[0]}")
                except Exception:
                    if "fail" in result.lower():
                        logger.error(f"ClassiCube Heartbeat failed with response: {result}")

        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
        await asyncio.sleep(45)