from constants import Constants
from terminal import Terminal
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
from secrets import token_bytes
from typing import Any

class Encryption:
    secret: bytes = b""

    @staticmethod
    def __setup_aes_key():
        Encryption.secret = token_bytes(Constants.KEY_SIZE)

    @staticmethod
    def __generate_nonce() -> bytes:
        return token_bytes(Constants.NONCE_SIZE)

    @staticmethod
    def __create_cipher(nonce: bytes):
        return AES.new(Encryption.secret, AES.MODE_EAX, nonce=nonce, mac_len=Constants.TAG_SIZE)

    @staticmethod
    def __create_cipher_new_nonce():
        nonce = Encryption.__generate_nonce()
        return Encryption.__create_cipher(nonce)

    @staticmethod
    def encrypt_aes_with_rsa(key: bytes) -> bytes:
        Terminal.debug(f"creating secret...")

        Encryption.__setup_aes_key()
        Terminal.debug(f"secret: {Encryption.secret}")

        public_key = RSA.import_key(key)
        Terminal.debug(f"imported public key: {public_key}")

        rsa_cipher = PKCS1_OAEP.new(public_key)
        Terminal.debug(f"created cipher: can encrypt: {rsa_cipher.can_encrypt()}")

        Terminal.debug(f"created rsa cipher: {rsa_cipher}")

        encrypted_secret = rsa_cipher.encrypt(Encryption.secret)
        Terminal.debug(f"encrypted secret: {encrypted_secret}")

        return encrypted_secret

    @staticmethod
    def encrypt_with_aes(data: bytes) -> list[bytes]:
        cipher = Encryption.__create_cipher_new_nonce()

        ciphertext, tag = cipher.encrypt_and_digest(data)
        nonce = cipher.nonce

        Terminal.debug(f"nonce: {nonce}")
        Terminal.debug(f"tag: {tag}:")
        Terminal.debug(f"ciphertext: {ciphertext}:")

        return [nonce + tag + ciphertext]

    @staticmethod
    def decrypt_with_aes(data: bytes) -> bytes:
        nonce_size = Constants.NONCE_SIZE
        nonce_tag_size = Constants.NONCE_SIZE + Constants.TAG_SIZE

        nonce = data[:nonce_size]
        tag = data[nonce_size:nonce_tag_size]
        ciphertext = data[nonce_tag_size:]

        Terminal.debug(f"nonce: {nonce}")
        Terminal.debug(f"tag: {tag}")
        Terminal.debug(f"ciphertext: {ciphertext}")

        cipher = Encryption.__create_cipher(nonce)

        data = cipher.decrypt(ciphertext)

        try:
            cipher.verify(tag)
            return data
        except ValueError:
            Terminal.error("error while decrypting data: decryption key is incorrect or message is corrupted.")

        return b""
