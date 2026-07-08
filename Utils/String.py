# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

from Utils.state import cpe

def WriteString(string):
    encoded = string.encode('cp437' if cpe else 'ascii', 'replace')
    return encoded[:64].ljust(64, b' ')

def ReadString(data: bytes) -> str:
    decoded = data[:64].decode('cp437' if cpe else 'ascii', errors='replace')
    return decoded.rstrip(' \x00')
