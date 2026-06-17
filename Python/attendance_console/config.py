# config.py
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_env_required(key):
    val = os.getenv(key)
    if not val:
        print(f"[ERROR] Required environment variable '{key}' is missing. Please check your .env file.")
        sys.exit(1)
    return val

# --------------------
# Database configuration
# --------------------
DB_CONFIG = {
    "dbname": get_env_required("DB_NAME"),
    "user": get_env_required("DB_USER"),
    "password": get_env_required("DB_PASSWORD"),
    "host": get_env_required("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
}

# Hikvision credentials
# --------------------
HIK_USERNAME = get_env_required("HIK_USERNAME")
HIK_PASSWORD = get_env_required("HIK_PASSWORD")

# --------------------
# Device URLs
# --------------------
# Parse comma-separated list of URLs from environment
device_urls_env = os.getenv("DEVICE_URLS")
if device_urls_env:
    DEVICE_URLS = [url.strip() for url in device_urls_env.split(",") if url.strip()]
else:
    print("[ERROR] Required environment variable 'DEVICE_URLS' is missing. Please check your .env file.")
    sys.exit(1)

# --------------------
# Full import start date
# --------------------
FULL_IMPORT_START_DATE = os.getenv("FULL_IMPORT_START_DATE", "2023-01-01")
