import customtkinter as ctk
from PIL import Image
import tkinter.messagebox as mb
import pywinstyles


class SignupWindow(ctk.CTkFrame):
    WIDTH = 1920
    HEIGHT = 1017
    view_name = "Sign-Up Page"

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
        bg_widget = ctk.CTkLabel(self, image=self.background_image, text="")
        bg_widget.place(x=0, y=0, relwidth=1, relheight=1)

        # Signup frame — centered
        frame_w, frame_h = 450, 690
        self.signup_frame = ctk.CTkFrame(
            self, width=frame_w, height=frame_h,
            corner_radius=20, fg_color="#0C0E25", bg_color="#000001"
        )
        pywinstyles.set_opacity(self.signup_frame, color="#000001")
        self.signup_frame.place(relx=0.5, rely=0.5, anchor="center")

        self._build_signup_contents()
        self.bind("<Return>", lambda e: self._on_signup_click())

    def _build_signup_contents(self):
        padx = 60
        y = 40

        header = ctk.CTkLabel(self.signup_frame, text="Create Account",
                              font=ctk.CTkFont(size=32, weight="bold"))
        header.place(x=padx + 60, y=y)

        y += 100
        name_label = ctk.CTkLabel(self.signup_frame, text="Full Name",
                                  font=ctk.CTkFont(size=16, weight="bold"))
        name_label.place(x=padx, y=y)
        y += 30
        self.name_entry = ctk.CTkEntry(self.signup_frame, width=320, placeholder_text="John Doe")
        self.name_entry.place(x=padx, y=y)

        y += 60
        email_label = ctk.CTkLabel(self.signup_frame, text="Email",
                                   font=ctk.CTkFont(size=16, weight="bold"))
        email_label.place(x=padx, y=y)
        y += 30
        self.email_entry = ctk.CTkEntry(self.signup_frame, width=320, placeholder_text="name@example.com")
        self.email_entry.place(x=padx, y=y)

        y += 60
        pwd_label = ctk.CTkLabel(self.signup_frame, text="Password",
                                 font=ctk.CTkFont(size=16, weight="bold"))
        pwd_label.place(x=padx, y=y)
        y += 30
        self.password_entry = ctk.CTkEntry(self.signup_frame, width=320, show="●", placeholder_text="Enter password")
        self.password_entry.place(x=padx, y=y)

        y += 60
        confirm_label = ctk.CTkLabel(self.signup_frame, text="Confirm Password",
                                     font=ctk.CTkFont(size=16, weight="bold"))
        confirm_label.place(x=padx, y=y)
        y += 30
        self.confirm_entry = ctk.CTkEntry(self.signup_frame, width=320, show="●", placeholder_text="Re-enter password")
        self.confirm_entry.place(x=padx, y=y)

        y += 70
        signup_btn = ctk.CTkButton(self.signup_frame, text="Sign Up",
                                   font=ctk.CTkFont(weight="bold"),
                                   width=120, fg_color="#817CFC",
                                   command=self._on_signup_click)
        signup_btn.place(x=padx + 100, y=y)

        y += 60
        go_to_login_label = ctk.CTkLabel(self.signup_frame, text="Already have an account?")
        go_to_login_label.place(x=padx - 30, y=y)

        y += 30
        login_btn = ctk.CTkButton(self.signup_frame, text="Back to Login",
                                  font=ctk.CTkFont(weight="bold"),
                                  width=80, fg_color="#817CFC",
                                  command=lambda: self.controller.show_frame("LoginWindow"))
        login_btn.place(x=padx - 30, y=y)

        y += 60
        note_label = ctk.CTkLabel(
            self.signup_frame,
            text="By signing up, you agree to our Terms of Service and Privacy Policy.",
            font=ctk.CTkFont(size=10),
            wraplength=300,
            justify="center"
        )
        note_label.place(x=padx - 45, y=y)

    def _on_signup_click(self):
        # clear previous inline error
        try:
            self.error_label.configure(text="")
        except Exception:
            pass

        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip().lower()
        pwd = self.password_entry.get()
        confirm = self.confirm_entry.get()

        if not name or not email or not pwd or not confirm:
            mb.showwarning("Missing fields", "Please fill out all fields.")
            return

        if pwd != confirm:
            mb.showerror("Mismatch", "Passwords do not match.")
            return

        # basic email validation
        if "@" not in email or "." not in email.split("@")[-1]:
            mb.showerror("Invalid email", "Please enter a valid email address.")
            return

        # Correctly flag this as a pending signup attempt
        self.controller.pending_signup = email

        try:
            self.controller.network_client.send({
                "type": "signup",
                "payload": {"full_name": name, "email": email, "password": pwd}
            })
        except Exception as e:
            mb.showwarning("Error", f"Failed to send signup request: {e}")

    def show_error(self, message: str):
        """Placeholder for displaying inline error messages from the controller."""
        # The main controller (app_main) shows the popup warning.
        # This method could be expanded to show an error label within the frame.
        print(f"Signup Frame received error: {message}")
        pass
