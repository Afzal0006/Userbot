import re
import os
import logging
import sys
import time
import secrets
import string
import io
import asyncio
import csv
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from typing import Dict, Any, Optional, Tuple, List
import html
import pandas as pd
import pytz
from openpyxl.utils import get_column_letter

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, PicklePersistence,
    ConversationHandler, CallbackQueryHandler
)
from telegram.error import BadRequest
from telegram.constants import ParseMode

# --- CONFIGURATION ---
TOKEN = "8284699769:AAFEX-SOVAi2YPEW0x_ymN99u8FchliXhik"  # IMPORTANT: REPLACE WITH YOUR BOT TOKEN
DB_FILE = "escrow_bot.dbbb"  # Database file name
OWNER_ID = 6249999953  # Replace with your Telegram User ID
DEVELOPER_ID = 7998795678  # Replace with the developer's Telegram User ID
ALLOWED_ADMIN_GROUPS = [-1002807741648]  # Replace with your group IDs
BLACKLIST_ADMIN_IDS = [230401283 , 8029087069 , 230401283] # Admins who can manage the blacklist besides owners

# --- LOGGING SETUP ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- BUTTONS & CONSTANTS ---
BTN_MY_HOLDING, BTN_MY_VOLUME, BTN_MY_PENDING, BTN_MY_FEES, BTN_BACK = "📊 My Holding", "📈 My Volume", "⏳ My Pending Deals", "💰 My Fees", "◀️ Back"
BTN_VOLUME_TODAY, BTN_VOLUME_WEEKLY, BTN_VOLUME_MONTHLY, BTN_VOLUME_ALL_TIME = "Today's Volume", "This Week's Volume", "This Month's Volume", "All-Time Volume"
BTN_FEES_TODAY, BTN_FEES_WEEKLY, BTN_FEES_MONTHLY, BTN_FEES_ALL_TIME = "Today's Fees", "This Week's Fees", "This Month's Fees", "All-Time Fees"
BTN_OWNER_LIST_USERS, BTN_OWNER_BACK_TO_LIST, BTN_OWNER_GLOBAL_STATS, BTN_OWNER_ALL_ADMIN_STATS, BTN_OWNER_EXPORT_EXCEL, BTN_OWNER_EXPORT_CSV, BTN_OWNER_BACK_TO_MAIN = "👥 List All Admins", "◀️ Back to User List", "🌐 Global Stats", "🏆 All Admin Stats", "💾 Export to Excel", "💾 Export to CSV", "◀️ Back to Main Panel"
BTN_OWNER_USD_DASHBOARD = "🏦 All Holdings"
BTN_PARTICIPANT_STATS, BTN_PARTICIPANT_HISTORY = "📊 My Stats", "📜 My Deal History"
BTN_BLACKLIST_MENU = "🚫 Blacklist Menu"
BTN_BLACKLIST_ADD, BTN_BLACKLIST_REMOVE, BTN_BLACKLIST_VIEW = "/blacklist <id/upi> [reason]", "/unblacklist <id/upi>", "/viewblacklist"
USER_BUTTON_PREFIX = "👤 "
DASH_ADMIN_PREFIX = "👤 "
DASH_DEAL_PREFIX = "🆔 "
BTN_DASH_BACK_TO_ADMINS = "◀️ Back to Admins"
BTN_DASH_BACK_TO_DEALS = "◀️ Back to Deals"
BTN_DASH_FORCE_RELEASE = "🚨 Force Release"

# --- CONVERSATION STATES for /add command ---
SELECTING_FEE = 1

# --- KEYBOARDS ---
ADMIN_KEYBOARD = ReplyKeyboardMarkup([[KeyboardButton(BTN_MY_HOLDING), KeyboardButton(BTN_MY_VOLUME)], [KeyboardButton(BTN_MY_PENDING), KeyboardButton(BTN_MY_FEES)]], resize_keyboard=True)
PARTICIPANT_KEYBOARD = ReplyKeyboardMarkup([[KeyboardButton(BTN_PARTICIPANT_STATS)], [KeyboardButton(BTN_PARTICIPANT_HISTORY)]], resize_keyboard=True)
OWNER_VIEWING_KEYBOARD = ReplyKeyboardMarkup([[KeyboardButton(BTN_MY_HOLDING), KeyboardButton(BTN_MY_VOLUME)], [KeyboardButton(BTN_MY_PENDING), KeyboardButton(BTN_MY_FEES)], [KeyboardButton(BTN_OWNER_BACK_TO_LIST)]], resize_keyboard=True)
PRIVILEGED_MAIN_KEYBOARD = ReplyKeyboardMarkup([[KeyboardButton(BTN_OWNER_LIST_USERS), KeyboardButton(BTN_OWNER_GLOBAL_STATS)], [KeyboardButton(BTN_OWNER_ALL_ADMIN_STATS), KeyboardButton(BTN_OWNER_USD_DASHBOARD)], [KeyboardButton(BTN_OWNER_EXPORT_EXCEL), KeyboardButton(BTN_OWNER_EXPORT_CSV)], [KeyboardButton(BTN_BLACKLIST_MENU)]], resize_keyboard=True)
BLACKLIST_KEYBOARD = ReplyKeyboardMarkup([[KeyboardButton(BTN_BLACKLIST_ADD)], [KeyboardButton(BTN_BLACKLIST_REMOVE)], [KeyboardButton(BTN_BLACKLIST_VIEW)], [KeyboardButton(BTN_OWNER_BACK_TO_MAIN)]], resize_keyboard=True)

# --- USER GROUPS ---
PRIVILEGED_USERS = [OWNER_ID, DEVELOPER_ID]
BLACKLIST_MANAGERS = list(set(PRIVILEGED_USERS + BLACKLIST_ADMIN_IDS))

# --- HELPER FUNCTIONS ---
def parse_shorthand_amount(amount_str: str) -> float:
    if not isinstance(amount_str, str): raise ValueError("Input must be a string.")
    clean_str = str(amount_str).strip().lower()
    clean_str = re.sub(r'[^\d.k]', '', clean_str)
    if not clean_str: raise ValueError(f"Invalid number format: {amount_str}")
    if clean_str.endswith('k'):
        numeric_part = clean_str[:-1]
        if not numeric_part: raise ValueError("Invalid format: 'k' without a number.")
        try: return float(numeric_part) * 1000.0
        except ValueError: raise ValueError(f"Invalid number format with 'k': {amount_str}")
    else:
        try: return float(clean_str)
        except ValueError: raise ValueError(f"Invalid number format: {amount_str}")

async def safe_reply_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs):
    if not update.message: return
    try: await update.message.reply_text(text, **kwargs)
    except BadRequest as e:
        if "Message to be replied not found" in str(e):
            logger.warning(f"Failed to reply to a message (likely deleted). Sending directly to chat {update.effective_chat.id}.")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, **kwargs)
        else: logger.error(f"A BadRequest error occurred during reply: {e}"); raise

def get_transactions(context: ContextTypes.DEFAULT_TYPE) -> dict: return context.bot_data.setdefault("transactions", {})
def get_users(context: ContextTypes.DEFAULT_TYPE) -> dict: return context.bot_data.setdefault("users", {})
def get_blacklist(context: ContextTypes.DEFAULT_TYPE) -> dict: return context.bot_data.setdefault("blacklist", {})
def get_manual_admins(context: ContextTypes.DEFAULT_TYPE) -> set: return context.bot_data.setdefault("manual_admins", set())
def get_processed_message_ids(context: ContextTypes.DEFAULT_TYPE) -> list: return context.bot_data.setdefault("processed_message_ids", [])

def escape_markdown_v1(text: str) -> str:
    if not isinstance(text, str): return ""
    escape_chars = r'_*`['
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def is_crypto_address(item: str) -> bool:
    btc_pattern = r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$'
    eth_pattern = r'^0x[a-fA-F0-9]{40}$'
    tron_pattern = r'^T[A-Za-z1-9]{33}$'
    if re.match(btc_pattern, item) or re.match(eth_pattern, item) or re.match(tron_pattern, item):
        return True
    return False

def is_user_an_escrower(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return any(t.get('user_id') == user_id for t in get_transactions(context).values())
async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id; chat_id = update.effective_chat.id
    cache_key = f"admin_cache_{chat_id}"; cached_data = context.bot_data.get(cache_key, (None, 0))
    if time.time() - cached_data[1] < 60: return user_id in cached_data[0]
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = {admin.user.id for admin in admins}
        context.bot_data[cache_key] = (admin_ids, time.time()); return user_id in admin_ids
    except Exception: return False

async def is_main_group_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not ALLOWED_ADMIN_GROUPS: return False
    for group_id in ALLOWED_ADMIN_GROUPS:
        try:
            admins = await context.bot.get_chat_administrators(group_id)
            if user_id in {admin.user.id for admin in admins}: return True
        except Exception as e: logger.warning(f"Could not check admin status for group {group_id}: {e}"); continue
    return False

async def is_authorized_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id in get_manual_admins(context): return True
    return await is_main_group_admin(user_id, context)

# Decorators
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not await is_group_admin(update, context):
            try: await safe_reply_text(update, context, "This command can only be used by group admins.")
            except AttributeError: await update.callback_query.answer("This action is for admins only.", show_alert=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper
def privileged_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id not in PRIVILEGED_USERS:
            await safe_reply_text(update, context, "⛔️ Access Denied.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper
def blacklist_manager_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id not in BLACKLIST_MANAGERS:
            await safe_reply_text(update, context, "⛔️ You do not have permission to manage the blacklist.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# --- CORE LOGIC FUNCTIONS ---
def register_user(source: Update | CallbackQuery | User, context: ContextTypes.DEFAULT_TYPE):
    user = None
    if isinstance(source, User): user = source
    else: user = getattr(source, 'from_user', None) or getattr(source, 'effective_user', None)
    if user and str(user.id) not in get_users(context):
        get_users(context)[str(user.id)] = {'first_name': user.first_name, 'username': user.username}
def generate_trade_id(): return '#TID' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))
def get_time_range(period: str) -> tuple[datetime, datetime]:
    now_utc = datetime.now(pytz.utc)
    if period == "today": return now_utc.replace(hour=0, minute=0, second=0, microsecond=0), now_utc
    if period == "weekly": return (now_utc - timedelta(days=now_utc.weekday())).replace(hour=0, minute=0, second=0, microsecond=0), now_utc
    if period == "monthly": return now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now_utc
    return datetime.min.replace(tzinfo=pytz.utc), now_utc
def _get_holding_text(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    transactions = get_transactions(context).values()
    total_holding = sum((t['received_amount'] - t['fee'] - t['amount_released']) for t in transactions if t.get('user_id') == user_id and t.get('status') == 'holding')
    return f"📊 Total Holding\n\nThis user is currently holding ${total_holding:,.2f} in active escrow deals."
def _get_pending_text(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    all_transactions = get_transactions(context).values()
    pending_deals = [t for t in all_transactions if t.get('user_id') == user_id and t.get('status') == 'holding']
    if not pending_deals: return "✅ This user has no pending deals."
    text = f"⏳ Pending Deals ({len(pending_deals)})\n"
    for deal in sorted(pending_deals, key=lambda d: d['received_date']):
        remaining = (deal['received_amount'] - deal['fee']) - deal['amount_released']
        text += f"\n- ID: {deal['trade_id']}\n  Holding: ${remaining:,.2f}"
    return text
def get_stats_text(user_id: int, context: ContextTypes.DEFAULT_TYPE, stat_type: str, period: str) -> str:
    start_date, end_date = get_time_range(period)
    transactions = [t for t in get_transactions(context).values() if t.get('user_id') == user_id]
    total = 0
    for t in transactions:
        received_date_str = t.get('received_date')
        if received_date_str:
            received_date = datetime.fromisoformat(received_date_str)
            if start_date <= received_date <= end_date:
                if stat_type == 'received_amount':
                    total += t.get('deal_amount', t.get('received_amount', 0))
                else: total += t.get(stat_type, 0)
    title_period = period.replace("_", " ").title()
    title_stat = "Volume" if stat_type == "received_amount" else "Fees"
    icon = "📈" if stat_type == "received_amount" else "💰"
    return f"{icon} Total {title_stat} ({title_period})\n\nThis user's total {title_stat.lower()} (based on created deals) is ${total:,.2f}."
def _get_global_stats_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    HISTORICAL_VOLUME = 1281677.856462921
    HISTORICAL_DEAL_COUNT = 7093
    all_deals = list(get_transactions(context).values())
    bot_total_volume = sum(t.get('deal_amount', t.get('received_amount', 0)) for t in all_deals)
    bot_deal_count = len(all_deals)
    start_today_utc, _ = get_time_range("today")
    todays_volume = sum(t.get('deal_amount', t.get('received_amount', 0)) for t in all_deals if t.get('received_date') and datetime.fromisoformat(t['received_date']) >= start_today_utc)
    final_total_volume = HISTORICAL_VOLUME + bot_total_volume
    final_deal_count = HISTORICAL_DEAL_COUNT + bot_deal_count
    return (f"📊 (CRYPTO) Escrow Stats of P.A.G.A.L Escrow\n\n"
            f"💰 Total Escrowed Amount: \n{final_total_volume:,.2f}$\n\n"
            f"📅 Today's Escrowed Amount: {todays_volume:,.2f}$\n\n"
            f"🔢 Total Escrows Done Till Now: {final_deal_count}\n\n"
            f"📊 Always use @Escrow_Pagal for safer transactions!\n"
            f"📊 Data Recorded from 19 March 2025")
def _get_participant_stats_text(target_user: User, context: ContextTypes.DEFAULT_TYPE) -> str:
    username = target_user.username
    if not username:
        return (f"📊 Participant Stats for {target_user.first_name}\n\n"
                f"This user needs to set a public @username in their Telegram settings to view full stats.")

    all_transactions = get_transactions(context).values()
    participant_volumes = defaultdict(float)
    for t in all_transactions:
        deal_amt = t.get('deal_amount', t.get('received_amount', 0))
        if buyer := t.get('buyer_username'): participant_volumes[buyer.lower()] += deal_amt
        if seller := t.get('seller_username'): participant_volumes[seller.lower()] += deal_amt

    sorted_participants = sorted(participant_volumes.items(), key=lambda item: item[1], reverse=True)
    user_rank = "Unranked"
    username_lower = username.lower()
    for i, (p_user, p_vol) in enumerate(sorted_participants):
        if p_user == username_lower: user_rank = f"#{i + 1}"; break

    user_deals = [t for t in all_transactions if username_lower in ((t.get('buyer_username') or '').lower(), (t.get('seller_username') or '').lower())]
    if not user_deals: return f"@{username} have not done any deal in Crypto"

    p_volume = sum(t.get('deal_amount', t.get('received_amount', 0)) for t in user_deals)
    total_deals = len(user_deals)
    ongoing_deals = sum(1 for t in user_deals if t.get('status') == 'holding')
    highest_deal = max((t.get('deal_amount', t.get('received_amount', 0)) for t in user_deals), default=0.0)

    return (f"📊 Participant Stats for @{username} (CRYPTO)\n\n"
            f"👑 Ranking: {user_rank}\n"
            f"📈 Total Volume: $ {p_volume:,.2f}\n"
            f"🔢 Total Deals: {total_deals}\n"
            f"🕜 Ongoing Deals: {ongoing_deals}\n"
            f"⚡️ Highest Deal - $ {highest_deal:,.2f}\n\n"
            f"📊 Always use @Escrow_Pagal for safer transactions!")

def clear_dashboard_state(context: ContextTypes.DEFAULT_TYPE):
    """Clears all session-specific dashboard/viewing states."""
    context.user_data.pop('dashboard_level', None)
    context.user_data.pop('dashboard_admin_id', None)
    context.user_data.pop('dashboard_trade_id', None)
    context.user_data.pop('viewing_user_id', None)
    context.user_data.pop('viewing_participant_username', None)

# --- COMMAND HANDLERS ---
@privileged_only
async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_dashboard_state(context)
    await update.message.reply_text("Welcome, Owner/Developer.", reply_markup=PRIVILEGED_MAIN_KEYBOARD)

@privileged_only
async def view_as_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows a privileged user to view the bot as if they were a regular participant."""
    if not context.args:
        await safe_reply_text(update, context, "Usage: /viewas @username\nThis allows you to see the panel for any user, even if they haven't started the bot.")
        return

    clear_dashboard_state(context)
    target_identifier = context.args[0]
    
    if not target_identifier.startswith('@'):
        await safe_reply_text(update, context, "Invalid format. Please provide an @username to view their participant panel.")
        return

    target_username = target_identifier.lstrip('@').lower()
    
    has_deals = any(
        target_username == (t.get('buyer_username') or '').lower() or 
        target_username == (t.get('seller_username') or '').lower()
        for t in get_transactions(context).values()
    )

    if not has_deals:
        await safe_reply_text(update, context, f"No deals found for user @{target_username} in the database.")
        return

    context.user_data['viewing_participant_username'] = target_username
    await update.message.reply_text(
        f"👁️ You are now viewing the bot as @{target_username}.\n\n"
        f"You can now use their participant panel. Use /panel to return to your admin view.",
        reply_markup=PARTICIPANT_KEYBOARD
    )

async def owner_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_users = get_users(context)
    other_users = {uid: udata for uid, udata in all_users.items() if int(uid) not in PRIVILEGED_USERS and is_user_an_escrower(int(uid), context)}
    if not other_users: await update.message.reply_text("No admins have interacted with the bot yet.", reply_markup=PRIVILEGED_MAIN_KEYBOARD); return
    user_buttons = [[KeyboardButton(f"{USER_BUTTON_PREFIX}{udata.get('first_name', uid)} ({uid})")] for uid, udata in other_users.items()]
    user_buttons.append([KeyboardButton(BTN_OWNER_BACK_TO_MAIN)])
    await update.message.reply_text("Select an admin to view their dashboard:", reply_markup=ReplyKeyboardMarkup(user_buttons, resize_keyboard=True))

@privileged_only
async def owner_export_data_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transactions = get_transactions(context)
    if not transactions: await safe_reply_text(update, context, "There are no transactions to export yet."); return
    await safe_reply_text(update, context, "Generating Excel report... this may take a moment.")
    try:
        users = get_users(context); IST = pytz.timezone('Asia/Kolkata'); export_data = []
        s_no = 1; total_volume, total_fees, completed_deals, pending_deals = 0, 0, 0, 0
        sorted_txs = sorted(
            transactions.values(), 
            key=lambda x: x.get('received_date') or datetime.min.isoformat()
        )
        for tx in sorted_txs:
            deal_amount = tx.get('deal_amount', tx.get('received_amount', 0)); received_amount, fee = tx.get('received_amount', 0), tx.get('fee', 0)
            if tx.get('status') == 'completed': total_volume += deal_amount; total_fees += fee; completed_deals += 1
            else: pending_deals += 1
            admin_info = users.get(str(tx.get('user_id')), {}); 
            created_utc = datetime.fromisoformat(tx['received_date']) if tx.get('received_date') else None; 
            completed_utc = datetime.fromisoformat(tx['completed_date']) if tx.get('completed_date') else None; 
            created_ist = created_utc.astimezone(IST) if created_utc else None; 
            completed_ist = completed_utc.astimezone(IST) if completed_utc else None
            row = {'S.No.': s_no, 'Date (IST)': created_ist.strftime('%d-%m-%Y') if created_ist else 'N/A', 'Time (IST)': created_ist.strftime('%I:%M:%S %p') if created_ist else 'N/A', 'Admin Name': admin_info.get('first_name', f"ID: {tx.get('user_id')}"), 'Deal Amount ($)': deal_amount, 'Received Amount ($)': received_amount, 'Fee ($)': fee, 'Amount Released ($)': tx.get('amount_released', 0), 'Amount Remaining ($)': (received_amount - fee) - tx.get('amount_released', 0), 'Status': tx.get('status', 'N/A').capitalize(), 'Buyer': f"@{tx.get('buyer_username')}" if tx.get('buyer_username') else 'N/A', 'Seller': f"@{tx.get('seller_username')}" if tx.get('seller_username') else 'N/A', 'Trade ID': tx.get('trade_id'), 'Completed Date (IST)': completed_ist.strftime('%d-%m-%Y') if completed_ist else 'N/A', 'Completed Time (IST)': completed_ist.strftime('%I:%M:%S %p') if completed_ist else 'N/A',}
            export_data.append(row); s_no += 1
        df = pd.DataFrame(export_data); summary_data = {'Metric': ['Total Volume (Completed Deals)', 'Total Fees Collected', 'Completed Deals', 'Pending Deals'], 'Value': [f"${total_volume:,.2f}", f"${total_fees:,.2f}", completed_deals, pending_deals]}; summary_df = pd.DataFrame(summary_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False); df.to_excel(writer, sheet_name='All Transactions', index=False)
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for i, col in enumerate(worksheet.columns):
                    max_length = max(len(str(cell.value)) for cell in col if cell.value); worksheet.column_dimensions[get_column_letter(i + 1)].width = max_length + 2
        output.seek(0); filename = f"escrow-report-{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        await update.message.reply_document(document=output, filename=filename, caption="Here is your professional data report.")
    except Exception as e: logger.error(f"Failed to export Excel data: {e}", exc_info=True); await safe_reply_text(update, context, f"An error occurred during Excel export: {e}")

@privileged_only
async def owner_export_data_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transactions = get_transactions(context)
    if not transactions: await safe_reply_text(update, context, "There are no transactions to export yet."); return
    await safe_reply_text(update, context, "Generating CSV export...")
    try:
        users = get_users(context); IST = pytz.timezone('Asia/Kolkata'); export_data = []
        sorted_txs = sorted(
            transactions.values(), 
            key=lambda x: x.get('received_date') or datetime.min.isoformat()
        )
        for tx in sorted_txs:
            admin_info = users.get(str(tx.get('user_id')), {}); 
            created_utc = datetime.fromisoformat(tx['received_date']) if tx.get('received_date') else None; 
            completed_utc = datetime.fromisoformat(tx['completed_date']) if tx.get('completed_date') else None; 
            created_ist = created_utc.astimezone(IST) if created_utc else None; 
            completed_ist = completed_utc.astimezone(IST) if completed_utc else None
            row = {'Trade ID': tx.get('trade_id'), 'Status': tx.get('status', 'N/A').capitalize(), 'Admin Name': admin_info.get('first_name', f"ID: {tx.get('user_id')}"), 'Buyer': f"@{tx.get('buyer_username')}" if tx.get('buyer_username') else 'N/A', 'Seller': f"@{tx.get('seller_username')}" if tx.get('seller_username') else 'N/A', 'Deal Amount ($)': tx.get('deal_amount', tx.get('received_amount', 0)), 'Received Amount ($)': tx.get('received_amount', 0), 'Fee ($)': tx.get('fee', 0), 'Amount Released ($)': tx.get('amount_released', 0), 'Received Date (IST)': created_ist.strftime('%Y-%m-%d') if created_ist else 'N/A', 'Received Time (IST)': created_ist.strftime('%H:%M:%S') if created_ist else 'N/A', 'Completed Date (IST)': completed_ist.strftime('%Y-%m-%d') if completed_ist else 'N/A', 'Completed Time (IST)': completed_ist.strftime('%H:%M:%S') if completed_ist else 'N/A',}
            export_data.append(row)
        if not export_data: await safe_reply_text(update, context, "No data available to export."); return
        output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=export_data[0].keys()); writer.writeheader(); writer.writerows(export_data)
        csv_bytes = io.BytesIO(output.getvalue().encode('utf-8')); csv_bytes.seek(0); filename = f"escrow-export-{datetime.now().strftime('%Y-%m-%d')}.csv"
        await update.message.reply_document(document=csv_bytes, filename=filename, caption="Here is your CSV data export.")
    except Exception as e: logger.error(f"Failed to export CSV data: {e}", exc_info=True); await safe_reply_text(update, context, f"An error occurred during CSV export: {e}")

async def owner_all_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transactions, users = get_transactions(context).values(), get_users(context); admin_stats = defaultdict(lambda: {'volume': 0, 'fees': 0, 'count': 0})
    for t in transactions:
        if t.get('status') == 'completed': admin_id = str(t['user_id']); admin_stats[admin_id]['volume'] += t.get('deal_amount', t.get('received_amount', 0)); admin_stats[admin_id]['fees'] += t['fee']; admin_stats[admin_id]['count'] += 1
    if not admin_stats: await safe_reply_text(update, context, "No completed deals found to generate admin stats."); return
    sorted_admins = sorted(admin_stats.items(), key=lambda item: item[1]['volume'], reverse=True)
    text = "🏆 All-Time Admin Leaderboard (Completed Deals)\n"
    for admin_id, stats in sorted_admins: name = users.get(admin_id, {}).get('first_name', f"ID {admin_id}"); text += f"\n- {name}:\n  📈 Vol: ${stats['volume']:,.2f} | 💰 Fees: ${stats['fees']:,.2f} | 🔢 Deals: {stats['count']}"
    await update.message.reply_text(text)

async def show_participant_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows stats for the participant being viewed (if in view mode) or the current user."""
    viewing_username = context.user_data.get('viewing_participant_username')
    
    if viewing_username:
        target_user = User(id=0, first_name=f"@{viewing_username}", is_bot=False, username=viewing_username)
    else:
        target_user = update.effective_user
        register_user(target_user, context)

    text = _get_participant_stats_text(target_user, context)
    await update.message.reply_text(text)

# --- MODIFIED: Redesigned function for a professional history view with message chunking ---
async def show_participant_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows a professionally formatted history for the user, splitting it into multiple messages if too long."""
    viewing_username = context.user_data.get('viewing_participant_username')
    IST = pytz.timezone('Asia/Kolkata')
    TELEGRAM_MSG_LIMIT = 4000  # A safe buffer below the 4096 limit

    if viewing_username:
        username_to_check = viewing_username
        header = f"<b>📜 Deal History for @{html.escape(username_to_check)}</b>"
    else:
        user = update.effective_user
        username_to_check = user.username
        if not username_to_check:
            await safe_reply_text(update, context, "Please set a Telegram username to view your deal history.")
            return
        header = "<b>📜 Your Deal History</b>"

    username_lower = username_to_check.lower()
    deals = [t for t in get_transactions(context).values() if username_lower in ((t.get('buyer_username') or '').lower(), (t.get('seller_username') or '').lower())]
    if not deals:
        await safe_reply_text(update, context, f"No deals found for user @{html.escape(username_to_check)}.")
        return

    # Sort deals safely
    sorted_deals = sorted(
        deals, 
        key=lambda d: d.get('completed_date', d.get('received_date')) or datetime.min.isoformat(), 
        reverse=True
    )
    
    message_chunks = []
    current_chunk = header

    for deal in sorted_deals:
        deal_details_list = []
        
        # --- Role, Other Party, and Escrower ---
        role = "Buyer" if (deal.get('buyer_username') or '').lower() == username_lower else "Seller"
        other_party_username = deal.get('seller_username' if role == "Buyer" else 'buyer_username', 'N/A')
        escrower_username = deal.get('escrowed_by_username', 'N/A')

        # --- Deal Amount ---
        deal_amt = deal.get('deal_amount', deal.get('received_amount', 0))

        # --- Status ---
        status = deal.get('status', 'holding').capitalize()
        status_line = f"{status}"
        if status == 'Completed': status_line += " ✅"

        # --- Timestamps ---
        start_date_ist_str = "N/A"
        if start_date_str := deal.get('received_date'):
            start_date_ist = datetime.fromisoformat(start_date_str).astimezone(IST)
            start_date_ist_str = start_date_ist.strftime('%d %b %Y, %I:%M %p')
            
        end_date_ist_str = ""
        if status == 'Completed' and (end_date_str := deal.get('completed_date')):
            end_date_ist = datetime.fromisoformat(end_date_str).astimezone(IST)
            end_date_ist_str = f"\n<b>Completed:</b> {end_date_ist.strftime('%d %b %Y, %I:%M %p')}"
        
        # Assemble the formatted block for this deal
        deal_block = (
            f"\n\n-------------------------\n"
            f"<b>Trade ID:</b> <code>{html.escape(deal['trade_id'])}</code>\n"
            f"<b>Your Role:</b> {role}\n"
            f"<b>Other Party:</b> @{html.escape(other_party_username)}\n"
            f"<b>Escrower:</b> {html.escape(escrower_username)}\n"
            f"<b>Amount:</b> <code>${deal_amt:,.2f}</code>\n"
            f"<b>Status:</b> {status_line}\n"
            f"<b>Created:</b> {start_date_ist_str}"
            f"{end_date_ist_str}"
        )

        # Check if adding the next block would exceed the limit
        if len(current_chunk) + len(deal_block) > TELEGRAM_MSG_LIMIT:
            message_chunks.append(current_chunk) # Store the completed chunk
            current_chunk = "" # Start a new chunk

        current_chunk += deal_block

    # Add the last remaining chunk
    if current_chunk:
        message_chunks.append(current_chunk)
    
    # Send all the chunks
    for i, chunk in enumerate(message_chunks):
        # Add a page number if there are multiple chunks
        if len(message_chunks) > 1:
            chunk += f"\n\n<i>Page {i+1} of {len(message_chunks)}</i>"
        await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)


@blacklist_manager_only
async def blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 1: await safe_reply_text(update, context, "Usage: /blacklist <id/upi/address> [reason]\nExample: /blacklist scammer@ybl Scammer UPI"); return
    item_to_blacklist = context.args[0]; reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided."; blacklist = get_blacklist(context)
    if item_to_blacklist in blacklist: await safe_reply_text(update, context, f"Identifier `{item_to_blacklist}` is already on the blacklist.", parse_mode=ParseMode.MARKDOWN); return
    blacklist[item_to_blacklist] = {"reason": reason, "added_by": update.effective_user.id, "date_added": datetime.now(pytz.utc).isoformat()}
    await safe_reply_text(update, context, f"✅ Identifier `{item_to_blacklist}` has been blacklisted.", parse_mode=ParseMode.MARKDOWN)

@blacklist_manager_only
async def unblacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: await safe_reply_text(update, context, "Usage: /unblacklist <id/upi/address>"); return
    item_to_unblacklist = context.args[0]; blacklist = get_blacklist(context)
    if item_to_unblacklist not in blacklist: await safe_reply_text(update, context, f"Identifier `{item_to_unblacklist}` is not on the blacklist.", parse_mode=ParseMode.MARKDOWN); return
    del blacklist[item_to_unblacklist]
    await safe_reply_text(update, context, f"✅ Identifier `{item_to_unblacklist}` has been removed from the blacklist.", parse_mode=ParseMode.MARKDOWN)

@blacklist_manager_only
async def view_blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    blacklist, users = get_blacklist(context), get_users(context)
    if not blacklist: await safe_reply_text(update, context, "The blacklist is currently empty."); return
    text = "🚫 **Blacklist**\n\n"
    for item, data in blacklist.items(): admin_id = str(data.get('added_by')); admin_name = users.get(admin_id, {}).get('first_name', f"ID {admin_id}"); text += f"- `{item}`\n  Reason: {escape_markdown_v1(data.get('reason'))}\n  Added by: {escape_markdown_v1(admin_name)}\n"
    await safe_reply_text(update, context, text, parse_mode=ParseMode.MARKDOWN)

async def scan_for_blacklisted_addresses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    blacklist = get_blacklist(context)
    if not blacklist: return
    message_text = update.message.text
    for blacklisted_item, data in blacklist.items():
        if blacklisted_item in message_text:
            user, chat = update.effective_user, update.effective_chat
            reason = data.get("reason", "No reason provided.")
            alert_text = ""
            if is_crypto_address(blacklisted_item):
                alert_text = (f"🚨 BLACKLIST ALERT 🚨\n\n" f"A blacklisted crypto address was just posted.\n\n" f"👤 User: {user.full_name}\n" f"🔗 Username: @{user.username or 'N/A'}\n" f"🏢 Group: {chat.title or 'Unknown Group'}\n" f"📝 Address: {blacklisted_item}\n" f"🚫 Reason: {reason}")
            else:
                alert_text = (f"🚨 BLACKLIST ALERT 🚨\n\n" f"A blacklisted item was just posted.\n\n" f"👤 User: {user.full_name}\n" f"🔗 Username: @{user.username or 'N/A'}\n" f"🏢 Group: {chat.title or 'Unknown Group'}\n" f"📝 Identifier: {blacklisted_item}\n" f"🚫 Reason: {reason}")
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Go to message", url=update.message.link)]]) if update.message.link else None
            for manager_id in BLACKLIST_MANAGERS:
                try: await context.bot.send_message(chat_id=manager_id, text=alert_text, reply_markup=keyboard)
                except Exception as e: logger.error(f"CRITICAL: Failed to send blacklist alert to manager {manager_id}. Error: {e}")
            return

async def dm_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.message and update.message.text and update.effective_chat.type == 'private'): return
    register_user(update, context) # Register early, start command will handle the "first start" logic
    text, user = update.message.text, update.effective_user

    is_viewing_admin = 'viewing_user_id' in context.user_data
    is_viewing_participant = 'viewing_participant_username' in context.user_data
    dashboard_level = context.user_data.get('dashboard_level')

    if user.id in PRIVILEGED_USERS:
        if dashboard_level:
            if dashboard_level == 'admin_list':
                if text == BTN_OWNER_BACK_TO_MAIN: await panel_command(update, context)
                else:
                    admin_id_match = re.search(r'\((\d+)\)', text)
                    if admin_id_match: await show_deals_for_admin(update, context, int(admin_id_match.group(1)))
            elif dashboard_level == 'deal_list':
                if text == BTN_DASH_BACK_TO_ADMINS: await usd_dashboard_command(update, context)
                elif text.startswith(DASH_DEAL_PREFIX): await show_deal_details(update, context, text.split(" ", 1)[1])
            elif dashboard_level == 'deal_details':
                admin_id = context.user_data.get('dashboard_admin_id'); trade_id = context.user_data.get('dashboard_trade_id')
                if text == BTN_DASH_BACK_TO_DEALS: await show_deals_for_admin(update, context, admin_id)
                elif text == BTN_DASH_FORCE_RELEASE: await force_release_deal(update, context, trade_id)
            return

        if is_viewing_participant:
            if text == BTN_PARTICIPANT_STATS: return await show_participant_stats(update, context)
            if text == BTN_PARTICIPANT_HISTORY: return await show_participant_history(update, context)
            await panel_command(update, context)
            return

        if is_viewing_admin:
            target_user_id = context.user_data.get('viewing_user_id')
            reply_text, reply_markup = None, None
            active_back_button = BTN_OWNER_BACK_TO_LIST
            if text == BTN_MY_HOLDING: reply_text = _get_holding_text(target_user_id, context)
            elif text == BTN_MY_PENDING: reply_text = _get_pending_text(target_user_id, context)
            elif text == BTN_MY_VOLUME: reply_markup = ReplyKeyboardMarkup([[KeyboardButton(BTN_VOLUME_TODAY), KeyboardButton(BTN_VOLUME_WEEKLY)],[KeyboardButton(BTN_VOLUME_MONTHLY), KeyboardButton(BTN_VOLUME_ALL_TIME)],[KeyboardButton(active_back_button)]], resize_keyboard=True)
            elif text == BTN_MY_FEES: reply_markup = ReplyKeyboardMarkup([[KeyboardButton(BTN_FEES_TODAY), KeyboardButton(BTN_FEES_WEEKLY)],[KeyboardButton(BTN_FEES_MONTHLY), KeyboardButton(BTN_FEES_ALL_TIME)],[KeyboardButton(active_back_button)]], resize_keyboard=True)
            elif text == active_back_button:
                context.user_data.pop('viewing_user_id'); await owner_list_users(update, context)
                return
            elif text in [BTN_VOLUME_TODAY, BTN_VOLUME_WEEKLY, BTN_VOLUME_MONTHLY, BTN_VOLUME_ALL_TIME]: period = text.split("'s ")[0].split(" ")[0].lower().replace("all-time", "all_time"); reply_text = get_stats_text(target_user_id, context, 'received_amount', period)
            elif text in [BTN_FEES_TODAY, BTN_FEES_WEEKLY, BTN_FEES_MONTHLY, BTN_FEES_ALL_TIME]: period = text.split("'s ")[0].split(" ")[0].lower().replace("all-time", "all_time"); reply_text = get_stats_text(target_user_id, context, 'fee', period)
            if reply_text: await update.message.reply_text(reply_text)
            elif reply_markup: await update.message.reply_text(f"Viewing {text.lower()}:", reply_markup=reply_markup)
            return

        if text == BTN_OWNER_LIST_USERS: return await owner_list_users(update, context)
        if text == BTN_OWNER_GLOBAL_STATS: return await update.message.reply_text(_get_global_stats_text(context))
        if text == BTN_OWNER_ALL_ADMIN_STATS: return await owner_all_admin_stats(update, context)
        if text == BTN_OWNER_EXPORT_EXCEL: return await owner_export_data_excel(update, context)
        if text == BTN_OWNER_EXPORT_CSV: return await owner_export_data_csv(update, context)
        if text == BTN_OWNER_USD_DASHBOARD: return await usd_dashboard_command(update, context)
        if text == BTN_OWNER_BACK_TO_MAIN: return await panel_command(update, context)
        if text == BTN_BLACKLIST_MENU: return await update.message.reply_text("🚫 Blacklist Management\n\nUse the commands below or the buttons to manage the list.", reply_markup=BLACKLIST_KEYBOARD)
        if text.startswith(USER_BUTTON_PREFIX):
            try:
                target_user_id = int(re.search(r'\((\d+)\)$', text).group(1))
                if str(target_user_id) in get_users(context):
                    context.user_data['viewing_user_id'] = target_user_id; target_name = get_users(context)[str(target_user_id)].get('first_name', target_user_id)
                    await update.message.reply_text(f"👁️ Now viewing dashboard for *{target_name}*.", reply_markup=OWNER_VIEWING_KEYBOARD, parse_mode=ParseMode.MARKDOWN)
                else: await update.message.reply_text("User not found.")
            except (AttributeError, ValueError): await update.message.reply_text("Invalid user button format.")
        return

    target_user_id = user.id
    is_admin = await is_authorized_admin(target_user_id, context)

    if not is_admin:
        if text == BTN_PARTICIPANT_STATS: return await show_participant_stats(update, context)
        if text == BTN_PARTICIPANT_HISTORY: return await show_participant_history(update, context)
        await start_command(update, context)
        return

    reply_text, reply_markup = None, None
    if text == BTN_MY_HOLDING: reply_text = _get_holding_text(target_user_id, context)
    elif text == BTN_MY_PENDING: reply_text = _get_pending_text(target_user_id, context)
    elif text == BTN_MY_VOLUME: reply_markup = ReplyKeyboardMarkup([[KeyboardButton(BTN_VOLUME_TODAY), KeyboardButton(BTN_VOLUME_WEEKLY)],[KeyboardButton(BTN_VOLUME_MONTHLY), KeyboardButton(BTN_VOLUME_ALL_TIME)],[KeyboardButton(BTN_BACK)]], resize_keyboard=True)
    elif text == BTN_MY_FEES: reply_markup = ReplyKeyboardMarkup([[KeyboardButton(BTN_FEES_TODAY), KeyboardButton(BTN_FEES_WEEKLY)],[KeyboardButton(BTN_FEES_MONTHLY), KeyboardButton(BTN_FEES_ALL_TIME)],[KeyboardButton(BTN_BACK)]], resize_keyboard=True)
    elif text == BTN_BACK: await start_command(update, context); return
    elif text in [BTN_VOLUME_TODAY, BTN_VOLUME_WEEKLY, BTN_VOLUME_MONTHLY, BTN_VOLUME_ALL_TIME]: period = text.split("'s ")[0].split(" ")[0].lower().replace("all-time", "all_time"); reply_text = get_stats_text(target_user_id, context, 'received_amount', period)
    elif text in [BTN_FEES_TODAY, BTN_FEES_WEEKLY, BTN_FEES_MONTHLY, BTN_FEES_ALL_TIME]: period = text.split("'s ")[0].split(" ")[0].lower().replace("all-time", "all_time"); reply_text = get_stats_text(target_user_id, context, 'fee', period)
    if reply_text: await update.message.reply_text(reply_text)
    elif reply_markup: await update.message.reply_text(f"Viewing {text.lower()}:", reply_markup=reply_markup)

# --- MODIFIED: /start now uses the new professional history format ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    IST = pytz.timezone('Asia/Kolkata')
    is_first_start = str(user.id) not in get_users(context)
    
    register_user(update, context)
    clear_dashboard_state(context)

    if is_first_start and user.username:
        username_lower = user.username.lower()
        past_deals = [t for t in get_transactions(context).values() if username_lower in ((t.get('buyer_username') or '').lower(), (t.get('seller_username') or '').lower())]
        
        if past_deals:
            message_parts = ["<b>👋 Welcome!</b>\nWe've noticed you participated in deals with us before starting the bot. Here is your recent activity:"]
            sorted_deals = sorted(
                past_deals, 
                key=lambda d: d.get('completed_date', d.get('received_date')) or datetime.min.isoformat(), 
                reverse=True
            )
            for deal in sorted_deals[:5]: # Show up to 5 past deals on start
                role = "Buyer" if (deal.get('buyer_username') or '').lower() == username_lower else "Seller"
                other_party_username = deal.get('seller_username' if role == "Buyer" else 'buyer_username', 'N/A')
                escrower_username = deal.get('escrowed_by_username', 'N/A')
                deal_amt = deal.get('deal_amount', deal.get('received_amount', 0))
                status = deal.get('status', 'holding').capitalize()
                status_line = f"{status}"
                if status == 'Completed': status_line += " ✅"
                
                start_date_ist_str = "N/A"
                if start_date_str := deal.get('received_date'):
                    start_date_ist = datetime.fromisoformat(start_date_str).astimezone(IST)
                    start_date_ist_str = start_date_ist.strftime('%d %b %Y, %I:%M %p')
                
                deal_block = (
                    f"<b>Trade ID:</b> <code>{html.escape(deal['trade_id'])}</code>\n"
                    f"<b>Your Role:</b> {role}\n"
                    f"<b>Other Party:</b> @{html.escape(other_party_username)}\n"
                    f"<b>Escrower:</b> {html.escape(escrower_username)}\n"
                    f"<b>Amount:</b> <code>${deal_amt:,.2f}</code>\n"
                    f"<b>Status:</b> {status_line}\n"
                    f"<b>Created:</b> {start_date_ist_str}"
                )
                message_parts.append(deal_block)
            
            full_message = "\n\n-------------------------\n\n".join(message_parts)
            await update.message.reply_text(full_message, parse_mode=ParseMode.HTML)
    
    if user.id in PRIVILEGED_USERS:
        await panel_command(update, context)
    elif await is_authorized_admin(user.id, context):
        await update.message.reply_text(f"🙏🏻 Welcome, Admin {user.first_name}!", reply_markup=ADMIN_KEYBOARD)
    else:
        await update.message.reply_text(f"🙏🏻 Welcome, {user.first_name}! This is your personal deal dashboard.", reply_markup=PARTICIPANT_KEYBOARD)

@admin_only
async def add_deal_command_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    register_user(update, context)
    replied_message = update.message.reply_to_message
    if not replied_message: await safe_reply_text(update, context, "Please reply to the 'DEAL INFO' message to use this command."); return ConversationHandler.END
    processed_ids = get_processed_message_ids(context)
    if replied_message.message_id in processed_ids: await safe_reply_text(update, context, "This deal has already been processed."); return ConversationHandler.END
    if len(context.args) != 1: await safe_reply_text(update, context, "Usage: /add <received_amount>\nExample: /add 1.2k"); return ConversationHandler.END
    try:
        received_amount = parse_shorthand_amount(context.args[0])
        if received_amount <= 0: raise ValueError
    except ValueError: await safe_reply_text(update, context, "Invalid amount format. Use numbers like 1000, 1.2k, or 50."); return ConversationHandler.END
    context.user_data['add_deal_data'] = {'received_amount': received_amount, 'replied_message_id': replied_message.message_id, 'chat_id': update.effective_chat.id, 'user_dict': update.effective_user.to_dict()}
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("1% Fee", callback_data="fee_1.0")], [InlineKeyboardButton("0.7% Fee", callback_data="fee_0.7")],])
    await update.message.reply_text("Please select the fee percentage for this deal:", reply_markup=keyboard, reply_to_message_id=replied_message.message_id)
    return SELECTING_FEE

async def select_fee_and_create_deal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    deal_data = context.user_data.get('add_deal_data')
    if not deal_data: await query.edit_message_text("Error: Could not find deal data. Please start again with /add."); return ConversationHandler.END
    user_dict = deal_data['user_dict']; admin = User(id=user_dict['id'], first_name=user_dict['first_name'], is_bot=user_dict.get('is_bot', False), username=user_dict.get('username'))
    try: fee_percentage = float(query.data.replace('fee_', ''))
    except (ValueError, TypeError): await query.edit_message_text("Error: Invalid fee selection. Please start again."); return ConversationHandler.END
    received_amount = deal_data['received_amount']; replied_message_id = deal_data['replied_message_id']; chat_id = deal_data['chat_id']; fee = received_amount * (fee_percentage / 100.0)
    try:
        fwd_msg = await context.bot.forward_message(chat_id, chat_id, replied_message_id)
        original_text = fwd_msg.text or ""; await fwd_msg.delete()
    except BadRequest as e: logger.error(f"Could not forward replied message {replied_message_id} to get text: {e}"); await query.edit_message_text("Error: Could not read the original deal info message. It might have been deleted."); return ConversationHandler.END
    deal_amount_match = re.search(r"amount\s*[:=]\s*(.+)", original_text, re.I); deal_amount = received_amount
    if deal_amount_match:
        try: deal_amount = parse_shorthand_amount(deal_amount_match.group(1).strip())
        except ValueError: logger.warning(f"Could not parse original deal amount from text: {deal_amount_match.group(1).strip()}. Using received amount as fallback.")
    trade_id = generate_trade_id(); escrowed_by = f"@{admin.username or admin.first_name}"; buyer = re.search(r"buyer\s*:\s*@(\w+)", original_text, re.I); seller = re.search(r"seller\s*:\s*@(\w+)", original_text, re.I); b_user = buyer.group(1) if buyer else ""; s_user = seller.group(1) if seller else ""; release_amount = received_amount - fee
    deal_text = (f"💰 Received Amount : ${received_amount:,.2f}\n" f"📤 Release/Refund Amount : ${release_amount:,.2f}\n" f"🆔 Trade ID: {trade_id}\n\n" f"Continue the Deal\n" f"Buyer : @{b_user}\n" f"Seller : @{s_user}\n\n" f"Escrowed By : {escrowed_by}")
    await query.delete_message()
    try: sent_message = await context.bot.send_message(chat_id, deal_text, reply_to_message_id=replied_message_id)
    except BadRequest: logger.warning(f"Could not reply to message {replied_message_id}. Sending without reply."); sent_message = await context.bot.send_message(chat_id, deal_text)
    get_transactions(context)[trade_id] = {'user_id': admin.id, 'chat_id': chat_id, 'deal_amount': deal_amount, 'received_amount': received_amount, 'fee': fee, 'amount_released': 0.0, 'trade_id': trade_id, 'status': 'holding', 'received_date': datetime.now(pytz.utc).isoformat(), 'completed_date': None, 'deal_info_text': f"Continue the Deal\nBuyer : @{b_user}\nSeller : @{s_user}", 'escrowed_by_username': escrowed_by, 'original_message_id': replied_message_id, 'bot_deal_message_id': sent_message.message_id, 'buyer_username': b_user, 'seller_username': s_user}
    get_processed_message_ids(context).append(replied_message_id); del context.user_data['add_deal_data']
    return ConversationHandler.END

async def cancel_deal_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query: await update.callback_query.answer()
    await safe_reply_text(update, context, "Deal creation cancelled.")
    if 'add_deal_data' in context.user_data: del context.user_data['add_deal_data']
    return ConversationHandler.END

@admin_only
async def close_deal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    replied_msg = update.message.reply_to_message
    if not replied_msg: await safe_reply_text(update, context, "Please reply to a deal message to use this command."); return
    transactions = get_transactions(context); trade_id = None
    for t_id, d in transactions.items():
        if d.get('original_message_id') == replied_msg.message_id or d.get('bot_deal_message_id') == replied_msg.message_id: trade_id = t_id; break
    if not trade_id or trade_id not in transactions: await safe_reply_text(update, context, "Couldn't identify an active deal. Please reply to the bot's deal creation message."); return
    deal = transactions[trade_id]
    if deal.get('user_id') != update.effective_user.id and update.effective_user.id not in PRIVILEGED_USERS: await safe_reply_text(update, context, "❌ Only the original escrower or a bot owner can modify this deal."); return
    if deal['status'] == 'completed': await safe_reply_text(update, context, f"Deal {trade_id} is already completed."); return
    if not context.args: await safe_reply_text(update, context, "❗️Usage: /close <amount>\n\nYou must specify how much to release (e.g., /close 1.2k)."); return
    try: amount_to_close = parse_shorthand_amount(context.args[0]); assert amount_to_close > 0
    except (ValueError, IndexError): await safe_reply_text(update, context, "Invalid amount format. Use numbers like 1000 or 1.2k."); return
    releasable_now = deal['received_amount'] - deal['fee'] - deal['amount_released']
    if amount_to_close > (releasable_now + 0.01): await safe_reply_text(update, context, f"Error: Cannot close ${amount_to_close:,.2f}. Only ${releasable_now:,.2f} is remaining."); return
    deal['amount_released'] += amount_to_close; remaining = deal['received_amount'] - deal['fee'] - deal['amount_released']; b_user = deal.get('buyer_username', 'N/A'); s_user = deal.get('seller_username', 'N/A'); deal_participants_text = f"Buyer : @{b_user}\nSeller : @{s_user}"
    if remaining < 0.01:
        deal['status'], deal['completed_date'] = 'completed', datetime.now(pytz.utc).isoformat()
        reply_text = (f"✅ Deal Completed\n" f"🆔 Trade ID: {trade_id}\n" f"📤 Released: ${amount_to_close:,.2f}\n" f"ℹ️ Total Released: ${deal['amount_released']:,.2f}\n\n" f"{deal_participants_text}\n\n" f"🛡️ Escrowed By: {deal['escrowed_by_username']}")
    else: reply_text = (f"⏳ Deal Still Ongoing\n\n" f"🆔 Trade ID: {trade_id}\n" f"📤 Partially Released: ${amount_to_close:,.2f}\n" f"ℹ️ Total Released: ${deal['amount_released']:,.2f}\n" f"💰 Amount Remaining: ${remaining:,.2f}\n\n" f"{deal_participants_text}\n\n" f"🛡️ Escrowed By: {deal['escrowed_by_username']}")
    try: await context.bot.send_message(chat_id=update.effective_chat.id, text=reply_text, reply_to_message_id=replied_msg.message_id)
    except BadRequest: logger.warning(f"Could not reply to message {replied_msg.message_id} for {trade_id}. Replying to command instead."); await safe_reply_text(update, context, reply_text)

@admin_only
async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    replied_msg = update.message.reply_to_message
    if not replied_msg: await safe_reply_text(update, context, "Please reply to a deal message to use this command."); return
    transactions = get_transactions(context); trade_id = None
    for t_id, d in transactions.items():
        if d.get('original_message_id') == replied_msg.message_id or d.get('bot_deal_message_id') == replied_msg.message_id: trade_id = t_id; break
    if not trade_id or trade_id not in transactions: await safe_reply_text(update, context, "Couldn't identify an active deal. Please reply to the bot's deal creation message."); return
    deal = transactions[trade_id]; user = update.effective_user
    if deal.get('user_id') != user.id and user.id not in PRIVILEGED_USERS: await safe_reply_text(update, context, "❌ Only the original escrower or a bot owner can edit this deal."); return
    if deal['status'] == 'completed': await safe_reply_text(update, context, f"Deal {trade_id} is already completed and cannot be edited."); return
    message_text = update.message.text; changes = {}; change_log = []
    deal_amount_match = re.search(r"^\s*deal\s+([\d.\w$,]+)\s*$", message_text, re.I | re.M); received_amount_match = re.search(r"^\s*received\s+([\d.\w$,]+)\s*$", message_text, re.I | re.M); fee_match = re.search(r"^\s*fee\s+([\d.\w$,]+)\s*$", message_text, re.I | re.M); buyer_match = re.search(r"^\s*buyer\s+(@\w+)\s*$", message_text, re.I | re.M); seller_match = re.search(r"^\s*seller\s+(@\w+)\s*$", message_text, re.I | re.M)
    if deal_amount_match: changes['deal_amount'] = deal_amount_match.group(1)
    if received_amount_match: changes['received_amount'] = received_amount_match.group(1)
    if fee_match: changes['fee'] = fee_match.group(1)
    if buyer_match: changes['buyer_username'] = buyer_match.group(1)
    if seller_match: changes['seller_username'] = seller_match.group(1)
    if not changes: await safe_reply_text(update, context, "❗️No valid fields found to edit. Usage:\nReply to a deal with `/edit` and on new lines specify what to change:\n`deal 5k`\n`received 5k`\n`fee 25`\n`buyer @new_buyer`\n`seller @new_seller`", parse_mode=ParseMode.MARKDOWN); return
    for field, new_value_str in changes.items():
        original_value = None; field_name_for_log = ""
        if field in ['deal_amount', 'received_amount', 'fee']:
            try: amount = parse_shorthand_amount(new_value_str); assert amount >= 0
            except (ValueError, AssertionError): await safe_reply_text(update, context, f"Invalid amount format for `{field}`: `{new_value_str}`."); return
            if field in ['received_amount', 'fee']:
                current_received = deal['received_amount'] if field != 'received_amount' else amount; current_fee = deal['fee'] if field != 'fee' else amount
                if current_received < deal['amount_released'] + current_fee: await safe_reply_text(update, context, f"❌ Error: New amounts would be invalid. Received amount (${current_received:,.2f}) must be >= amount released + fee (${deal['amount_released'] + current_fee:,.2f})."); return
            original_value = f"${deal.get(field, 0):,.2f}"; deal[field] = amount; field_name_for_log = field.replace('_', ' ').title()
        elif field in ['buyer_username', 'seller_username']: original_value = f"@{deal.get(field, 'N/A')}"; deal[field] = new_value_str.lstrip('@'); field_name_for_log = "Buyer" if field == "buyer_username" else "Seller"
        change_log.append(f"<b>{field_name_for_log}:</b> <code>{html.escape(str(original_value))}</code> ➡️ <code>{html.escape(new_value_str)}</code>")
    b_user = deal.get('buyer_username', ''); s_user = deal.get('seller_username', ''); deal['deal_info_text'] = f"Continue the Deal\nBuyer : @{b_user}\nSeller : @{s_user}"; release_amount = deal['received_amount'] - deal['fee']
    new_deal_text = (f"💰 Received Amount : ${deal['received_amount']:,.2f}\n" f"📤 Release/Refund Amount : ${release_amount:,.2f}\n" f"🆔 Trade ID: {trade_id}\n\n" f"Continue the Deal\n" f"Buyer : @{b_user}\n" f"Seller : @{s_user}\n\n" f"Escrowed By : {deal['escrowed_by_username']}")
    group_message_updated = False
    try: await context.bot.edit_message_text(chat_id=deal['chat_id'], message_id=deal['bot_deal_message_id'], text=new_deal_text); group_message_updated = True
    except BadRequest as e: logger.warning(f"Could not edit group message for deal {trade_id} (BadRequest): {e}")
    editor = update.effective_user; IST = pytz.timezone('Asia/Kolkata'); timestamp = datetime.now(IST).strftime('%d %b %Y, %I:%M %p %Z'); chat_title = html.escape(update.effective_chat.title or "Unknown Group"); message_link = update.message.link; edit_status_icon = "✅" if group_message_updated else "⚠️"; edit_status_text = "Successfully updated" if group_message_updated else "Update FAILED"; change_details = "\n".join(change_log)
    notification_text = (f"⚠️ <b>Deal Edited</b> ⚠️\n\n" f"A deal was just modified by an admin.\n\n" f"👤 <b>Admin:</b> {editor.mention_html()} (<code>{editor.id}</code>)\n" f"🆔 <b>Trade ID:</b> <code>{trade_id}</code>\n" f"⏰ <b>Time:</b> {timestamp}\n\n" f"<b><u>Change Details:</u></b>\n{change_details}\n\n" f"🏢 <b>Group:</b> {chat_title}\n" f"🔗 <a href='{message_link}'>Link to Edit Command</a>\n" f"💬 <b>Group Msg Edit Status:</b> {edit_status_icon} {edit_status_text}")
    for user_id in PRIVILEGED_USERS:
        try: await context.bot.send_message(chat_id=user_id, text=notification_text, parse_mode=ParseMode.HTML)
        except Exception as e: logger.error(f"Failed to send edit notification to privileged user {user_id}: {e}")
    reply_to_admin_text = f"✅ Deal `{trade_id}` updated successfully.\n"
    if not group_message_updated: reply_to_admin_text += "⚠️ The original group message could not be edited (it may be too old or deleted)."
    await safe_reply_text(update, context, reply_to_admin_text, parse_mode=ParseMode.MARKDOWN)

async def handle_deal_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.message and update.message.reply_to_message): return
    replied_message = update.message.reply_to_message
    if not (replied_message.from_user.is_bot and replied_message.from_user.id == context.bot.id): return
    trade_id_match = re.search(r"Trade ID: (#TID\w+)", replied_message.text or "")
    if not trade_id_match: return
    trade_id = trade_id_match.group(1)
    deal = get_transactions(context).get(trade_id)
    if not deal: return
    replier_user = update.effective_user
    is_escrower = (replier_user.id == deal.get('user_id'))
    is_buyer = replier_user.username and deal.get('buyer_username') and (replier_user.username.lower() == deal['buyer_username'].lower())
    is_seller = replier_user.username and deal.get('seller_username') and (replier_user.username.lower() == deal['seller_username'].lower())
    is_admin = await is_group_admin(update, context)
    if not (is_escrower or is_buyer or is_seller or is_admin):
        logger.info(f"Unauthorized reply from user '{replier_user.username}' ({replier_user.id}) on deal {trade_id}. Deleting message.")
        try:
            await update.message.delete()
            logger.info(f"Successfully deleted message {update.message.message_id} from {replier_user.id}.")
            chat_id_for_link = str(deal['chat_id']).replace('-100', '')
            deal_message_link = f"https://t.me/c/{chat_id_for_link}/{deal['bot_deal_message_id']}"
            alert_text = (f"🗑️ <b>Unauthorized Reply Deleted</b> 🗑️\n\n" f"The bot automatically removed a reply to a deal thread from a non-participant.\n\n" f"👤 <b>User Deleted:</b> {replier_user.mention_html()} (<code>{replier_user.id}</code>)\n" f"🏢 <b>Group:</b> {html.escape(update.effective_chat.title or 'Unknown')}\n" f"🆔 <b>Trade ID:</b> <code>{trade_id}</code>\n\n" f"🔗 <a href='{deal_message_link}'>View Deal Thread</a>")
            recipients = {deal['user_id'], OWNER_ID, DEVELOPER_ID}
            for user_id in recipients:
                try: await context.bot.send_message(chat_id=user_id, text=alert_text, parse_mode=ParseMode.HTML)
                except Exception as e: logger.error(f"Failed to send deletion alert to admin {user_id} for deal {trade_id}. Error: {e}")
        except BadRequest as e: logger.error(f"Failed to delete unauthorized reply for deal {trade_id}. Bot may lack admin rights. Error: {e}")
    else:
        role = "Admin";
        if is_escrower: role = "Escrower"
        elif is_buyer: role = "Buyer"
        elif is_seller: role = "Seller"
        logger.info(f"Allowing authorized reply from user '{replier_user.username}' (Role: {role}) on deal {trade_id}.")

async def public_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    register_user(target_user, context); text = _get_participant_stats_text(target_user, context); await safe_reply_text(update, context, text)

async def global_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await safe_reply_text(update, context, _get_global_stats_text(context))

@admin_only
async def group_holdings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id; admin_holdings = defaultdict(float)
    for t in get_transactions(context).values():
        if t.get('status') == 'holding' and t.get('chat_id') == chat_id: admin_holdings[t['user_id']] += t['received_amount'] - t['fee'] - t['amount_released']
    if not admin_holdings: await safe_reply_text(update, context, "✅ There are currently no active escrow holdings in this group."); return
    text, grand_total = "📊 *Admin Holdings in this Group*\n\n", 0; users = get_users(context)
    for admin_id, total_holding in sorted(admin_holdings.items(), key=lambda item: item[1], reverse=True): admin_name = users.get(str(admin_id), {}).get('first_name', f"ID {admin_id}"); text += f"👤 {escape_markdown_v1(admin_name)}: ${total_holding:,.2f}\n"; grand_total += total_holding
    text += f"\n💰 *Grand Total Holding*: ${grand_total:,.2f}"; await safe_reply_text(update, context, text, parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adminwise_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    IST = pytz.timezone('Asia/Kolkata'); now_ist = datetime.now(IST); start_of_day_utc = now_ist.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc); admin_volumes = defaultdict(float)
    for t in get_transactions(context).values():
        if t.get('received_date'):
            received_date_aware = datetime.fromisoformat(t['received_date'])
            if received_date_aware >= start_of_day_utc: admin_volumes[t['user_id']] += t.get('deal_amount', t.get('received_amount', 0))
    if not admin_volumes: await safe_reply_text(update, context, "✅ No new escrow deals have been added by any admin today."); return
    text, grand_total = f"📊 *Admin Volume Today ({now_ist.strftime('%d %b %Y')})*\n\n", 0; users = get_users(context)
    for admin_id, total_volume in sorted(admin_volumes.items(), key=lambda item: item[1], reverse=True): admin_name = users.get(str(admin_id), {}).get('first_name', f"ID {admin_id}"); text += f"👤 {escape_markdown_v1(admin_name)}: ${total_volume:,.2f}\n"; grand_total += total_volume
    text += f"\n💰 *Total Today*: ${grand_total:,.2f}"; await safe_reply_text(update, context, text, parse_mode=ParseMode.MARKDOWN)

@admin_only
async def top_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transactions = get_transactions(context).values()
    if not transactions: await safe_reply_text(update, context, "There are no deals yet."); return
    participant_stats = defaultdict(lambda: {'volume': 0.0, 'count': 0})
    for t in transactions:
        deal_amt = t.get('deal_amount', t.get('received_amount', 0))
        if buyer := t.get('buyer_username'): participant_stats[buyer]['volume'] += deal_amt; participant_stats[buyer]['count'] += 1
        if seller := t.get('seller_username'): participant_stats[seller]['volume'] += deal_amt; participant_stats[seller]['count'] += 1
    if not participant_stats: await safe_reply_text(update, context, "No participants found."); return
    sorted_participants = sorted(participant_stats.items(), key=lambda item: item[1]['volume'], reverse=True)
    text = "🏆 *Top 10 Participants (by Volume)*\n\n"
    for i, (username, stats) in enumerate(sorted_participants[:10]): text += f"*{i+1}*. @{escape_markdown_v1(username)}:\n   - Volume: *${stats['volume']:,.2f}*\n   - Deals: *{stats['count']}*\n"
    await safe_reply_text(update, context, text, parse_mode=ParseMode.MARKDOWN)

@privileged_only
async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: await safe_reply_text(update, context, "Please reply to a user's message to make them an admin."); return
    target_user = update.message.reply_to_message.from_user; manual_admins = get_manual_admins(context)
    if target_user.id in manual_admins: await safe_reply_text(update, context, f"{target_user.first_name} is already a manual admin."); return
    manual_admins.add(target_user.id); register_user(target_user, context); await safe_reply_text(update, context, f"✅ {target_user.first_name} has been manually granted admin panel access.")

@privileged_only
async def del_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: await safe_reply_text(update, context, "Please reply to a user's message to remove their admin access."); return
    target_user = update.message.reply_to_message.from_user; manual_admins = get_manual_admins(context)
    if target_user.id not in manual_admins: await safe_reply_text(update, context, f"{target_user.first_name} is not a manual admin."); return
    manual_admins.remove(target_user.id); await safe_reply_text(update, context, f"✅ Admin panel access has been revoked for {target_user.first_name}.")

@privileged_only
async def list_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_users = get_users(context); manual_admins = get_manual_admins(context); text = " *Authorized Admins*\n\n*Manual Admins:*\n"
    if manual_admins:
        for user_id in manual_admins: text += f"- {escape_markdown_v1(all_users.get(str(user_id), {}).get('first_name', f'ID: {user_id}'))} (`{user_id}`)\n"
    else: text += "- _None_\n"
    text += "\n*Group Admins (Automatic):*\n"
    if ALLOWED_ADMIN_GROUPS:
        for group_id in ALLOWED_ADMIN_GROUPS:
            try:
                chat = await context.bot.get_chat(group_id); text += f"\n*From Group: {escape_markdown_v1(chat.title)}* (`{group_id}`)\n"
                group_admins = await context.bot.get_chat_administrators(group_id); group_admin_ids = {admin.user.id for admin in group_admins if admin.user.id not in PRIVILEGED_USERS}
                if group_admin_ids:
                    for user_id in group_admin_ids: text += f"  - {escape_markdown_v1(all_users.get(str(user_id), {}).get('first_name', f'ID: {user_id}'))} (`{user_id}`)\n"
                else: text += "  - _None found besides owners_\n"
            except Exception as e: text += f"\n- _Could not fetch admins for group `{group_id}`: {e}_\n"
    else: text += "- _No admin groups are configured_\n"
    await safe_reply_text(update, context, text, parse_mode=ParseMode.MARKDOWN)

async def usd_dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dashboard_level'] = 'admin_list'
    transactions = get_transactions(context).values(); users = get_users(context); admin_holdings = defaultdict(list)
    for t in transactions:
        if t.get('status') == 'holding': admin_holdings[t['user_id']].append(t)
    if not admin_holdings: await update.message.reply_text("✅ No active deals in holding across all admins.", reply_markup=PRIVILEGED_MAIN_KEYBOARD); clear_dashboard_state(context); return
    buttons = []
    sorted_admins = sorted(admin_holdings.items(), key=lambda item: len(item[1]), reverse=True)
    for admin_id, deals in sorted_admins: admin_info = users.get(str(admin_id), {}); admin_name = admin_info.get('first_name', f"ID: {admin_id}"); deal_count = len(deals); buttons.append([KeyboardButton(f"{DASH_ADMIN_PREFIX}{admin_name} ({admin_id}) - {deal_count} deals")])
    buttons.append([KeyboardButton(BTN_OWNER_BACK_TO_MAIN)])
    await update.message.reply_text("🏦 *All Holdings Dashboard*\n\nSelect an admin to view their active deals.", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True), parse_mode=ParseMode.MARKDOWN)

async def show_deals_for_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, admin_id: int):
    context.user_data['dashboard_level'] = 'deal_list'; context.user_data['dashboard_admin_id'] = admin_id
    transactions = get_transactions(context).values(); admin_deals = sorted([t for t in transactions if t.get('user_id') == admin_id and t.get('status') == 'holding'], key=lambda d: d.get('received_date') or datetime.min.isoformat()); admin_name = get_users(context).get(str(admin_id), {}).get('first_name', f"ID {admin_id}")
    if not admin_deals: await update.message.reply_text(f"✅ {escape_markdown_v1(admin_name)} has no more active deals."); return await usd_dashboard_command(update, context)
    buttons = [[KeyboardButton(f"{DASH_DEAL_PREFIX}{deal['trade_id']}")] for deal in admin_deals]; buttons.append([KeyboardButton(BTN_DASH_BACK_TO_ADMINS)])
    await update.message.reply_text(f"🏦 Viewing holdings for *{escape_markdown_v1(admin_name)}*", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True), parse_mode=ParseMode.MARKDOWN)

async def show_deal_details(update: Update, context: ContextTypes.DEFAULT_TYPE, trade_id: str):
    deal = get_transactions(context).get(trade_id)
    if not deal: await update.message.reply_text("❌ Error: This deal could not be found."); admin_id = context.user_data.get('dashboard_admin_id'); return await show_deals_for_admin(update, context, admin_id)
    context.user_data['dashboard_level'] = 'deal_details'; context.user_data['dashboard_trade_id'] = trade_id
    detail_text = _get_dashboard_deal_details_text(deal, context); buttons = [[KeyboardButton(BTN_DASH_FORCE_RELEASE)], [KeyboardButton(BTN_DASH_BACK_TO_DEALS)]]
    await update.message.reply_text(detail_text, reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True), parse_mode=ParseMode.MARKDOWN)

async def force_release_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, trade_id: str):
    deal = get_transactions(context).get(trade_id); admin_id = context.user_data.get('dashboard_admin_id')
    if not deal: await update.message.reply_text("❌ Error: This deal could not be found while trying to release."); return await show_deals_for_admin(update, context, admin_id)
    if deal['status'] == 'completed': await update.message.reply_text(f"ℹ️ Deal {trade_id} is already completed."); return await show_deals_for_admin(update, context, admin_id)
    deal['status'] = 'completed'; deal['completed_date'] = datetime.now(pytz.utc).isoformat(); deal['amount_released'] = deal['received_amount'] - deal['fee']; releaser_name = update.effective_user.first_name
    await update.message.reply_text(f"✅ *Deal {trade_id} has been manually force-released by {escape_markdown_v1(releaser_name)}.*", parse_mode=ParseMode.MARKDOWN)
    try: await context.bot.send_message(chat_id=deal['chat_id'], text=f"🔔 *Deal Update*\nDeal `{trade_id}` has been manually force-released by a bot owner.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e: logger.warning(f"Could not send force-release notification to group {deal['chat_id']} for deal {trade_id}: {e}")
    await show_deals_for_admin(update, context, admin_id)

def _get_dashboard_deal_details_text(deal: dict, context: ContextTypes.DEFAULT_TYPE) -> str:
    users = get_users(context); admin_info = users.get(str(deal.get('user_id')), {}); admin_name = admin_info.get('first_name', f"ID: {deal.get('user_id')}")
    created_date_str = deal.get('received_date')
    created_date = datetime.fromisoformat(created_date_str).astimezone(pytz.timezone('Asia/Kolkata')).strftime('%d %b %Y, %I:%M %p') if created_date_str else "Unknown"
    return (f"📝 *Deal Details: {deal['trade_id']}*\n\n" f"**Status:** {deal.get('status', 'N/A').capitalize()}\n" f"**Created By:** {escape_markdown_v1(admin_name)}\n" f"**Created On:** {created_date} (IST)\n" f"**Buyer:** @{escape_markdown_v1(deal.get('buyer_username') or 'N/A')}\n" f"**Seller:** @{escape_markdown_v1(deal.get('seller_username') or 'N/A')}\n\n" f"💰 **Deal Amount:** ${deal.get('deal_amount', 0):,.2f}\n" f"📥 **Received:** ${deal.get('received_amount', 0):,.2f}\n" f"💸 **Fee:** ${deal.get('fee', 0):,.2f}\n" f"🔐 **Currently Holding:** ${(deal['received_amount'] - deal['fee']) - deal['amount_released']:,.2f}")

# --- MAIN APPLICATION ---
async def main() -> None:
    if OWNER_ID == 0 or DEVELOPER_ID == 0: logger.critical("FATAL: OWNER_ID or DEVELOPER_ID is not set."); sys.exit(1)
    if not TOKEN or "YOUR_BOT_TOKEN_HERE" in TOKEN: logger.critical("FATAL: TOKEN is not set."); sys.exit(1)
    if not ALLOWED_ADMIN_GROUPS: logger.critical("FATAL: ALLOWED_ADMIN_GROUPS list is empty."); sys.exit(1)
    try:
        persistence = PicklePersistence(filepath=DB_FILE)
        logger.info(f"✅ Using local database file: {DB_FILE}")
        application = Application.builder().token(TOKEN).persistence(persistence).build()
        group_filter = filters.Chat(chat_id=ALLOWED_ADMIN_GROUPS)

        privileged_handlers = [
            CommandHandler("panel", panel_command),
            CommandHandler("addadmin", add_admin_command, filters=group_filter),
            CommandHandler("deladmin", del_admin_command, filters=group_filter),
            CommandHandler("listadmins", list_admins_command),
            CommandHandler("exportexcel", owner_export_data_excel),
            CommandHandler("exportcsv", owner_export_data_csv),
            CommandHandler("blacklist", blacklist_command),
            CommandHandler("unblacklist", unblacklist_command),
            CommandHandler("viewblacklist", view_blacklist_command),
            CommandHandler("viewas", view_as_command, filters=filters.ChatType.PRIVATE)
        ]

        application.add_handlers(privileged_handlers, group=-1)
        application.add_handler(CommandHandler("start", start_command, filters=filters.ChatType.PRIVATE))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, dm_message_router))
        add_conv_handler = ConversationHandler(entry_points=[CommandHandler("add", add_deal_command_start, filters=group_filter)], states={SELECTING_FEE: [CallbackQueryHandler(select_fee_and_create_deal, pattern='^fee_')]}, fallbacks=[CommandHandler("cancel", cancel_deal_creation)], conversation_timeout=120)
        application.add_handler(add_conv_handler)
        group_handlers = [CommandHandler("close", close_deal_command, filters=group_filter), CommandHandler("edit", edit_command, filters=group_filter), CommandHandler("stats", public_stats_command, filters=group_filter), CommandHandler("gstats", global_stats_command, filters=group_filter), CommandHandler("holdings", group_holdings_command, filters=group_filter), CommandHandler("adminwise", adminwise_stats_command, filters=group_filter), CommandHandler("top", top_users_command, filters=group_filter),]
        application.add_handlers(group_handlers)
        application.add_handler(MessageHandler(filters.REPLY & group_filter & ~filters.COMMAND, handle_deal_replies), group=1)
        application.add_handler(MessageHandler(filters.TEXT & group_filter & ~filters.COMMAND, scan_for_blacklisted_addresses), group=1)
        logger.info("✅ Bot is configured. Starting polling...")
        async with application:
            await application.start()
            await application.updater.start_polling()
            await asyncio.Event().wait()
    except FileNotFoundError: logger.warning(f"Database file '{DB_FILE}' not found. A new one will be created on first run.")
    except KeyboardInterrupt: logger.info("Bot shutting down via Ctrl-C.")
    except Exception as e: logger.critical(f"An unexpected error occurred in main: {e}", exc_info=True)
    finally: logger.info("Bot has been stopped.")

if __name__ == "__main__":
    asyncio.run(main())