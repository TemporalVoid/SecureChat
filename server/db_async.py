# server/db_async.py

import aiosqlite
import asyncio
from pathlib import Path
import uuid
from .config import settings

# --- Constants ---
DB_FILE = settings.DATABASE_PATH


class Database:
    """
    Asynchronous wrapper for the SQLite database.
    Manages connections and provides methods for data operations.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = None
        print(f"Database will be initialized at: {self.db_path}")

    async def connect(self):
        # Establish a connection to the SQLite database.
        try:
            self._conn = await aiosqlite.connect(self.db_path)
            # Enable row factory to get results as dictionaries
            self._conn.row_factory = aiosqlite.Row
            print("Database connection successful.")
            # Ensure the schema is created on first connect
            await self._initialize_schema()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise

    async def close(self):
        # Gracefully close the database connection.
        if self._conn:
            await self._conn.close()
            print("Database connection closed.")

    async def _initialize_schema(self):
        # Create the necessary tables if they don't already exist.
        cursor = await self._conn.cursor()

        # Users table: id is a deterministic uuid5 (stored as TEXT)
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                full_name TEXT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Messages table: sender_id/recipient_id reference users.id (TEXT)
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                payload_blob BLOB NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (recipient_id) REFERENCES users (id)
            )
        """)

        await self._conn.commit()
        print("Schema initialized successfully.")

    def _generate_user_id(self, email: str) -> str:
        """
        Deterministic UUID5 generated from email.
        We normalize the email by lowercasing and stripping whitespace.
        """
        norm_email = email.strip().lower()
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, norm_email))

    async def add_user(self, full_name: str, email: str, password: str) -> str | None:
        """
        Adds a new user to the database.
        Returns the new user's id (UUID string) on success, or None if the email already exists.
        """
        user_id = self._generate_user_id(email)
        try:
            cursor = await self._conn.execute(
                "INSERT INTO users (id, full_name, email, password) VALUES (?, ?, ?, ?)",
                (user_id, full_name, email, password)
            )
            await self._conn.commit()
            print(f"User '{email}' added with ID: {user_id}")
            return user_id
        except aiosqlite.IntegrityError:
            # This error occurs if the email is not unique.
            print(f"User with email '{email}' already exists.")
            return None

    async def get_user_by_email(self, email: str) -> aiosqlite.Row | None:
        """
        Fetches a user's data from the database by their email.
        Returns a Row object (like a dict) or None if not found.
        """
        cursor = await self._conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        )
        user_row = await cursor.fetchone()
        return user_row

    async def get_user_by_id(self, user_id: str) -> aiosqlite.Row | None:
        """Helper to fetch user by id (UUID string)."""
        cursor = await self._conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
        return await cursor.fetchone()
    
    async def store_message(self, sender_id: str, recipient_id: str, payload: str) -> int:
        """Stores a chat message in the database."""
        cursor = await self._conn.execute(
            "INSERT INTO messages (sender_id, recipient_id, payload_blob) VALUES (?, ?, ?)",
            (sender_id, recipient_id, payload.encode('utf-8'))
        )
        await self._conn.commit()
        print(f"Stored offline message from {sender_id} to {recipient_id}")
        return cursor.lastrowid


# --- Self-testing block ---
async def main_test():
    """
    This function is for testing the Database class independently.
    It demonstrates how to use the class methods.
    """
    print("--- Running Database Module Test ---")

    # Ensure we start with a clean slate for testing
    if DB_FILE.exists():
        DB_FILE.unlink()

    db = Database(DB_FILE)

    try:
        await db.connect()

        # --- Test Case 1: Add a new user ---
        print("\n[Test Case 1] Adding a new user 'alice@example.com'")
        alice_id = await db.add_user("Alice Wonderland", "alice@example.com", "hashed_password_alice")
        assert alice_id is not None
        print(f"alice_id: {alice_id}")

        # --- Test Case 2: Try to add the same user again ---
        print("\n[Test Case 2] Trying to add 'alice@example.com' again (should fail)")
        duplicate_id = await db.add_user("Alice Wonderland", "alice@example.com", "hashed_password_alice")
        assert duplicate_id is None

        # --- Test Case 3: Fetch an existing user by email ---
        print("\n[Test Case 3] Fetching user 'alice@example.com'")
        alice_data = await db.get_user_by_email("alice@example.com")
        assert alice_data is not None
        assert alice_data['email'] == 'alice@example.com'
        assert alice_data['id'] == alice_id
        print(f"Fetched data: id={alice_data['id']}, email={alice_data['email']}, full_name={alice_data['full_name']}")

        # --- Test Case 4: Fetch a non-existent user ---
        print("\n[Test Case 4] Fetching non-existent user 'bob@example.com'")
        bob_data = await db.get_user_by_email("bob@example.com")
        assert bob_data is None
        print("User 'bob@example.com' not found, as expected.")

    except AssertionError as ae:
        print(f"Assertion failed during test: {ae}")
    except Exception as e:
        print(f"An error occurred during the test: {e}")
    finally:
        await db.close()
        print("\n--- Database Module Test Finished ---")


if __name__ == "__main__":
    # This allows us to run this file directly to test its functionality.
    asyncio.run(main_test())
