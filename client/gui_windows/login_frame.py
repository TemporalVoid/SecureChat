# client/gui_windows/login_frame.py
import customtkinter as ctk
from PIL import Image
import tkinter.messagebox as mb
import pywinstyles


class LoginWindow(ctk.CTkFrame):
    WIDTH = 1920
    HEIGHT = 1017
    view_name = "Login Page"

    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Background image
        bg_pil_img = Image.open("client/gui_windows/assets/frame0/login_bg.png")
        self.background_image = ctk.CTkImage(
            light_image=bg_pil_img,
            dark_image=bg_pil_img,
            size=(self.WIDTH, self.HEIGHT)
        )
        bg_widget = ctk.CTkLabel(master=self, image=self.background_image, text="", bg_color="transparent")
        bg_widget.place(x=0, y=0, relwidth=1, relheight=1)

        # Login frame
        frame_w = 400
        frame_h = 500
        self.login_frame = ctk.CTkFrame(
            self,
            width=frame_w,
            height=frame_h,
            corner_radius=20,
            fg_color="#0C0E25",
            bg_color="#000001"
        )
        pywinstyles.set_opacity(self.login_frame, color="#000001")
        self.login_frame.place(relx=0.96, rely=0.5, anchor="e")

        self._build_login_contents()
        self.bind("<Return>", lambda e: self._on_login_click())

    def _build_login_contents(self):
        padx = 20

        header = ctk.CTkLabel(self.login_frame, text="Welcome back!",
                              font=ctk.CTkFont(size=36, weight="bold"))
        header.place(x=padx, y=40)

        email_label = ctk.CTkLabel(self.login_frame, text="Email",
                                   font=ctk.CTkFont(size=16, weight="bold"))
        email_label.place(x=padx, y=130)
        self.email_entry = ctk.CTkEntry(self.login_frame, width=320, placeholder_text="name@example.com")
        self.email_entry.place(x=padx, y=160)

        pwd_label = ctk.CTkLabel(self.login_frame, text="Password",
                                 font=ctk.CTkFont(size=16, weight="bold"))
        pwd_label.place(x=padx, y=210)
        self.password_entry = ctk.CTkEntry(self.login_frame, width=320, show="●", placeholder_text="Enter your password")
        self.password_entry.place(x=padx, y=240)
        
        # --- NEW WIDGET: Add a label to display inline error messages ---
        self.error_label = ctk.CTkLabel(self.login_frame, text="", text_color="red", wraplength=300)
        self.error_label.place(x=padx, y=340)
        # --- END OF NEW WIDGET ---

        login_btn = ctk.CTkButton(self.login_frame, text="Login", font=ctk.CTkFont(weight="bold"), width=120, fg_color="#817CFC", command=self._on_login_click)
        login_btn.place(x=padx + 100, y=290)

        new_label = ctk.CTkLabel(self.login_frame, text="New here?")
        new_label.place(x=padx, y=385)

        signup_btn = ctk.CTkButton(self.login_frame, text="Sign-up", font=ctk.CTkFont(weight="bold"), width=80, fg_color="#817CFC", command=lambda: self.controller.show_frame("SignupWindow"))
        signup_btn.place(x=padx, y=420)

    def _on_login_click(self):
        # Clear previous inline error message before a new attempt
        self.error_label.configure(text="")

        email = self.email_entry.get().strip().lower()
        pwd = self.password_entry.get()
        if not email or not pwd:
            self.show_error("Please enter email and password.")
            return
            
        self.controller.pending_login = email
        try:
            self.controller.network_client.send({
                "type": "login",
                "payload": {"email": email, "password": pwd}
            })
        except Exception as e:
            self.show_error(f"Failed to send login request: {e}")

    def show_error(self, message: str):
        """Surface server or local errors in the Login UI."""
        # Prefer displaying the error in the dedicated label.
        if self.error_label:
            self.error_label.configure(text=message)
        else: # Fallback to a messagebox if the label somehow doesn't exist.
            try:
                mb.showerror("Login error", message)
            except Exception:
                pass

