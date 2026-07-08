# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

import Utils.state as state
from Utils.Logger import logger

def CheckExtension(name: str) -> bool:
    if state.cpe:
        exts = getattr(state, "extensions", {})
        if not isinstance(exts, dict):
            return False
        val = exts.get(name)
        enabled = isinstance(val, int) and val >= 1
       
        return enabled
    else:
        return False
