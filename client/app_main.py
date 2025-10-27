# client/app_main.py
import customtkinter as ctk
import queue
import ctypes
from typing import Type, Dict

from .state_manager import StateManager
from .network_client import NetworkClient

from .gui_windows.login_frame import LoginWindow
from .gui_windows.signup_frame import SignupWindow
from .gui_windows.main_chat_window import MainWindow

# Try to detect a CustomTkinter messagebox widget if available; fall back to tkinter.messagebox
try:
    CTK_MESSAGEBOX = getattr(ctk, "CTkMessagebox", None)
except Exception:
    CTK_MESSAGEBOX = None

import tkinter.messagebox as tk_mb  # fallback if CTk messagebox isn't available

myappid = u'mycompany.myproduct.subproduct.version'
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass


class App(ctk.CTk):
    PROCESS_INTERVAL_MS = 100

    def __init__(self):
        super().__init__()
        self.title("Secure Chat")
        self._configure_appearance()
        self._init_window_geometry()

        # core services and state
        self.gui_queue: "queue.Queue[dict]" = queue.Queue()
        self.state_manager = StateManager()
        self.network_client = NetworkClient(self.gui_queue)

        # frame registry
        self.frame_classes: Dict[str, Type[ctk.CTkFrame]] = {}
        self.frames: Dict[str, ctk.CTkFrame] = {}
        self.icons: Dict[str, str] = {}

        # runtime helpers
        self.pending_login: str | None = None
        self.pending_signup: str | None = None

        self._init_core()
        self._init_layout()
        self._register_default_frames()
        self.show_frame("LoginWindow")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(self.PROCESS_INTERVAL_MS, self.process_incoming)

    # Appearance
    def _configure_appearance(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    # Window geometry
    def _init_window_geometry(self):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(1280, screen_w)
        height = min(720, screen_h)
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        try:
            self.state("zoomed")
        except Exception:
            pass

    def _init_core(self):
        try:
            self.network_client.start()
        except Exception as e:
            print("Failed to start network client:", e)

    def _init_layout(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

    def register_frame(self, name: str, cls: Type[ctk.CTkFrame], icon_path: str | None = None):
        self.frame_classes[name] = cls
        if icon_path:
            self.icons[name] = icon_path

    def _register_default_frames(self):
        self.register_frame("LoginWindow", LoginWindow, icon_path="client/gui_windows/assets/frame0/key.ico")
        self.register_frame("SignupWindow", SignupWindow, icon_path="client/gui_windows/assets/frame0/compose.ico")
        self.register_frame("MainWindow", MainWindow, icon_path="client/gui_windows/assets/frame1/chat.ico")

    def show_frame(self, page_name: str):
        FrameClass = self.frame_classes.get(page_name)
        if not FrameClass:
            print(f"Error: Unknown frame '{page_name}'")
            return
        if page_name not in self.frames:
            frame = FrameClass(parent=self.container, controller=self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[page_name] = frame
        frame = self.frames[page_name]
        frame.tkraise()
        view_name = getattr(frame, "view_name", None)
        if view_name:
            self.title(view_name)
        if page_name in self.icons:
            try:
                self.iconbitmap(self.icons[page_name])
            except Exception:
                pass

    def _show_error_dialog(self, title: str, message: str):
        try:
            if CTK_MESSAGEBOX:
                CTK_MESSAGEBOX(title=title, message=message, icon="warning")
            else:
                tk_mb.showwarning(title, message)
        except Exception:
            print(f"{title}: {message}")

    def process_incoming(self):
        try:
            while not self.gui_queue.empty():
                msg = self.gui_queue.get_nowait()
                try:
                    self._handle_message(msg)
                except Exception as e:
                    print("Error handling incoming message:", e, "msg:", msg)
        finally:
            self.after(self.PROCESS_INTERVAL_MS, self.process_incoming)

    def _handle_message(self, message: dict):
        mtype = message.get("type")
        if mtype == "response":
            payload = message.get("payload", {}) or {}
            status = payload.get("status")

            if status == "ok" and "users" in payload:
                users = payload.get("users", [])
                main_win = self.frames.get("MainWindow")
                if main_win and hasattr(main_win, "update_online_list"):
                    main_win.update_online_list(users)
                return

            if status == "ok" and self.pending_signup:
                self.pending_signup = None
                self.show_frame("LoginWindow")
                return

            if status == "ok" and self.pending_login:
                user_info = payload.get("user_info")
                if user_info and 'id' in user_info and 'full_name' in user_info:
                    self.pending_login = None
                    self.state_manager.set_user(
                        user_id=user_info['id'],
                        full_name=user_info['full_name'],
                        email=user_info.get('email')
                    )
                    self.show_frame("MainWindow")
                else:
                    self._show_error_dialog("Login Error", "Server did not provide user information on login.")
                    self.pending_login = None # Clear pending flag on error
                return

            if status == "error":
                err = payload.get("message", "Server error")
                self._show_error_dialog("Request Failed", err)
                if self.pending_signup:
                    self.pending_signup = None
                if self.pending_login:
                    self.pending_login = None
                return

            print("Server response:", payload)
            return

        if mtype == "new_message":
            main_win = self.frames.get("MainWindow")
            if main_win and hasattr(main_win, "add_new_message"):
                main_win.add_new_message(message.get("payload"))
            return

        if mtype == "logout":
            self.state_manager.set_user(None, None, None)
            #self.show_frame("LoginWindow")
            self.destroy()
            return

        # --- MODIFIED SECTION: Robust Network Event Handling ---
        # If the network disconnects or an error occurs, send the user to the login screen.
        if mtype in ("network_disconnected", "network_error"):
            print("Network event:", message)
            # Only act if the user is currently logged in. No need to do anything if we're already on the login screen.
            if self.state_manager.get_user_id():
                self.state_manager.set_user(None, None, None) # Reset the user's state
                self.show_frame("LoginWindow")
                
                # Attempt to display an informative message on the login screen itself.
                login_frame = self.frames.get("LoginWindow")
                if login_frame and hasattr(login_frame, "show_error"):
                    error_payload = message.get('payload', 'Connection lost. Please log in again.')
                    login_frame.show_error(str(error_payload))
            return

        # Other informational network events that don't require action.
        if mtype in ("network_connected", "network_stopped"):
            print("Network event:", message)
            return
        # --- END OF MODIFIED SECTION ---

        print("Unhandled GUI message:", message)

    # --- MODIFIED SECTION: Clean Shutdown Process ---
    def on_closing(self):
        """
        This function is called when the user clicks the main window's 'X' button.
        """
        print("Application closing...")
        try:
            # 1. Attempt to send a logout message to the server. This is a "best effort" attempt.
            # If the network is already down, this will fail silently.
            if self.state_manager.get_user_id():
                 self.network_client.send({"type": "logout"})
        except Exception as e:
            print(f"Could not send logout message: {e}")
        
        # 2. Stop the network client thread to prevent reconnection attempts.
        self.network_client.stop()
        
        # 3. Destroy the main application window, which terminates the program.
        self.destroy()
    # --- END OF MODIFIED SECTION ---


if __name__ == "__main__":
    app = App()
    app.mainloop()

