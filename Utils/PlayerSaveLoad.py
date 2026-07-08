# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import os
import yaml
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAYERS_YML = PROJECT_ROOT / "db" / "players.yml"
def ResourcePath(relative_path: str) -> str:
    return str(PROJECT_ROOT / relative_path)

def LoadPlayers():
    if not PLAYERS_YML.exists():
        return {}
    with open(PLAYERS_YML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def SavePlayers(data):
    PLAYERS_YML.parent.mkdir(parents=True, exist_ok=True)
    with open(PLAYERS_YML, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
