# client/network_client.py
import asyncio
import threading
import json
import queue
import time
import os
import base64
from typing import Optional

# NEW: Import cryptography modules
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from .secure_channel import SecureChannel
from .config import settings

DEFAULT_HOST = settings.SERVER_HOST
DEFAULT_PORT =  settings.SERVER_PORT
_INTERNAL_STOP = {"_internal_stop": True}


class NetworkClient:
    def __init__(self, gui_queue: "queue.Queue"):
        self.gui_queue = gui_queue
        self.outgoing: "queue.Queue[dict]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._secure_channel: Optional[SecureChannel] = None  # NEW: For encryption

    # ... start, stop, send methods remain the same ...
    def start(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, args=(host, port), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        try:
            self.outgoing.put_nowait(_INTERNAL_STOP)
        except Exception:
            pass
        if self._loop:
            try:
                asyncio.run_coroutine_threadsafe(self._close_connection(), self._loop)
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1)

    def send(self, obj: dict):
        if not isinstance(obj, dict):
            raise TypeError("NetworkClient.send expects a dict")
        self.outgoing.put(obj)

    def _run_loop(self, host: str, port: int):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._async_main(host, port))
        except Exception as e:
            try:
                self.gui_queue.put({"type": "network_error", "payload": f"network loop error: {e}"})
            except Exception:
                print("network loop error:", e)
        finally:
            try:
                self._loop.close()
            except Exception:
                pass
            self._loop = None

    async def _perform_handshake(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> SecureChannel:
        # 1. Receive the server's public key
        line = await reader.readline()
        pubkey_envelope = json.loads(line.decode())
        if pubkey_envelope.get("type") != "handshake_start":
            raise ConnectionError("Server did not start handshake correctly.")
        
        server_pubkey_pem = pubkey_envelope['payload']['public_key'].encode()
        server_public_key = serialization.load_pem_public_key(server_pubkey_pem)

        # 2. Generate a symmetric AES key
        aes_key = os.urandom(32)  # 256-bit key

        # 3. Encrypt the AES key with the server's public key
        encrypted_aes_key = server_public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        encrypted_key_b64 = base64.b64encode(encrypted_aes_key).decode('utf-8')

        # 4. Send the encrypted key back to the server
        key_exchange_envelope = {
            "type": "key_exchange",
            "payload": {"key": encrypted_key_b64}
        }
        writer.write((json.dumps(key_exchange_envelope) + "\n").encode())
        await writer.drain()

        # 5. Initialize the secure channel and wait for confirmation
        secure_channel = SecureChannel(aes_key)
        
        # 6. Receive encrypted confirmation
        line = await reader.readline()
        encrypted_confirm_env = json.loads(line.decode())
        decrypted_json = secure_channel.decrypt(encrypted_confirm_env['payload'])
        confirmation = json.loads(decrypted_json)

        if confirmation.get("type") != "handshake_complete":
            raise ConnectionError("Server did not confirm secure channel.")
        
        print("Cryptographic handshake successful. Secure channel established.")
        return secure_channel

    async def _async_main(self, host: str, port: int):
        retry_delay = 1.0
        while not self._stop_event.is_set():
            try:
                reader, writer = await asyncio.open_connection(host, port)
                self._writer = writer
                
                # --- NEW: Perform handshake ---
                self._secure_channel = await self._perform_handshake(reader, writer)
                
                self.gui_queue.put({"type": "network_connected", "payload": {"host": host, "port": port}})
                await asyncio.gather(self._recv_loop(reader), self._send_loop())
            except Exception as e:
                self.gui_queue.put({"type": "network_error", "payload": f"connection/handshake error: {e}"})
                await asyncio.sleep(retry_delay)
                retry_delay = min(10.0, retry_delay * 2)
            finally:
                self._secure_channel = None # Clear secure channel on disconnect
                if self._writer:
                    try:
                        self._writer.close()
                        await self._writer.wait_closed()
                    except Exception: pass
                    self._writer = None
                if not self._stop_event.is_set():
                    self.gui_queue.put({"type": "network_disconnected", "payload": None})
        self.gui_queue.put({"type": "network_stopped", "payload": None})

    async def _recv_loop(self, reader: asyncio.StreamReader):
        try:
            while not self._stop_event.is_set():
                line = await reader.readline()
                if not line: return
                
                # --- NEW: Decrypt the message ---
                if not self._secure_channel: return
                try:
                    # The entire line is an envelope containing the encrypted payload
                    outer_envelope = json.loads(line.decode())
                    decrypted_json_str = self._secure_channel.decrypt(outer_envelope['payload'])
                    obj = json.loads(decrypted_json_str)
                    
                    if isinstance(obj, dict):
                        self.gui_queue.put(obj)
                except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
                    self.gui_queue.put({"type": "network_error", "payload": "invalid/undecryptable message from server"})
        except Exception as e:
            self.gui_queue.put({"type": "network_error", "payload": f"recv loop error: {e}"})

    async def _send_loop(self):
        loop = asyncio.get_running_loop()
        try:
            while not self._stop_event.is_set():
                item = await loop.run_in_executor(None, self.outgoing.get)
                if item is _INTERNAL_STOP or (isinstance(item, dict) and item.get("_internal_stop")): return
                if not isinstance(item, dict): continue
                if self._writer is None or self._secure_channel is None:
                    self.gui_queue.put({"type": "network_error", "payload": "not connected"})
                    continue
                
                # --- NEW: Encrypt the message ---
                try:
                    json_string = json.dumps(item)
                    encrypted_payload = self._secure_channel.encrypt(json_string)
                    envelope = {"type": "encrypted_payload", "payload": encrypted_payload}
                    data = (json.dumps(envelope) + "\n").encode()

                    self._writer.write(data)
                    await self._writer.drain()
                except Exception as e:
                    self.gui_queue.put({"type": "network_error", "payload": f"send error: {e}"})
                    return
        except Exception as e:
            self.gui_queue.put({"type": "network_error", "payload": f"send loop exception: {e}"})

    async def _close_connection(self):
        self._stop_event.set()
        try:
            self.outgoing.put_nowait(_INTERNAL_STOP)
        except Exception: pass
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception: pass
        await asyncio.sleep(0.01)