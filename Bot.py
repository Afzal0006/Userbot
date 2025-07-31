from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import random

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check args
    if len(context.args) < 1:
        await update.message.reply_text("Use: /add <amount>")
        return

    # Parse amount
    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("Amount number me likho!")
        return

    # Fee & Release
    fee = round(amount * 0.05, 2)  # 5% fee
    release_amount = round(amount - fee, 2)
    trade_id = f"#TID{random.randint(100000,999999)}"

    # Escrower info
    escrower = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
    buyer_tag = f"[{update.effective_user.first_name}](tg://user?id={update.effective_user.id})"

    # Final message
    message = (
        f"{buyer_tag}\n\n"
        "💰 P.A.G.A.L INR Transactions\n\n"
        f"💵 Received Amount: ₹{amount}\n"
        f"💸 Release/Refund Amount: ₹{release_amount}\n"
        f"⚖️ Escrow Fee: ₹{fee}\n"
        f"🆔 Trade ID: {trade_id}\n\n"
        f"_Escrowed by {escrower}_"
    )

    # Delete the /add message
    try:
        await update.message.delete()
    except:
        pass

    # Send the deal info
    await update.message.chat.send_message(message, parse_mode="Markdown")

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.run_polling()
