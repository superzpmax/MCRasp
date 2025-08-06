from Utils.String import WriteString
from Utils.Confloader import conf

async def TexturePack(writer):
    writer.write(b'\x28' + conf['texturepack'])