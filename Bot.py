from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("❌ Usage: /complete <amount>")
        return

    amount = context.args[0]
    escrower = update.effective_user.username or update.effective_user.first_name

    msg = (
        f"✅ DEAL COMPLETED\n\n"
        f"💵 Released Amount: ₹{amount}\n"
        f"🤝 Escrowed By: @{escrower}"
    )

    # delete command message
    try:
        await update.message.delete()
    except:
        pass

    await update.effective_chat.send_message(msg)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("complete", complete_deal))
    print("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
