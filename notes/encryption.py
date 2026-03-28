from cryptography.fernet import Fernet
from .env import NOTE_ENCRYPTION_KEY

cipher = Fernet(NOTE_ENCRYPTION_KEY)

def encrypt_text(text: str):
    return cipher.encrypt(text.encode()).decode()


def decrypt_text(text: str):
    return cipher.decrypt(text.encode()).decode()