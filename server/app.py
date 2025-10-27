# server/app.py

import asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Import our own modules
from .config import settings
from .db_async import Database
from .registry import UserRegistry
from .auth import Authenticator
from .connection import ClientSession
from .router import Router

class Server:
    """
    The main Chat Server class.
    Manages the server lifecycle and client connections.
    """
    def __init__(self):
        # Load settings from our config module
        self.host = settings.SERVER_HOST
        self.port = settings.SERVER_PORT
        
        # --- Generate RSA key pair for the server ---
        print("Generating RSA-2048 key pair for secure key exchange...")
        self.rsa_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = self.rsa_private_key.public_key()
        self.public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        print("RSA key pair generated.")
        # --- END ---
        
        # Initialize our core components
        self.db = Database(settings.DATABASE_PATH)
        self.registry = UserRegistry()
        self.authenticator = Authenticator(self.db)
        self.router = Router(self.registry, self.db)
        
        self._server = None
        print("Server components initialized.")

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        This coroutine is executed for each new client connection.
        It creates a ClientSession to manage the connection.
        """
        # Delegate the entire handling of the client to the ClientSession class.
        session = ClientSession(self, reader, writer)
        await session.handle_connection()


    async def start(self):
        """
        Starts the server and the database connection.
        """
        await self.db.connect()
        
        self._server = await asyncio.start_server(
            self.handle_client, self.host, self.port)

        addrs = ', '.join(str(sock.getsockname()) for sock in self._server.sockets)
        print(f'Serving on {addrs}')

        async with self._server:
            await self._server.serve_forever()

    async def stop(self):
        """
        Gracefully stops the server and closes the database connection.
        """
        print("Shutting down server...")
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        await self.db.close()
        print("Server shut down gracefully.")


async def main():
    server = Server()
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received.")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())