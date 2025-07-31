import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

# 🔹 ADD DEAL COMMAND
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

    if len(context.args) < 1:
        await update.message.reply_text("❌ Usage: Reply to DEAL INFO message with /add <amount>")
        return

    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid amount!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to the DEAL INFO message with /add <amount>")
        return

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
        f"Escrowed by {escrower}\n"
    )

    await update.effective_chat.send_message(
        msg,
        reply_to_message_id=update.message.reply_to_message.message_id
    )

# 🔹 COMPLETE DEAL COMMAND
async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

    if len(context.args) < 1:
        await update.message.reply_text("❌ Usage: /complete <amount>")
        return

    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid amount!")
        return

    escrower = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown"

    msg = (
        f"✅ DEAL COMPLETED\n\n"
        f"💵 Released Amount: ₹{amount}\n"
        f"🤝 Escrowed By: {escrower}\n"
    )

    await update.effective_chat.send_message(msg)

# 🔹 MAIN FUNCTION
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    print("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
