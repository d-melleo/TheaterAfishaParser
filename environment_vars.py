from os import getenv

from dotenv import load_dotenv

# Load virtual environment
load_dotenv()

URL_AFISHA = getenv("URL_AFISHA")
BOT_TOKEN = getenv("BOT_TOKEN")  # Bot API Token
RECIPIENTS = getenv("RECIPIENTS")  # Telegram user IDs
RECIPIENTS = [chat_id.strip() for chat_id in RECIPIENTS.split(',')]