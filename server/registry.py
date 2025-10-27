# server/registry.py

import asyncio
from typing import Dict, Optional, List, Any

ClientSession = object 

class UserRegistry:
    def __init__(self):
        # The core data structure now maps user_id (UUID string) to their session objects.
        self._online_users: Dict[str, ClientSession] = {}
        self._lock = asyncio.Lock()
        print("UserRegistry initialized.")

    async def register_user(self, user_id: str, session: ClientSession) -> None:
        """Registers a user as online using their unique user ID."""
        async with self._lock:
            if user_id in self._online_users:
                print(f"Warning: User ID '{user_id}' is already registered. Overwriting session.")
            self._online_users[user_id] = session
            print(f"User with ID '{user_id}' registered.")

    async def unregister_user(self, user_id: str) -> None:
        """Removes a user from the online registry using their user ID."""
        async with self._lock:
            if user_id in self._online_users:
                del self._online_users[user_id]
                print(f"User with ID '{user_id}' unregistered.")

    async def get_session_by_id(self, user_id: str) -> Optional[ClientSession]:
        """Retrieves the session object for a given online user by their ID."""
        async with self._lock:
            return self._online_users.get(user_id)

    async def get_online_users_list(self) -> List[Dict[str, Any]]:
        """
        Returns a list of dictionaries, each representing an online user.
        """
        async with self._lock:
            # We access attributes that we will add to the ClientSession object
            return [
                {"id": session.user_id, "full_name": session.full_name}
                for session in self._online_users.values()
                if session.is_authenticated
            ]