from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"

# Memory me last deal store karega per chat
last_deal = {}

# ---------- /add ----------
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Delete command
    if update.message:
        try:
            await update.message.delete()
        except:
            pass

    # Amount check
    if not context.args:
        await update.effective_chat.send_message("❌ Example: /add 500")
        return

    # Buyer = command dene wala
    buyer = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.mention_html()

    # Seller = reply user (agar reply nahi kiya to ❓)
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        seller = f"@{user.username}" if user.username else user.mention_html()
    else:
        seller = "❓ (reply karke seller tag karo)"

    # Store last deal
    last_deal[update.effective_chat.id] = {"buyer": buyer, "seller": seller}

    amount = context.args[0]
    msg = (
        f"💰 DEAL INFO :\n\n"
        f"BUYER : {buyer}\n"
        f"SELLER : {seller}\n"
        f"DEAL AMOUNT : ₹{amount}\n"
        f"🤝 Escrowed By: @{update.effective_user.username}"
    )
    await update.effective_chat.send_message(msg)


# ---------- /complete ----------
async def complete_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Delete command
    if update.message:
        try:
            await update.message.delete()
        except:
            pass

    if not context.args:
        await update.effective_chat.send_message("❌ Example: /complete 500")
        return

    deal = last_deal.get(update.effective_chat.id, None)
    if not deal:
        await update.effective_chat.send_message("❌ Pehle /add se deal start karo")
        return

    amount = context.args[0]
    buyer = deal["buyer"]
    seller = deal["seller"]

    msg = (
        f"✅ DEAL COMPLETED\n\n"
        f"BUYER : {buyer}\n"
        f"SELLER : {seller}\n"
        f"RELEASED : ₹{amount}\n"
        f"🤝 Escrowed By: @{update.effective_user.username}"
    )
    await update.effective_chat.send_message(msg)


# ---------- Run Bot ----------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("add", add_deal))
app.add_handler(CommandHandler("complete", complete_deal))

print("Bot Running...")
app.run_polling()
