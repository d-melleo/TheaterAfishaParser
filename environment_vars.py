from os import getenv

from dotenv import load_dotenv

# Load virtual environment
load_dotenv()

BOT_TOKEN = getenv("BOT_TOKEN")  # Bot API Token
RECIPIENTS = getenv("RECIPIENTS")  # Telegram user IDs
URL_AFISHA = getenv("URL_AFISHA")