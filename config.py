import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID'))
GOOGLE_SHEETS_CRED_FILE = os.getenv('GOOGLE_SHEETS_CRED_FILE')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
CACHE_EXPIRY = int(os.getenv('CACHE_EXPIRY', 300))  # Default 5 minutes