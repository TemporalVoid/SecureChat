# server/auth.py

import bcrypt
import asyncio

# We import the Database class from our previously created module.
# The '.' signifies a relative import from the same package (the 'server' folder).
from .db_async import Database, DB_FILE


def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt.
    Returns the hashed password as a UTF-8 string suitable for storing in the DB.
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')


def check_password(password: str, hashed_password: str) -> bool:
    """
    Checks if a plain-text password matches a stored hash.
    """
    password_bytes = password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)


class Authenticator:
    """
    Handles user authentication by checking credentials against the database.
    Uses email as the unique identifier for users.
    """
    def __init__(self, db: Database):
        # Dependency injection of the Database instance
        self.db = db
        print("Authenticator initialized.")

    async def authenticate(self, email: str, password: str) -> dict | None:
        """
        Authenticates a user by email and password.

        Args:
            email: The user's email.
            password: The user's plain-text password.

        Returns:
            A dictionary with user data upon successful authentication, otherwise None.
        """
        normalized_email = email.strip().lower()
        print(f"Attempting to authenticate user with email '{normalized_email}'...")
        user_row = await self.db.get_user_by_email(normalized_email)

        if not user_row:
            print(f"Authentication failed: User with email '{normalized_email}' not found.")
            return None  # User does not exist

        # The DB stores the hashed password in column 'password'
        stored_hash = user_row['password']
        if check_password(password, stored_hash):
            print(f"Authentication successful for user '{normalized_email}'.")
            return dict(user_row)
        else:
            print(f"Authentication failed: Invalid password for user '{normalized_email}'.")
            return None  # Password mismatch


# --- Self-testing block ---
async def main_test():
    """
    This function is for testing the Authenticator class independently.
    """
    print("--- Running Authenticator Module Test ---")

    # Use a clean test database
    if DB_FILE.exists():
        DB_FILE.unlink()

    db = Database(DB_FILE)
    await db.connect()

    try:
        # --- Setup: Create a test user ---
        print("\n[Setup] Creating a test user 'Test User' with email 'test@example.com' and password 'password123'")
        test_password = "password123"
        hashed_pw = hash_password(test_password)
        # add_user(full_name, email, password_hashed)
        created_id = await db.add_user("Test User", "test@example.com", hashed_pw)
        assert created_id is not None
        print(f"Created user id: {created_id}")

        # --- Test Case 1: Successful Authentication ---
        print("\n[Test Case 1] Authenticating with correct credentials")
        authenticator = Authenticator(db)
        user_data = await authenticator.authenticate("test@example.com", "password123")
        assert user_data is not None
        assert user_data['email'] == "test@example.com"
        print("Authentication success test passed.")

        # --- Test Case 2: Failed Authentication (Wrong Password) ---
        print("\n[Test Case 2] Authenticating with wrong password")
        user_data_fail = await authenticator.authenticate("test@example.com", "wrongpassword")
        assert user_data_fail is None
        print("Wrong-password test passed.")

        # --- Test Case 3: Failed Authentication (Non-existent User) ---
        print("\n[Test Case 3] Authenticating with non-existent user")
        user_data_nonexistent = await authenticator.authenticate("nonexistent@example.com", "password123")
        assert user_data_nonexistent is None
        print("Non-existent-user test passed.")

    except AssertionError as ae:
        print(f"Assertion failed during tests: {ae}")
    except Exception as e:
        print(f"An error occurred during the test: {e}")
    finally:
        await db.close()
        print("\n--- Authenticator Module Test Finished ---")


if __name__ == "__main__":
    asyncio.run(main_test())
