import hashlib
import secrets
from io import BytesIO

from Crypto.Cipher import AES, PKCS1_OAEP
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

    @classmethod
    def create_from_public_key(cls, credential: bytes, pub_key: RSA.RsaKey) -> tuple["SecureSession", bytes, bytes]:
        session_key = secrets.token_bytes(16)
        cipher_rsa = PKCS1_OAEP.new(pub_key)
        enc_session_key = cipher_rsa.encrypt(session_key)
        secure_session = cls(session_key)
        enc_credential = secure_session.encrypt(credential)
        return secure_session, enc_session_key, enc_credential

    @classmethod
    def create_from_auth_request(cls, pri_key: RSA.RsaKey, auth_request: bytes) -> tuple["SecureSession", bytes]:
        auth = BytesIO(auth_request)
        enc_session_key, nonce, tag, ciphertext = [auth.read(x) for x in (pri_key.size_in_bytes(), 16, 16, -1)]
        cipher_rsa = PKCS1_OAEP.new(pri_key)
        session_key = cipher_rsa.decrypt(enc_session_key)
        secure_session = cls(session_key)
        credential = secure_session.decrypt(ciphertext)
        return secure_session, credential


def export_rsa_key(name: str) -> None:
    key = RSA.generate(2048)

    private_key = key.export_key()
    with open("%s_pri.pem" % name, "wb") as fo:
        fo.write(private_key)

    public_key = key.publickey().export_key()
    with open("%s_pub.pem" % name, "wb") as fo:
        fo.write(public_key)


def sha256sum(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
