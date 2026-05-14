import logging
import sqlite3
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- কনফিগারেশন ---
TOKEN = '8298395996:AAGNXNlNAbJcnC1GRzFXo1tDKlH-MbsPU98'
ADMIN_ID = 1867145881  
BIKASH_NO = '01619779327'
NAGAD_NO = '01987926484'
SUPPORT_LINK = "https://t.me/snaieliza69"

DB_FILE = 'smart_nft.db'

# --- ডাটাবেজ ফাংশন ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, total_dep REAL DEFAULT 0, total_with REAL DEFAULT 0, referred_by INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS investments 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, pkg_name TEXT, amount REAL, last_profit TEXT, days_done INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# --- মেইন মেনু ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("👤 একাউন্ট", callback_data='account'), InlineKeyboardButton("👥 রেফার", callback_data='refer')],
        [InlineKeyboardButton("📦 প্যাকেজ", callback_data='packages'), InlineKeyboardButton("💰 ডিপোজিট", callback_data='deposit')],
        [InlineKeyboardButton("💸 উত্তোলন", callback_data='withdraw'), InlineKeyboardButton("📞 সাপোর্ট", url=SUPPORT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- টাকা অ্যাড কমান্ড ---
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        u_id, amount = int(context.args[0]), float(context.args[1])
        conn = get_db_connection()
        conn.execute("UPDATE users SET balance = balance + ?, total_dep = total_dep + ? WHERE user_id = ?", (amount, amount, u_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ সাকসেস! আইডি `{u_id}` তে {amount}৳ অ্যাড হয়েছে।")
        try: await context.bot.send_message(chat_id=u_id, text=f"🎉 অভিনন্দন! {amount}৳ অ্যাড হয়েছে।")
        except: pass
    except: await update.message.reply_text("❌ ভুল! উদাহরণ: `/add 123456 500`")

# --- হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user, args = update.effective_user, context.args
    init_db()
    conn = get_db_connection()
    user_exists = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,)).fetchone()
    if not user_exists:
        ref_id = int(args[0]) if args and args[0].isdigit() else None
        conn.execute("INSERT INTO users (user_id, referred_by) VALUES (?,?)", (user.id, ref_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"স্বাগতম {user.first_name}!", reply_markup=main_menu())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    u_id = query.from_user.id
    await query.answer()

    if query.data == 'account':
        conn = get_db_connection()
        d = conn.execute("SELECT balance, total_dep, total_with FROM users WHERE user_id=?", (u_id,)).fetchone()
        conn.close()
        await query.edit_message_text(f"👤 আইডি: `{u_id}`\n💰 ব্যালেন্স: {d[0]}৳\n📥 ডিপোজিট: {d[1]}৳\n📤 উত্তোলন: {d[2]}৳", reply_markup=main_menu(), parse_mode='Markdown')
    
    elif query.data == 'deposit':
        await query.edit_message_text("💰 কত টাকা ডিপোজিট করবেন? (মিনিমাম ১০০০ টাকা):")
        context.user_data['state'] = 'dep_amt'

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state, text, u_id = context.user_data.get('state'), update.message.text, update.effective_user.id
    if state == 'dep_amt' and text.isdigit() and int(text) >= 1000:
        context.user_data['d_amt'] = text
        await update.message.reply_text(f"বিকাশ/নগদ (P): {BIKASH_NO}\nটাকা পাঠিয়ে TrxID দিন।")
        context.user_data['state'] = 'dep_trx'
    elif state == 'dep_trx':
        msg = f"📥 নতুন ডিপোজিট!\nআইডি: `{u_id}`\nটাকা: {context.user_data['d_amt']}\nTrxID: `{text}`\n\n`/add {u_id} {context.user_data['d_amt']}`"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode='Markdown')
        await update.message.reply_text("✅ রিকোয়েস্ট পাঠানো হয়েছে।")
        context.user_data['state'] = None

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_balance))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == '__main__': main()
