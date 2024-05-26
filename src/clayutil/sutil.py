import hashlib

from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

__all__ = (
    "SecureSession",
    "export_rsa_key",
    "sha256sum",
)


class SecureSession(object):
    def __init__(self, session_key: bytes):
        if len(session_key) == 16:
            self.__session_key = session_key
        else:
            raise ValueError("the key length must be 16")

    def encrypt(self, message: bytes) -> bytes:
        cipher = AES.new(self.__session_key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(message)
        return cipher.nonce + tag + ciphertext

    def decrypt(self, encrypted_message: bytes) -> bytes:
        nonce = encrypted_message[:16]
        tag = encrypted_message[16:32]
        ciphertext = encrypted_message[32:]
        cipher = AES.new(self.__session_key, AES.MODE_EAX, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)


def export_rsa_key(name: str) -> None:
    key = RSA.generate(2048)

    private_key = key.export_key()
    with open("%s_priv.pem" % name, "wb") as fo:
        fo.write(private_key)

    public_key = key.publickey().export_key()
    with open("%s_pub.pem" % name, "wb") as fo:
        fo.write(public_key)


def sha256sum(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
