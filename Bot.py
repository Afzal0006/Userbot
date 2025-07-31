from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import random

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Use: /add <amount>")
        return

    # Amount validation
    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("Amount number me likho!")
        return

    # Fee calculation (5%)
    fee = round(amount * 0.05, 2)
    release_amount = round(amount - fee, 2)

    # Random trade ID
    trade_id = f"#TID{random.randint(100000,999999)}"

    # Escrower info
    user = update.effective_user
    escrower = f"@{user.username}" if user.username else user.first_name

    # Final message
    message = (
        "💰 *XD Transaction*\n\n"
        f"💵 *Received Amount*: ₹{amount}\n"
        f"💸 *Release/Refund Amount*: ₹{release_amount}\n"
        f"⚖️ *Escrow Fee*: ₹{fee}\n"
        f"🆔 *Trade ID*: {trade_id}\n\n"
        f"_Escrowed by {escrower}_"
    )

    await update.message.reply_text(message, parse_mode="Markdown")

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.run_polling()
