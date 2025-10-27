# client/gui_windows/main_chat_window.py
import customtkinter as ctk
import datetime
from typing import List, Dict, Callable

class NewChatWindow(ctk.CTkToplevel):
    """A popup window to display online users and start a new chat."""
    def __init__(self, parent, online_users: List[Dict], on_select: Callable):
        super().__init__(parent)
        self.title("Start New Chat")
        self.geometry("300x400")
        self.transient(parent) # Keep popup on top of the main window
        self.grab_set() # Modal behavior

        self.on_select_callback = on_select
        self.online_users = online_users

        label = ctk.CTkLabel(self, text="Select a user to chat with:", font=ctk.CTkFont(weight="bold"))
        label.pack(padx=10, pady=10)

        scrollable_frame = ctk.CTkScrollableFrame(self)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        if not self.online_users:
            no_users_label = ctk.CTkLabel(scrollable_frame, text="No other users are online.")
            no_users_label.pack(pady=20)
        else:
            for user in self.online_users:
                # user is a dict {'id': '...', 'full_name': '...'}
                btn = ctk.CTkButton(
                    scrollable_frame,
                    text=user.get('full_name', 'Unknown User'),
                    command=lambda u=user: self._on_user_selected(u)
                )
                btn.pack(fill="x", padx=5, pady=3)

    def _on_user_selected(self, user: Dict):
        self.on_select_callback(user)
        self.destroy()


class MainWindow(ctk.CTkFrame):
    view_name = "Secure Chat"

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.grid_columnconfigure(0, weight=1, minsize=360)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # store state
        self.current_chat_id = None
        self.chats = {} # Will be populated from state manager
        self.online_users = [] # List of {'id': '...', 'full_name': '...'}
        self.new_chat_window = None

        self._create_left_frame()
        self._create_right_frame()
        self._load_and_populate_chats()

    def _create_left_frame(self):
        left = ctk.CTkFrame(self, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        topbar = ctk.CTkFrame(left, height=56, corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(topbar, text="Secure Chat", anchor="w")
        title.grid(row=0, column=0, padx=12, pady=12, sticky="w")
        # Connect the '+' button to its new function
        new_btn = ctk.CTkButton(topbar, text="+", width=36, height=36, corner_radius=18, command=self._on_new_chat_click)
        new_btn.grid(row=0, column=1, padx=12, pady=8, sticky="e")

        search_frame = ctk.CTkFrame(left, height=60)
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=8)
        search_frame.grid_columnconfigure(0, weight=1)
        search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search or start new chat")
        search_entry.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

        self.chat_list_scroll = ctk.CTkScrollableFrame(left)
        self.chat_list_scroll.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0,8))
        self.chat_list_scroll.grid_columnconfigure(0, weight=1)

    def _create_chat_item(self, parent, chat_id, name, preview, time_str):
        item = ctk.CTkFrame(parent, height=72)
        item.grid_columnconfigure(1, weight=1)
        avatar = ctk.CTkLabel(item, text=name[:1].upper(), width=48, height=48, corner_radius=24, anchor="center")
        avatar.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        name_lbl = ctk.CTkLabel(item, text=name, anchor="w")
        name_lbl.grid(row=0, column=1, sticky="ew", padx=(0,8))
        time_lbl = ctk.CTkLabel(item, text=time_str, anchor="e")
        time_lbl.grid(row=0, column=2, sticky="e", padx=(0,10))
        preview_lbl = ctk.CTkLabel(item, text=preview, anchor="w")
        preview_lbl.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(0,8))
        item.pack(fill="x", expand=True, padx=4, pady=2)
        
        def on_select(event=None, cid=chat_id):
            self._open_chat(cid)
        item.bind("<Button-1>", on_select)
        for w in item.winfo_children():
            w.bind("<Button-1>", on_select)
        return item

    def _load_and_populate_chats(self):
        # In a real app, you'd load existing chat partners from the state manager
        self.chats = self._sample_chats() # Using sample data for now
        self._populate_chat_list()

    def _populate_chat_list(self):
        for widget in self.chat_list_scroll.winfo_children():
            widget.destroy()
        for cid, info in self.chats.items():
            time_str = info.get("last_time", "")
            preview = info.get("last_message", "")
            self._create_chat_item(self.chat_list_scroll, cid, info["name"], preview, time_str)

    def _create_right_frame(self):
        right = ctk.CTkFrame(self, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=0, pady=6)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        self.header = ctk.CTkFrame(right, height=64, corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(1, weight=1)
        self.h_avatar = ctk.CTkLabel(self.header, text="?", width=40, height=40, corner_radius=20)
        self.h_avatar.grid(row=0, column=0, padx=12, pady=10)
        self.h_name = ctk.CTkLabel(self.header, text="Select a chat")
        self.h_name.grid(row=0, column=1, sticky="w")
        composer = ctk.CTkFrame(right, height=96, corner_radius=0)
        composer.grid(row=2, column=0, sticky="ew", pady=(4,0))
        composer.grid_columnconfigure(1, weight=1)
        self.history_scroll = ctk.CTkScrollableFrame(right)
        self.history_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(6,4))
        self.history_scroll.grid_columnconfigure(0, weight=1)
        self.message_text = ctk.CTkTextbox(composer, height=56)
        self.message_text.grid(row=0, column=1, sticky="ew", padx=(0,8), pady=8)
        self.message_text.bind("<Return>", self._on_enter_send)
        self.send_btn = ctk.CTkButton(composer, text="Send", width=80, command=self._on_send)
        self.send_btn.grid(row=0, column=2, padx=8, pady=8)

    def _open_chat(self, chat_id):
        if self.current_chat_id == chat_id:
            return
        self.current_chat_id = chat_id
        info = self.chats.get(chat_id, {"name": chat_id, "messages": []})
        self.h_avatar.configure(text=info.get("name", "?")[:1].upper())
        self.h_name.configure(text=info.get("name", "Unknown"))
        for w in self.history_scroll.winfo_children():
            w.destroy()
        
        persisted = self.controller.state_manager.get_messages(chat_id)
        current_user_id = self.controller.state_manager.get_user_id()
        for msg in persisted:
            sender_id = msg.get("sender", "them")
            self._add_message(
                "me" if sender_id == current_user_id else "them",
                msg.get("text", ""),
                msg.get("time")
            )

    def _add_message(self, sender, text, time=None):
        # (This function remains largely the same)
        wrap = ctk.CTkFrame(self.history_scroll)
        wrap.grid_columnconfigure(0, weight=1)
        anchor = "e" if sender == "me" else "w"
        padx = (60,12) if sender == "me" else (12,60)
        bubble = ctk.CTkLabel(wrap, text=text, corner_radius=12, wraplength=520, anchor="w",
                              fg_color="#3475f0" if sender == "me" else "#404040")
        bubble.grid(row=0, column=0, sticky=anchor, padx=padx, pady=6)
        if time is not None:
            try:
                if "T" in time:
                    time = datetime.datetime.fromisoformat(time).strftime("%H:%M")
            except Exception: pass
            time_lbl = ctk.CTkLabel(wrap, text=time, anchor=anchor)
            time_lbl.grid(row=1, column=0, sticky=anchor, padx=padx, pady=(0,8))
        wrap.pack(fill="x", padx=6)
        self.after(100, self.history_scroll._parent_canvas.yview_moveto, 1.0)


    def _on_enter_send(self, event=None):
        self._on_send()
        return "break"

    def _on_send(self):
        text = self.message_text.get("1.0", "end").strip()
        if not text or not self.current_chat_id:
            return
        
        # --- THIS IS THE KEY CHANGE FOR SERVER COMPATIBILITY ---
        # The 'current_chat_id' is the recipient's user ID.
        self.controller.network_client.send({
            "type": "chat",
            "payload": {"recipient_id": self.current_chat_id, "text": text}
        })
        # --- END OF KEY CHANGE ---
        
        self._add_message("me", text)
        self.controller.state_manager.save_message(
            chat_id=self.current_chat_id,
            sender=self.controller.state_manager.get_user_id(),
            text=text
        )
        self.message_text.delete("1.0", "end")

    def add_new_message(self, payload: Dict):
        # Server sends: {'sender_id': '...', 'sender_name': '...', 'text': '...'}
        sender_id = payload.get("sender_id")
        if not sender_id: return

        text = payload.get("text", "")
        ts = datetime.datetime.utcnow().isoformat()
        
        self.controller.state_manager.save_message(sender_id, sender_id, text, ts)
        
        if sender_id not in self.chats:
            self.chats[sender_id] = {"name": payload.get("sender_name", sender_id), "messages": []}
            self._populate_chat_list()

        if self.current_chat_id == sender_id:
            self._add_message("them", text, ts)

    def update_online_list(self, users: List[Dict]):
        my_user_id = self.controller.state_manager.get_user_id()
        # Filter out the current user from the list
        self.online_users = [user for user in users if user.get('id') != my_user_id]
        print("Updated online users:", self.online_users)
        if self.new_chat_window:
            self.new_chat_window.destroy()
            self.new_chat_window = NewChatWindow(self, self.online_users, self.start_new_chat)

    def _on_new_chat_click(self):
        # Ask the server for the latest online list
        self.controller.network_client.send({"type": "whoisonline"})
        # The response will trigger update_online_list, which will then open the window
        # For immediate feedback, we can open it with the last known list
        if self.new_chat_window is None or not self.new_chat_window.winfo_exists():
             self.new_chat_window = NewChatWindow(self, self.online_users, self.start_new_chat)

    def start_new_chat(self, user: Dict):
        """Callback from NewChatWindow. Creates and opens a chat."""
        user_id = user.get('id')
        user_name = user.get('full_name')
        if not user_id or not user_name: return

        if user_id not in self.chats:
            self.chats[user_id] = {"name": user_name, "messages": []}
            self._populate_chat_list()
        
        self._open_chat(user_id)

    def _sample_chats(self):
        return {} # Start with no chats, they will be created dynamically
