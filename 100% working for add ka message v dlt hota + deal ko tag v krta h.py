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
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "7607621887:AAGMXwj4mC5g3OsUo4p4xrxQKLKxVwnwZBM"

# Runtime stats storage
total_deals = 0
total_volume = 0
total_fee = 0.0
user_stats = {}       # Escrower stats
buyer_stats = {}      # Buyer stats
seller_stats = {}     # Seller stats

# ✅ Check if user is group admin
async def is_admin(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    try:
        member = await chat.get_member(user.id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# 🔹 Extract Buyer & Seller from reply message
def extract_buyer_seller(text: str):
    buyer = seller = None
    for line in text.splitlines():
        if line.upper().startswith("BUYER"):
            buyer = line.split(":", 1)[1].strip()
        elif line.upper().startswith("SELLER"):
            seller = line.split(":", 1)[1].strip()
    return buyer, seller

# 🔹 ADD DEAL COMMAND
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global total_deals, total_volume, total_fee, user_stats, buyer_stats, seller_stats

    if not await is_admin(update):
        username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        await update.message.reply_text(f"{username} Baag bhosadiya k")
        return

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

    # Update escrower stats
    user_stats[escrower] = user_stats.get(escrower, 0) + amount

    # Extract Buyer/Seller from replied message
    buyer, seller = extract_buyer_seller(update.message.reply_to_message.text or "")
    for user, stats_dict in [(buyer, buyer_stats), (seller, seller_stats)]:
        if user:
            stats_dict[user] = stats_dict.get(user, 0) + amount

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

# 🔹 TOP BUYERS
async def top_buyers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        await update.message.reply_text(f"{username} Baag bhosadiya k")
        return

    if not buyer_stats:
        await update.message.reply_text("❌ Abhi tak koi buyer deal nahi hui.")
        return

    sorted_users = sorted(buyer_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = "🏆 TOP BUYERS\n\n" + "\n".join(f"{idx+1}. {user} - ₹{volume}" for idx, (user, volume) in enumerate(sorted_users))
    await update.message.reply_text(msg)

# 🔹 TOP SELLERS
async def top_sellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        await update.message.reply_text(f"{username} Baag bhosadiya k")
        return

    if not seller_stats:
        await update.message.reply_text("❌ Abhi tak koi seller deal nahi hui.")
        return

    sorted_users = sorted(seller_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = "🏆 TOP SELLERS\n\n" + "\n".join(f"{idx+1}. {user} - ₹{volume}" for idx, (user, volume) in enumerate(sorted_users))
    await update.message.reply_text(msg)

# 🔹 MAIN FUNCTION
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CommandHandler("topbuyers", top_buyers))
    app.add_handler(CommandHandler("topsellers", top_sellers))
    print("Bot started... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
