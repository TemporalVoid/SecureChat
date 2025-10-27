# SecureChat 1.0

A secure, encrypted chat application built with Python featuring end-to-end encryption, user authentication, and a modern GUI interface.

## Features

- 🔐 End-to-end encryption using RSA and AES-256-GCM
- 👥 User authentication and registration
- 💬 Real-time messaging
- 📱 Modern dark-themed GUI built with CustomTkinter
- 🔄 Offline message support
- 👤 Online user status tracking
- 🗄️ Local message history storage

## Requirements

- Python 3.10+
- Required packages (see requirements.txt):
  - aiosqlite
  - bcrypt
  - cryptography
  - customtkinter
  - pydantic
  - python-dotenv
  - pywinstyles

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd secureChat_1.0
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Unix/MacOS:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the environment:
- Copy `.env.example` to create `server.env` and `client.env`
- Modify settings if needed (default values should work for local testing)

## Running the Application

1. Start the server:
```bash
# On Windows:
server_lunch.bat
# On Unix/MacOS:
python -m server.app
```

2. Start the client:
```bash
# On Windows:
client_lunch.bat
# On Unix/MacOS:
python -m client.app_main
```

## Architecture

### Server Components
- `server/app.py` - Main server application
- `server/auth.py` - User authentication handling
- `server/secure_channel.py` - Encryption implementation
- `server/router.py` - Message routing logic
- `server/registry.py` - Online user management

### Client Components
- `client/app_main.py` - Main client application
- `client/network_client.py` - Network communication
- `client/secure_channel.py` - Client-side encryption
- `client/gui_windows/` - GUI implementation

## Security Features

- AES-256-GCM encryption for all messages
- Secure key exchange using RSA-2048
- Password hashing using bcrypt
- Encrypted local storage for message history

## Development

### Project Structure
```
secureChat_1.0/
├── server/               # Server-side code
├── client/              # Client-side code
│   └── gui_windows/    # GUI components
├── .env.example        # Environment configuration template
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## License

[Your chosen license]

## Contributing

[Your contribution guidelines]
