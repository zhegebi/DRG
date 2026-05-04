import os
from pathlib import Path
from string import ascii_letters, digits, punctuation

from dotenv import load_dotenv

"""
This file defines the configuration of whole DRG server.
"""

# Database configuration
DB_DIR = "./data"
DB_FILE = "main.db"

# Authentication configuration
AUTH_SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
AUTH_ALGORITHM = "HS256"
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES = 30
AUTH_REFRESH_TOKEN_EXPIRE_DAYS = 7

# username and password constraints
USERNAME_MIN_LENGTH = 1
USERNAME_MAX_LENGTH = 20
USERNAME_ALLOWED_CHARS = set(ascii_letters + digits + punctuation)
USERNAME_ALLOWED_UTF8 = True  # Whether to allow UTF characters in username
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 20
PASSWORD_ALLOWED_CHARS = set(ascii_letters + digits + punctuation)

# frontend assets configuration
FRONTEND_DIR = Path("./client/dist")
FRONTEND_ASSETS_DIR = FRONTEND_DIR / "assets"

# .env variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
