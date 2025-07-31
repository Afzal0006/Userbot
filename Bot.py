import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

# Memory store for trades
trades = {}  # trade_id: {amount, buyer, seller, escrower}

# /add command
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Delete the command message
    try:
        await update.message.delete()
    except:
        pass

    # Validate amount
    if len(context.args) < 1:
        await update.message.reply_text("❌ Usage: Reply to DEAL INFO message with /add <amount>")
        return

    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid amount!")
        return

    # Must reply to a DEAL INFO message
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to the DEAL INFO message with /add <amount>")
        return

    # Extract Buyer & Seller from DEAL INFO
    deal_text = update.message.reply_to_message.text
    buyer = seller = "Unknown"

    for line in deal_text.splitlines():
        if "BUYER" in line.upper():
            buyer = line.split(":")[-1].strip()
        elif "SELLER" in line.upper():
            seller = line.split(":")[-1].strip()

    escrower = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown"

    # Fee & Release Calculation
    fee = round(amount * 0.02, 2)
    release_amount = round(amount - fee, 2)
    trade_id = f"TID{random.randint(100000, 999999)}"

    # Store trade info
    trades[trade_id] = {"amount": amount, "buyer": buyer, "seller": seller, "escrower": escrower}

    # Send Trade Message
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
    # Delete the command message
    try:
        await update.message.delete()
    except:
        pass

    # Validate amount
    if len(context.args) < 1:
        await update.message.reply_text("❌ Usage: Reply to the Trade Message with /complete <amount>")
        return

    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid amount!")
        return

    # Must reply to the Trade message
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to the Trade Message!")
        return

    # Extract Trade ID
    trade_message = update.message.reply_to_message.text
    trade_id = None
    for line in trade_message.splitlines():
        if "TID" in line:
            trade_id = line.split("#")[-1].strip()
            break

    if not trade_id or trade_id not in trades:
        await update.message.reply_text("❌ Trade ID not found in the replied message!")
        return

    # Get trade info
    buyer = trades[trade_id]["buyer"]
    seller = trades[trade_id]["seller"]
    escrower = trades[trade_id]["escrower"]

    # Complete Deal Message
    complete_msg = (
        "✅ DEAL COMPLETED\n\n"
        f"🆔 Trade ID: #{trade_id}\n"
        f"👤 Buyer: {buyer}\n"
        f"🏬 Seller: {seller}\n"
        f"💵 Released Amount: ₹{amount}\n\n"
        f"Escrowed by {escrower}"
    )

    await update.effective_chat.send_message(
        complete_msg,
        reply_to_message_id=update.message.reply_to_message.message_id
    )

# /cancel command
async def cancel_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Delete the command message
    try:
        await update.message.delete()
    except:
        pass

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to the Trade Message to cancel!")
        return

    reason = " ".join(context.args) if context.args else "No reason provided"

    # Extract Trade ID
    trade_message = update.message.reply_to_message.text
    trade_id = None
    for line in trade_message.splitlines():
        if "TID" in line:
            trade_id = line.split("#")[-1].strip()
            break

    if not trade_id or trade_id not in trades:
        await update.message.reply_text("❌ Trade ID not found in the replied message!")
        return

    buyer = trades[trade_id]["buyer"]
    seller = trades[trade_id]["seller"]
    escrower = trades[trade_id]["escrower"]

    cancel_msg = (
        "❌ DEAL CANCELLED\n\n"
        f"🆔 Trade ID: #{trade_id}\n"
        f"👤 Buyer: {buyer}\n"
        f"🏬 Seller: {seller}\n"
        f"⚠️ Reason: {reason}\n\n"
        f"Escrowed by {escrower}"
    )

    await update.effective_chat.send_message(
        cancel_msg,
        reply_to_message_id=update.message.reply_to_message.message_id
    )

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.add_handler(CommandHandler("cancel", cancel_deal))
    app.run_polling()
