from Utils.String import WriteString
from Utils.state import cpe
async def Message(string):
        return b'\x0d' + bytes([0]) + WriteString(string)