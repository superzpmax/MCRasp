from typing import Mapping
from Utils.Chatter import ErrorChat

def NormalizeNode(node: str) -> str:
    return (node or "").strip().lower()

def MatchPermission(perms: Mapping[str, bool], node: str, fallback: bool = False) -> bool:
    if not perms:
        return fallback

    node = NormalizeNode(node)
    if node in perms:
        return bool(perms[node])

    parts = node.split(".")
    for i in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:i]) + ".*"
        if candidate in perms:
            return bool(perms[candidate])

    if "*" in perms:
        return bool(perms["*"])

    if "other" in perms:
        return bool(perms["other"])

    return fallback

def HasPermission(player, node: str) -> bool:
    if getattr(player, "IsConsole", False):
        return True

    perms = getattr(player, "permissions", None) or {}
    return MatchPermission(perms, node, fallback=False)
async def RequirePermission(player, node: str, command: str) -> bool:
    if not HasPermission(player, node):
        await ErrorChat(player, player.writer, f"Insufficient permissions.")
        return False
    return True