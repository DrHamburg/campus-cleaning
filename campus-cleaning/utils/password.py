# utils/password.py
# Mirrors backend/utils/password.js from the Node.js version.

import re
import bcrypt

SALT_ROUNDS = 10


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=SALT_ROUNDS)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_password_strength(password):
    """Returns (valid: bool, message: str|None). Same rules as password.js:
    min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character."""
    if not isinstance(password, str) or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must contain at least one special character."
    return True, None
