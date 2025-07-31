import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "7607621887:AAGMXwj4mC5g3OsUo4p4xrxQKLKxVwnwZBM"

# Runtime stats storage
total_deals = 0
total_volume = 0
total_fee = 0.0
user_stats = {}  # {username: total_amount}

# ✅ Check if user is group admin
async def is_admin(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    try:
        member = await chat.get_member(user.id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# 🔹 ADD DEAL COMMAND
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global total_deals, total_volume, total_fee, user_stats

    if not await is_admin(update):
        username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        await update.message.reply_text(f"{username} Baag bhosadiya k")
        return

    # Sirf command message delete hoga
    try:
        await update.message.delete()
    except:
        pass

    if len(context.args) < 1:
        await update.effective_chat.send_message("❌ Usage: Reply to DEAL INFO message with /add <amount>")
        return

    try:
        amount = float(context.args[0])
    except:
        await update.effective_chat.send_message("❌ Invalid amount!")
        return

    if not update.message.reply_to_message:
        await update.effective_chat.send_message("❌ Please reply to the DEAL INFO message with /add <amount>")
        return

    fee = round(amount * 0.02, 2)
    release_amount = round(amount - fee, 2)
    trade_id = f"TID{random.randint(100000, 999999)}"
    escrower = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown"

    # Update global stats
    total_deals += 1
    total_volume += amount
    total_fee += fee

    # Update user stats
    user_key = escrower
    user_stats[user_key] = user_stats.get(user_key, 0) + amount

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
    if not await is_admin(update):
        username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        await update.message.reply_text(f"{username} Baag bhosadiya k")
        return

    # Sirf command delete hoga
    try:
        await update.message.delete()
    except:
        pass

    if len(context.args) < 1:
        await update.effective_chat.send_message("❌ Usage: /complete <amount>")
        return

    try:
        amount = float(context.args[0])
    except:
        await update.effective_chat.send_message("❌ Invalid amount!")
        return

    escrower = f"@{update.effective_user.username}" if update.effective_user.username else "Unknown"
    reply_id = update.message.reply_to_message.message_id if update.message.reply_to_message else None

    msg = (
        f"✅ DEAL COMPLETED\n\n"
        f"💵 Released Amount: ₹{amount}\n"
        f"🤝 Escrowed By: {escrower}\n"
    )

    await update.effective_chat.send_message(
        msg,
        reply_to_message_id=reply_id
    )

# 🔹 STATS COMMAND
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        await update.message.reply_text(f"{username} Baag bhosadiya k")
        return

    msg = (
        "📊 DEAL STATS\n\n"
        f"Total Deals: {total_deals}\n"
        f"Total Volume: ₹{total_volume}\n"
        f"Total Fee Collected: ₹{round(total_fee,2)}\n"
    )
    await update.message.reply_text(msg)

# 🔹 TOP USERS COMMAND
async def top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        await update.message.reply_text(f"{username} Baag bhosadiya k")
        return

    if not user_stats:
        await update.message.reply_text("❌ Abhi tak koi deal nahi hui.")
        return

    # Sort users by total volume
    sorted_users = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)
    top5 = sorted_users[:5]

    msg = "🏆 TOP USERS\n\n"
    for idx, (user, volume) in enumerate(top5, start=1):
        msg += f"{idx}. {user} - ₹{volume}\n"

    await update.message.reply_text(msg)

# 🔹 MAIN FUNCTION
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("complete", complete_deal))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("topusers", top_users))
    print("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
