import textwrap
from Packets.Message import Message

async def ErrorChat(obj, writer, string):
    prefix = "&cErr: &f"
    width = 64 - len(prefix)  

    lines = textwrap.wrap(string, width=width)

    for idx, line in enumerate(lines):
        if idx == 0:
            formatted = f"{prefix}{line}"
        elif idx < len(lines) - 1:
            formatted = f"&c| &f{line}"
        else:
            formatted = f"&c> &f{line}"

        obj.writer.write(await Message(formatted))
