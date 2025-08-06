from Utils.state import cpe

def WriteString(string):
    encoded = string.encode('cp437' if cpe else 'ascii', 'replace')
    return encoded[:64].ljust(64, b' ')

def ReadString(data: bytes) -> str:
    decoded = data[:64].decode('cp437' if cpe else 'ascii', errors='replace')
    return decoded.rstrip(' \x00')
