# server/secure_channel.py

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class SecureChannel:
    """
    Manages AES-GCM encryption and decryption for a secure session.
    AES-GCM is used because it provides both confidentiality and integrity.
    """
    def __init__(self, aes_key: bytes):
        if len(aes_key) != 32:
            raise ValueError("AES key must be 32 bytes for AES-256")
        self.aesgcm = AESGCM(aes_key)
        print("Secure channel initialized with AES-256-GCM.")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypts a plaintext string.
        Returns a base64-encoded string containing 'nonce:ciphertext'.
        """
        # A 12-byte nonce is required and must be unique per encryption
        nonce = os.urandom(12)
        plaintext_bytes = plaintext.encode('utf-8')
        
        ciphertext_bytes = self.aesgcm.encrypt(nonce, plaintext_bytes, None)
        
        
        encrypted_blob = base64.b64encode(nonce + ciphertext_bytes).decode('utf-8')
        return encrypted_blob

    def decrypt(self, encrypted_blob: str) -> str:
        """
        Decrypts a base64-encoded string containing 'nonce:ciphertext'.
        Returns the original plaintext string.
        """
        try:
            # Decode the base64 string to get the raw bytes
            encrypted_bytes = base64.b64decode(encrypted_blob)
            
            # The first 12 bytes are the nonce, the rest is the ciphertext
            nonce = encrypted_bytes[:12]
            ciphertext = encrypted_bytes[12:]
            
            decrypted_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            # If decryption fails (wrong key, tampered message ...), an error is raised
            print(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt or authenticate message")