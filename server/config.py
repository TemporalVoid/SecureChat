# server/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Define the base directory of the server component
SERVER_DIR = Path(__file__).parent.parent.resolve()

class Settings(BaseSettings):
    """
    Manages the server's configuration settings using pydantic-settings.
    It automatically reads values from environment variables or a .env file.
    """
    
    # This dictionary replaces the old inner 'Config' class.
    model_config = SettingsConfigDict(
        env_file="server.env", 
        env_file_encoding="utf-8"
    )

    # --- Network Settings ---
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8888

    # --- Database Settings ---
    # We construct a default path relative to this file's location.
    DATABASE_PATH: Path = SERVER_DIR / "chat_server.db"
    
    # --- Logging Settings ---
    LOG_LEVEL: str = "INFO"


# Create a single, globally accessible instance of the settings.
# Other modules will import this `settings` object.
settings = Settings()


# --- Self-testing / Demonstration block ---
def main_test():
    """
    Demonstrates how to access the configuration settings.
    """
    print("--- Running Updated Config Module Demonstration ---")
    print(f"Server Host: {settings.SERVER_HOST}")
    print(f"Server Port: {settings.SERVER_PORT}")
    print(f"Database Path: {settings.DATABASE_PATH}")
    print(f"Log Level: {settings.LOG_LEVEL}")

    # You can access attributes like a normal Python object
    assert isinstance(settings.SERVER_PORT, int)
    assert settings.DATABASE_PATH.name == "chat_server.db"
    
    print("\nConfiguration loaded and validated successfully!")
    print("--- Config Module Demonstration Finished ---")


if __name__ == "__main__":
    main_test()