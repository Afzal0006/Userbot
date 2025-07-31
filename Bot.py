import re
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Delete the command message
    try:
        await update.message.delete()
    except:
        pass

    # Check if amount provided
    if len(context.args) < 1:
        await update.message.reply_text("❌ Usage: Reply to DEAL INFO form with /add <amount>")
        return

    # Parse amount
    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid amount!")
        return

    # Must be reply to DEAL INFO message
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to the DEAL INFO message with /add <amount>")
        return

    form_text = update.message.reply_to_message.text

    # Extract Buyer & Seller from form
    buyer_match = re.search(r"BUYER\s*:\s*([^\n]+)", form_text, re.IGNORECASE)
    seller_match = re.search(r"SELLER\s*:\s*([^\n]+)", form_text, re.IGNORECASE)

    buyer = buyer_match.group(1).strip() if buyer_match else "Unknown"
    seller = seller_match.group(1).strip() if seller_match else "Unknown"

    # Calculate fee & release amount
    fee = round(amount * 0.02, 2)
    release_amount = round(amount - fee, 2)
    trade_id = f"TID{random.randint(100000, 999999)}"
    escrower = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown"

    # Final message
    msg = (
        "💰 INR Transactions\n\n"
        f"💵 Received Amount: ₹{amount}\n"
        f"💸 Release/Refund Amount: ₹{release_amount}\n"
        f"⚖️ Escrow Fee: ₹{fee}\n"
        f"🆔 Trade ID: #{trade_id}\n\n"
        f"_Escrowed by {escrower}_\n"
        f"👤 Buyer: {buyer}\n"
        f"👤 Seller: {seller}"
    )

    await update.effective_chat.send_message(msg)

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.run_polling()
