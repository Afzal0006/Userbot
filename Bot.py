from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import random

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

# Last deal storage
last_deal = {}

# Function to capture DEAL INFO form
async def deal_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.startswith("DEAL INFO"):
        try:
            lines = [line.strip() for line in text.splitlines() if ":" in line]

            buyer = lines[0].split(":", 1)[1].strip()
            seller = lines[1].split(":", 1)[1].strip()
            amount = lines[2].split(":", 1)[1].strip()
            time_to_complete = lines[3].split(":", 1)[1].strip() if len(lines) > 3 else "Unknown"

            trade_id = f"#TID{random.randint(100000,999999)}"

            last_deal["buyer"] = buyer
            last_deal["seller"] = seller
            last_deal["amount"] = amount
            last_deal["time"] = time_to_complete
            last_deal["trade_id"] = trade_id

            await update.message.reply_text(f"✅ Deal saved with Trade ID {trade_id}")

        except Exception as e:
            await update.message.reply_text("❌ Invalid DEAL INFO format!")

# /complete command
async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not last_deal:
        await update.message.reply_text("No deal info found! Send DEAL INFO first.")
        return

    buyer = last_deal["buyer"]
    seller = last_deal["seller"]
    amount = last_deal["amount"]
    trade_id = last_deal["trade_id"]

    message = (
        f"✅ Deal Completed\n"
        f"🆔 Trade ID: {trade_id}\n"
        f"💸 Released: ${amount}\n"
        f"👤 Buyer: {buyer}\n"
        f"👤 Seller: {seller}"
    )
    await update.message.reply_text(message)

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, deal_info_handler))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.run_polling()
