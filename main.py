import sqlite3
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- সেটিংস ---
TOKEN = '8298395996:AAGNXNlNAbJcnC1GRzFXo1tDKlH-MbsPU98'
ADMIN_ID = 6004236595  
BIKASH_NO = '01619779327'
NAGAD_NO = '01987926484'
SUPPORT_LINK = "https://t.me/snaieliza69"

PACKAGES = {
    "Silver_NFT": {"display": "🥈 Silver NFT", "price": 1000, "profit": 100},
    "Gold_NFT": {"display": "🥇 Gold NFT", "price": 3000, "profit": 300},
    "Diamond_NFT": {"display": "💎 Diamond NFT", "price": 5000, "profit": 500},
    "VIP_NFT": {"display": "👑 VIP NFT", "price": 10000, "profit": 1000}
}

# --- ডাটাবেজ ---
def init_db():
    conn = sqlite3.connect('smart_nft.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, total_dep REAL DEFAULT 0, 
                       total_with REAL DEFAULT 0, referred_by INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS investments 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, pkg_name TEXT, amount REAL, last_profit_time TEXT)''')
    conn.commit()
    conn.close()

# --- মেইন মেনু কিবোর্ড ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("👤 একাউন্ট", callback_data='account'), InlineKeyboardButton("👥 রেফার", callback_data='refer')],
        [InlineKeyboardButton("📦 প্যাকেজ কিনুন", callback_data='packages'), InlineKeyboardButton("📊 একটিভ প্যাকেজ", callback_data='active_pkgs')],
        [InlineKeyboardButton("💰 ডিপোজিট", callback_data='deposit'), InlineKeyboardButton("💸 উত্তোলন", callback_data='withdraw')],
        [InlineKeyboardButton("📞 সাপোর্ট", url=SUPPORT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')]])

# --- হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    u_id = update.effective_user.id
    args = context.args
    conn = sqlite3.connect('smart_nft.db')
    if not conn.execute("SELECT user_id FROM users WHERE user_id=?", (u_id,)).fetchone():
        ref_id = int(args[0]) if args and args[0].isdigit() else 0
        conn.execute("INSERT INTO users (user_id, referred_by) VALUES (?,?)", (u_id, ref_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"স্বাগতম {update.effective_user.first_name}!", reply_markup=main_menu())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    u_id = query.from_user.id
    await query.answer()

    if query.data == 'main_menu':
        context.user_data['state'] = None
        await query.edit_message_text("একটি অপশন বেছে নিন:", reply_markup=main_menu())

    elif query.data == 'active_pkgs':
        conn = sqlite3.connect('smart_nft.db')
        pkgs = conn.execute("SELECT pkg_name, last_profit_time FROM investments WHERE user_id=?", (u_id,)).fetchall()
        conn.close()
        
        if not pkgs:
            await query.edit_message_text("❌ আপনার কোনো একটিভ প্যাকেজ নেই!", reply_markup=back_button())
        else:
            text = "📊 **আপনার একটিভ প্যাকেজসমূহ:**\n\n"
            for p in pkgs:
                name = PACKAGES[p[0]]['display']
                last_time = datetime.strptime(p[1], '%Y-%m-%d %H:%M:%S')
                next_time = last_time + timedelta(hours=72)
                text += f"🔹 {name}\n🕒 পরবর্তী লাভ: `{next_time.strftime('%d-%m %I:%M %p')}`\n\n"
            await query.edit_message_text(text, reply_markup=back_button(), parse_mode='Markdown')

    elif query.data == 'packages':
        kb = [[InlineKeyboardButton(f"🛒 কিনুন {val['display']} ({val['price']}৳)", callback_data=f"buy_{key}")] for key, val in PACKAGES.items()]
        kb.append([InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')])
        await query.edit_message_text("📦 **ইনভেস্টমেন্ট প্যাকেজসমূহ (৭২ ঘণ্টা পর লাভ):**", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("buy_"):
        pkg_key = query.data.replace("buy_", "")
        pkg = PACKAGES[pkg_key]
        conn = sqlite3.connect('smart_nft.db')
        user_info = conn.execute("SELECT balance, referred_by FROM users WHERE user_id=?", (u_id,)).fetchone()
        
        if user_info[0] >= pkg['price']:
            conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (pkg['price'], u_id))
            conn.execute("INSERT INTO investments (user_id, pkg_name, amount, last_profit_time) VALUES (?,?,?,?)", 
                         (u_id, pkg_key, pkg['price'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            # রেফার কমিশন (১৫%)
            ref_id = user_info[1]
            if ref_id and ref_id != 0:
                comm = pkg['price'] * 0.15
                conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (comm, ref_id))
                try: await context.bot.send_message(chat_id=ref_id, text=f"🎉 কমিশন পেয়েছেন! আপনার রেফারেল {pkg['display']} কিনেছে।")
                except: pass
            conn.commit()
            await query.edit_message_text(f"✅ সফল! {pkg['display']} একটিভ হয়েছে।", reply_markup=back_button())
        else:
            await query.edit_message_text("❌ পর্যাপ্ত ব্যালেন্স নেই!", reply_markup=back_button())
        conn.close()

    elif query.data == 'deposit':
        await query.edit_message_text("💰 **কত টাকা ডিপোজিট করতে চান লিখুন?**\n(সর্বনিম্ন ১০০০৳)", reply_markup=back_button())
        context.user_data['state'] = 'ask_dep_amount'

    elif query.data == 'account':
        conn = sqlite3.connect('smart_nft.db')
        d = conn.execute("SELECT balance, total_dep, total_with FROM users WHERE user_id=?", (u_id,)).fetchone()
        conn.close()
        await query.edit_message_text(f"👤 আইডি: `{u_id}`\n💰 ব্যালেন্স: {d[0]}৳\n📥 ডিপোজিট: {d[1]}৳\n📤 উত্তোলন: {d[2]}৳", reply_markup=back_button(), parse_mode='Markdown')

    # ... অন্যান্য বাটন (Refer, Withdraw) আগের মতোই কাজ করবে ...

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    msg = update.message.text
    state = context.user_data.get('state')

    if state == 'ask_dep_amount':
        if msg.isdigit() and int(msg) >= 1000:
            context.user_data['dep_amount'] = msg
            await update.message.reply_text(f"✅ {msg}৳ ডিপোজিট করতে নিচের নাম্বারে টাকা পাঠান:\n\n🔸 বিকাশ: `{BIKASH_NO}`\n🔸 নগদ: `{NAGAD_NO}`\n\nটাকা পাঠিয়ে আপনার **TrxID** লিখুন।", reply_markup=back_button(), parse_mode='Markdown')
            context.user_data['state'] = 'waiting_trx'
        else:
            await update.message.reply_text("❌ সর্বনিম্ন ১০০০৳ হতে হবে। আবার পরিমাণ লিখুন।")

    elif state == 'waiting_trx':
        amount = context.user_data.get('dep_amount')
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"📥 **ডিপোজিট রিকোয়েস্ট!**\nID: `{u_id}`\nপরিমাণ: {amount}৳\nTrxID: {msg}\n\n`/add {u_id} {amount}`")
        await update.message.reply_text("✅ তথ্য জমা হয়েছে। দ্রুত চেক করা হবে।", reply_markup=back_button())
        context.user_data['state'] = None

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        t_id, amt = int(context.args[0]), float(context.args[1])
        conn = sqlite3.connect('smart_nft.db')
        conn.execute("UPDATE users SET balance = balance + ?, total_dep = total_dep + ? WHERE user_id = ?", (amt, amt, t_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ আইডি {t_id} তে {amt}৳ অ্যাড হয়েছে।")
        await context.bot.send_message(chat_id=t_id, text=f"🎉 আপনার একাউন্টে {amt}৳ অ্যাড করা হয়েছে।")
    except: await update.message.reply_text("ভুল! লিখুন: `/add আইডি টাকা`")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_balance))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == '__main__': main()
