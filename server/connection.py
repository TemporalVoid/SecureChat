# server/connection.py

import asyncio
import json
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

from .secure_channel import SecureChannel  # Import our new helper

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .app import Server

class ClientSession:
    def __init__(self, server: 'Server', reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.server = server
        self.reader = reader
        self.writer = writer
        
        # --- NEW STATE VARIABLES ---
        self.user_id: str | None = None
        self.full_name: str | None = None
        self.email: str | None = None # We can still store email for reference
        
        self.is_authenticated: bool = False
        self.addr = writer.get_extra_info('peername')
        self.secure_channel: SecureChannel | None = None
        print(f"ClientSession created for {self.addr!r}")

    async def _send_plaintext_json(self, data: dict):
        """Sends a plaintext JSON message. Used ONLY for the initial handshake."""
        json_message = json.dumps(data)
        self.writer.write((json_message + '\n').encode())
        await self.writer.drain()

    async def send_json(self, data: dict):
        """Encrypts and sends a JSON message through the secure channel."""
        if not self.secure_channel:
            print("Error: Attempted to send a message before secure channel was established.")
            return
        
        json_string = json.dumps(data)
        encrypted_payload = self.secure_channel.encrypt(json_string)
        
        # We wrap the encrypted payload in a simple JSON structure for consistency
        envelope = {"type": "encrypted_payload", "payload": encrypted_payload}
        final_message = json.dumps(envelope)
        
        self.writer.write((final_message + '\n').encode())
        await self.writer.drain()

    async def _handle_key_exchange(self, envelope: dict):
        """Receives and decrypts the client's AES key."""
        try:
            encrypted_key_b64 = envelope['payload']['key']
            encrypted_key = base64.b64decode(encrypted_key_b64)
            
            aes_key = self.server.rsa_private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # If we successfully decrypted the key, the handshake is complete!
            self.secure_channel = SecureChannel(aes_key)
            print(f"AES key received and decrypted from {self.addr!r}. Secure channel established.")
            
            # Send a confirmation message *through the new secure channel*
            await self.send_json({"type": "handshake_complete", "payload": {"message": "Secure channel established."}})
            return True
        except Exception as e:
            print(f"Key exchange failed for {self.addr!r}: {e}")
            return False

    async def handle_connection(self):
        """Manages the full lifecycle: handshake, authentication, messaging."""
        try:
            # --- PHASE 1: CRYPTOGRAPHIC HANDSHAKE ---
            # 1. Send the server's public RSA key to the client
            await self._send_plaintext_json({
                "type": "handshake_start",
                "payload": {"public_key": self.server.public_key_pem}
            })

            # 2. Wait for the client to send back the encrypted AES key
            line_bytes = await self.reader.readline()
            if not line_bytes:
                return # Client disconnected
            
            envelope = json.loads(line_bytes.decode())
            if envelope.get("type") != "key_exchange" or not await self._handle_key_exchange(envelope):
                print(f"Handshake failed for {self.addr!r}. Closing connection.")
                return # Handshake failed

            # --- PHASE 2: AUTHENTICATION AND MESSAGING (ENCRYPTED) ---
            while True:
                line_bytes = await self.reader.readline()
                if not line_bytes:
                    break
                
                # All subsequent messages are encrypted
                encrypted_envelope = json.loads(line_bytes.decode())
                decrypted_json_str = self.secure_channel.decrypt(encrypted_envelope['payload'])
                envelope = json.loads(decrypted_json_str)

                if not self.is_authenticated:
                    # Accept either login or signup while unauthenticated.
                    # NOTE: signup will create the user but NOT authenticate the session.
                    msg_type = envelope.get("type")
                    if msg_type == "login":
                        await self._perform_login(envelope)
                    elif msg_type == "signup":
                        await self._perform_signup(envelope)
                    else:
                        await self.send_json({
                            "type": "response",
                            "payload": {
                                "status": "error",
                                "message": "Not authenticated. Send 'login' or 'signup'."
                            }
                        })
                else:
                    await self._process_message(envelope)

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Invalid message format from {self.addr!r}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred with client {self.addr!r}: {e}")
        finally:
            if self.is_authenticated and self.user_id:
                await self.server.registry.unregister_user(self.user_id)
            self.writer.close()
            await self.writer.wait_closed()
            print(f"Connection to {self.addr!r} closed.")

    # The login and message processing logic is the same, just renamed
    # and now it receives a decrypted envelope.
    async def _perform_login(self, envelope: dict):
        try:
            payload = envelope["payload"]
            email, password = payload["email"], payload["password"]
            normalized_email = email.strip().lower()

            user_data = await self.server.authenticator.authenticate(normalized_email, password)
            if user_data:
                # --- UPDATED: Store user details in the session ---
                self.user_id = user_data['id']
                self.full_name = user_data['full_name']
                self.email = user_data['email']
                self.is_authenticated = True
                
                # Use user_id to register the session
                await self.server.registry.register_user(self.user_id, self)
                
                # Also send back the user data to the client
                await self.send_json({
                    "type": "response", 
                    "payload": {
                        "status": "ok", 
                        "message": f"Login successful. Welcome, {self.full_name}!",
                        "user_info": {"id": self.user_id, "full_name": self.full_name, "email": self.email}
                    }
                })
            else:
                await self.send_json({"type": "response", "payload": {"status": "error", "message": "Login failed. Invalid credentials."}})
        except (KeyError, TypeError):
            await self.send_json({"type": "response", "payload": {"status": "error", "message": "Malformed login envelope."}})

    async def _perform_signup(self, envelope: dict):
        try:
            if envelope.get("type") != "signup":
                await self.send_json({"type": "response", "payload": {"status": "error", "message": "Invalid type for signup"}})
                return

            payload = envelope["payload"]
            full_name = payload["full_name"]
            email = payload["email"]
            password = payload["password"]

            normalized_email = email.strip().lower()

            # hash the password before calling add_user
            # local import so we don't change top-level imports
            from .auth import hash_password

            hashed_pw = hash_password(password)

            # create the user in the DB; db.add_user returns the new user id or None if email exists
            created_id = await self.server.db.add_user(full_name, normalized_email, hashed_pw)
            if created_id:
                # Successful signup -> do NOT auto-login. Client must call login explicitly.
                await self.send_json({
                    "type": "response",
                    "payload": {
                        "status": "ok",
                        "message": "Sign-up successful. Please login to authenticate."
                    }
                })
            else:
                await self.send_json({"type": "response", "payload": {"status": "error", "message": "Sign-up failed. Email already exists."}})

        except (KeyError, TypeError):
            await self.send_json({"type": "response", "payload": {"status": "error", "message": "Malformed sign-up envelope."}})
    
    async def _process_message(self, envelope: dict):
        """
        Delegates message processing to the central router or handles session-specific commands.
        """
        msg_type = envelope.get("type")

        if msg_type == "chat":
            # --- DELEGATE to the Router ---
            await self.server.router.route_chat_message(self, envelope)
        
        elif msg_type == "whoisonline":
            # --- UPDATED to use new registry method ---
            online_users = await self.server.registry.get_online_users_list()
            await self.send_json({"type": "response", "payload": {"status": "ok", "users": online_users}})
        
        else:
            await self.send_json({"type": "response", "payload": {"status": "error", "message": f"Unknown command type: {msg_type}"}})