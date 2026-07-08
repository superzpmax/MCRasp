# Copyright (c) 2025 SuperZPMax
#
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# License: https://polyformproject.org/licenses/noncommercial/1.0.0/
# Required Notice: Copyright (c) 2025 SuperZPMax.
# Original software created by SuperZPMax.

from Utils.String import WriteString

async def MsgAnnouncement(string):
    return b'\x0d' + bytes([100]) + WriteString(string)

async def MsgStatus1(string):
    return b'\x0d' + bytes([1]) + WriteString(string)

async def MsgStatus2(string):
    return b'\x0d' + bytes([2]) + WriteString(string)

async def MsgStatus3(string):
    return b'\x0d' + bytes([3]) + WriteString(string)

async def MsgBottomRight1(string):
    return b'\x0d' + bytes([11]) + WriteString(string)

async def MsgBottomRight2(string):
    return b'\x0d' + bytes([12]) + WriteString(string)

async def MsgBottomRight3(string):
    return b'\x0d' + bytes([13]) + WriteString(string)
