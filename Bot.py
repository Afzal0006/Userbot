import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"
ESCROWER_USERNAME = "@YourEscrower"  # Apna escrower username daal do
FEE_PERCENT = 2  # 2% fee

# ---------- /add command ----------
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

    if len(context.args) < 1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Amount dena zaroori hai!\nExample: /add 500"
        )
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Amount number me do!\nExample: /add 500"
        )
        return

    fee = round(amount * FEE_PERCENT / 100, 2)

    # Buyer detection from reply
    if update.message.reply_to_message:
        buyer = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else "Unknown"
    else:
        buyer = "Buyer"

    seller = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown"
    trade_id = f"#TID{random.randint(100000, 999999)}"

    msg = (
        f"💰 DEAL INFO :\n"
        f"👤 BUYER : {buyer}\n"
        f"🛒 SELLER : {seller}\n"
        f"💵 DEAL AMOUNT : ₹{amount}\n"
        f"⚖️ Escrow Fee (2%) : ₹{fee}\n"
        f"🆔 Trade ID : {trade_id}\n"
        f"🤝 Escrowed By : {ESCROWER_USERNAME}"
    )

    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


# ---------- /complete command ----------
async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

    if len(context.args) < 1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Amount dena zaroori hai!\nExample: /complete 500"
        )
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Amount number me do!\nExample: /complete 500"
        )
        return

    fee = round(amount * FEE_PERCENT / 100, 2)
    released = round(amount - fee, 2)
    trade_id = f"#TID{random.randint(100000, 999999)}"

    msg = (
        f"✅ DEAL COMPLETED\n"
        f"💵 Released: ₹{released}\n"
        f"⚖️ Escrow Fee (2%) : ₹{fee}\n"
        f"🆔 Trade ID: {trade_id}\n"
        f"🤝 Escrowed By : {ESCROWER_USERNAME}"
    )

    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


# ---------- BOT RUN ----------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("add", add_deal))
app.add_handler(CommandHandler("complete", complete_deal))

print("🤖 Bot is running...")
app.run_polling()
