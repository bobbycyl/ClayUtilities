__all__ = ("SecureSession", "export_rsa_key")

from Crypto.Cipher import AES
from Crypto.PublicKey import RSA


class SecureSession(object):
    """使用AES-128加密会话消息"""

    def __init__(self, session_key: bytes):
        if len(session_key) == 16:
            self.__session_key = session_key
        else:
            raise ValueError("the key length must be 16")

    def encrypt(self, message: bytes) -> bytes:
        cipher = AES.new(self.__session_key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(message)  # type: ignore
        return cipher.nonce + tag + ciphertext  # type: ignore

    def decrypt(self, encrypted_message: bytes) -> bytes:
        nonce = encrypted_message[:16]
        tag = encrypted_message[16:32]
        ciphertext = encrypted_message[32:]
        cipher = AES.new(self.__session_key, AES.MODE_EAX, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)  # type: ignore


def export_rsa_key(name: str):
    key = RSA.generate(2048)

    private_key = key.export_key()
    with open("%s_priv.pem" % name, "wb") as fo_privkey:
        fo_privkey.write(private_key)

    public_key = key.publickey().export_key()
    with open("%s_pub.pem" % name, "wb") as fo_pubkey:
        fo_pubkey.write(public_key)
