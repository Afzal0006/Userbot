import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

# Last deal data store
last_deal = {}

# /add command
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Delete /add command message
    try:
        await update.message.delete()
    except:
        pass

    # Check if amount is given
    if len(context.args) < 1:
        await update.message.reply_text("❌ Usage: Reply to DEAL INFO with /add <amount>")
        return

    # Convert to float
    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid amount!")
        return

    # Must reply to DEAL INFO
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to the DEAL INFO message with /add <amount>")
        return

    # Extract Buyer & Seller from DEAL INFO
    deal_text = update.message.reply_to_message.text
    lines = deal_text.splitlines()
    buyer = seller = None

    for line in lines:
        if line.strip().startswith("BUYER"):
            buyer = line.split(":", 1)[1].strip()
        elif line.strip().startswith("SELLER"):
            seller = line.split(":", 1)[1].strip()

    # Save deal data for /complete
    trade_id = f"TID{random.randint(100000, 999999)}"
    fee = round(amount * 0.02, 2)
    release_amount = round(amount - fee, 2)

    last_deal["buyer"] = buyer or "Unknown"
    last_deal["seller"] = seller or "Unknown"
    last_deal["amount"] = release_amount
    last_deal["trade_id"] = trade_id

    escrower = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown"

    # Final add message
    msg = (
        "💰 INR Transactions\n\n"
        f"💵 Received Amount: ₹{amount}\n"
        f"💸 Release/Refund Amount: ₹{release_amount}\n"
        f"⚖️ Escrow Fee: ₹{fee}\n"
        f"🆔 Trade ID: #{trade_id}\n\n"
        f"Escrowed by {escrower}\n"
    )

    await update.effective_chat.send_message(
        msg,
        reply_to_message_id=update.message.reply_to_message.message_id
    )

# /complete command
async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not last_deal:
        await update.message.reply_text("❌ No active deal found! Use /add first.")
        return

    buyer = last_deal["buyer"]
    seller = last_deal["seller"]
    amount = last_deal["amount"]
    trade_id = last_deal["trade_id"]
    escrower = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown"

    msg = (
        f"✅ Deal Completed\n"
        f"🆔 Trade ID: #{trade_id}\n"
        f"💸 Released: ₹{amount}\n"
        f"👤 Buyer: {buyer}\n"
        f"👤 Seller: {seller}\n\n"
        f"Escrowed by {escrower}"
    )

    await update.message.reply_text(msg)

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.run_polling()
