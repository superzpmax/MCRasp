from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(stored_hash: str, provided_password: str) -> bool:
    try:
        return ph.verify(stored_hash, provided_password)
    except VerifyMismatchError:
        return False
