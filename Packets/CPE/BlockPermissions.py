from Utils.BlockPerms import permissions

async def SetPermissionsBlocks(writer):
    for block_id, values in permissions.items():
        allow, dele = values[0], values[1]      
        packet = b'\x1C' + bytes([block_id, allow, dele])
        writer.write(packet)
        await writer.drain()
