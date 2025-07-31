from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import random

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

# Fixed buyer & seller
BUYER = "@adityahere31"
SELLER = "@Yupmpm"

# /add command
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Use: /add <amount>")
        return

    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("Amount number me likho!")
        return

    fee = round(amount * 0.05, 2)  # 5% fee
    release_amount = round(amount - fee, 2)
    trade_id = f"#TID{random.randint(100000,999999)}"

    message = (
        "💰 *P.A.G.A.L INR Transactions*\n\n"
        f"💵 *Received Amount*: ₹{amount}\n"
        f"💸 *Release/Refund Amount*: ₹{release_amount}\n"
        f"⚖️ *Escrow Fee*: ₹{fee}\n"
        f"🆔 *Trade ID*: {trade_id}\n\n"
        f"_Escrowed by DemoBot_"
    )

    await update.message.reply_text(message, parse_mode="Markdown")

# /complete command
async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Use: /complete <amount>")
        return

    amount = context.args[0]
    trade_id = f"#TID{random.randint(100000,999999)}"

    message = (
        "✅ *Deal Completed*\n"
        f"🆔 *Trade ID*: {trade_id}\n"
        f"💸 *Released*: ${amount}\n"
        f"👤 *Buyer*: {BUYER}\n"
        f"👤 *Seller*: {SELLER}"
    )

    await update.message.reply_text(message, parse_mode="Markdown")

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.run_polling()
