# server/router.py

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .registry import UserRegistry
    from .db_async import Database
    from .connection import ClientSession

class Router:
    """
    Handles routing messages between clients.
    """
    def __init__(self, registry: "UserRegistry", db: "Database"):
        self.registry = registry
        self.db = db
        print("Router initialized.")

    async def route_chat_message(self, sender_session: "ClientSession", envelope: dict):
        """
        Routes a direct message from a sender to a recipient.
        """
        try:
            payload = envelope['payload']
            recipient_id = payload['recipient_id']
            message_text = payload['text']
            
            # Prevent users from sending messages from an ID that isn't their own
            sender_id = sender_session.user_id

            # Find the recipient's session in the registry
            recipient_session = await self.registry.get_session_by_id(recipient_id)

            if recipient_session:
                # --- Recipient is ONLINE ---
                print(f"Routing message from {sender_id} to online user {recipient_id}")
                # Construct the message to be delivered to the recipient
                delivery_envelope = {
                    "type": "new_message",
                    "payload": {
                        "sender_id": sender_id,
                        "sender_name": sender_session.full_name,
                        "text": message_text
                    }
                }
                await recipient_session.send_json(delivery_envelope)
            else:
                # --- Recipient is OFFLINE ---
                print(f"Recipient {recipient_id} is offline. Storing message.")
                # You might want to check if the recipient_id is a valid user in the DB first
                await self.db.store_message(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    payload=message_text
                )
                # inform the sender that the message was stored
                await sender_session.send_json({
                    "type": "response",
                    "payload": {
                        "status": "info",
                        "message": "Recipient is offline. Message stored."
                    }
                })

        except (KeyError, TypeError):
            await sender_session.send_json({"type": "response", "payload": {"status": "error", "message": "Malformed chat envelope."}})