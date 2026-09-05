from cryptography.fernet import Fernet

def generate_key() -> str:
    """Generates a URL-safe base64-encoded 32-byte key."""
    return Fernet.generate_key().decode()

def encrypt_data(data: bytes, key: str) -> bytes:
    """Encrypts plaintext bytes with the given Fernet key."""
    f = Fernet(key.encode())
    return f.encrypt(data)

def decrypt_data(token: bytes, key: str) -> bytes:
    """Decrypts ciphertext bytes with the given Fernet key."""
    f = Fernet(key.encode())
    return f.decrypt(token)