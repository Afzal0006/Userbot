import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pyrogram import Client as UserClient

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Credentials from ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")

# Pyrogram Userbot client
userbot = UserClient(
    name="userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION
)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Type /deal to create a private group.")

# Deal command
async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        async with userbot:
            # Create a private supergroup
            chat = await userbot.create_channel(f"Deal with {user.first_name}", is_supergroup=True)
            # Export invite link
            link = await userbot.export_chat_invite_link(chat.id)

        await update.message.reply_text(f"✅ New private group created!\nJoin here: {link}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        logger.error(e)

# Run bot
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("deal", deal))
    app.run_polling()
