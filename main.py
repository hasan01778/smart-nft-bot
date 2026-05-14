import logging
import sqlite3
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- কনফিগারেশন ---
TOKEN = '8298395996:AAGNXNlNAbJcnC1GRzFXo1tDKlH-MbsPU98'
ADMIN_ID = 1867145881  
BIKASH_NO = '01619779327'
NAGAD_NO = '01987926484'
SUPPORT_LINK = "https://t.me/snaieliza69"

PACKAGES = {
    "Silver NFT": {"price": 1000, "profit": 100},
    "Gold NFT": {"price": 3000, "profit": 300},
    "Diamond NFT": {"price": 5000, "profit": 500},
    "VIP NFT": {"price": 10000, "profit": 1000}
}

# --- ডাটাবেজ ফাংশন ---
def init_db():
    conn = sqlite3.connect('smart_nft.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, total_dep REAL DEFAULT 0, total_with REAL DEFAULT 0, referred_by INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS investments 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, pkg_name TEXT, amount REAL, last_profit TEXT, days_done INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# --- কিবোর্ড ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("👤 একাউন্ট", callback_data='account'), InlineKeyboardButton("👥 রেফার", callback_data='refer')],
        [InlineKeyboardButton("📦 প্যাকেজ", callback_data='packages'), InlineKeyboardButton("💰 ডিপোজিট", callback_data='deposit')],
        [InlineKeyboardButton("💸 উত্তোলন", callback_data='withdraw'), InlineKeyboardButton("📞 সাপোর্ট", url=SUPPORT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')]])

# --- হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user, args = update.effective_user, context.args
    init_db()
    conn = sqlite3.connect('smart_nft.db')
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

    if query.data == 'main_menu':
        await query.edit_message_text("মেনু থেকে একটি অপশন বেছে নিন:", reply_markup=main_menu())

    elif query.data == 'account':
        conn = sqlite3.connect('smart_nft.db')
        d = conn.execute("SELECT balance, total_dep, total_with FROM users WHERE user_id=?", (u_id,)).fetchone()
        conn.close()
        text = f"👤 আইডি: `{u_id}`\n💰 ব্যালেন্স: {d[0]}৳\n📥 ডিপোজিট: {d[1]}৳\n📤 উত্তোলন: {d[2]}৳"
        await query.edit_message_text(text, reply_markup=back_button(), parse_mode='Markdown')

    elif query.data == 'refer':
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={u_id}"
        await query.edit_message_text(f"👥 রেফার করে ১৫% কমিশন পান।\n🔗 আপনার লিংক: {ref_link}", reply_markup=back_button())

    elif query.data == 'packages':
        kb = [[InlineKeyboardButton(f"{k} - {v['price']}৳", callback_data=f"buy_{k}")] for k, v in PACKAGES.items()]
        kb.append([InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')])
        await query.edit_message_text("📦 প্যাকেজ বেছে নিন (প্রতি ৩ দিনে লাভ এড হবে):", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("buy_"):
        pkg = query.data.split("_")[1]
        price = PACKAGES[pkg]['price']
        conn = sqlite3.connect('smart_nft.db')
        bal = conn.execute("SELECT balance FROM users WHERE user_id=?", (u_id,)).fetchone()[0]
        if bal >= price:
            conn.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, u_id))
            conn.execute("INSERT INTO investments (user_id, pkg_name, amount, last_profit) VALUES (?,?,?,?)", 
                         (u_id, pkg, price, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            await query.edit_message_text(f"✅ সফল! {pkg} কেনা হয়েছে।", reply_markup=back_button())
        else:
            await query.edit_message_text("❌ ব্যালেন্স নেই! আগে ডিপোজিট করুন।", reply_markup=back_button())
        conn.close()

    elif query.data == 'deposit':
        await query.edit_message_text("💰 কত টাকা ডিপোজিট করবেন? (মিনিমাম ১০০০):", reply_markup=back_button())
        context.user_data['state'] = 'dep_amt'

    elif query.data == 'withdraw':
        bd_tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(bd_tz)
        if 12 <= now.hour < 22:
            await query.edit_message_text("💸 কত টাকা তুলতে চান? (১০% চার্জ প্রযোজ্য):", reply_markup=back_button())
            context.user_data['state'] = 'with_amt'
        else:
            await query.edit_message_text("❌ উত্তোলন বন্ধ! সকাল ১২টা থেকে রাত ১০টার মধ্যে চেষ্টা করুন।", reply_markup=back_button())

# --- টেক্সট হ্যান্ডলিং ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state, text, u_id = context.user_data.get('state'), update.message.text, update.effective_user.id
    
    if state == 'dep_amt' and text.isdigit() and int(text) >= 1000:
        context.user_data['d_amt'] = text
        await update.message.reply_text(f"বিকাশ/নগদ: {BIKASH_NO}\nটাকা পাঠিয়ে TrxID দিন।", reply_markup=back_button())
        context.user_data['state'] = 'dep_trx'
    
    elif state == 'dep_trx':
        msg = f"📥 নতুন ডিপোজিট!\nআইডি: `{u_id}`\nটাকা: {context.user_data['d_amt']}\nTrxID: `{text}`\n\n`/add {u_id} {context.user_data['d_amt']}`"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode='Markdown')
        await update.message.reply_text("✅ রিকোয়েস্ট পাঠানো হয়েছে।", reply_markup=back_button())
        context.user_data['state'] = None

    elif state == 'with_amt' and text.isdigit() and int(text) >= 1000:
        context.user_data['w_amt'] = text
        await update.message.reply_text(f"নাম্বার দিন:", reply_markup=back_button())
        context.user_data['state'] = 'with_no'

    elif state == 'with_no':
        msg = f"💸 নতুন উত্তোলন!\nআইডি: `{u_id}`\nটাকা: {context.user_data['w_amt']}\nনাম্বার: `{text}`"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode='Markdown')
        await update.message.reply_text("✅ রিকোয়েস্ট পাঠানো হয়েছে।", reply_markup=back_button())
        context.user_data['state'] = None

# --- এডমিন কমান্ড ---
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        u_id, amount = int(context.args[0]), float(context.args[1])
        conn = sqlite3.connect('smart_nft.db')
        conn.execute("UPDATE users SET balance = balance + ?, total_dep = total_dep + ? WHERE user_id = ?", (amount, amount, u_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ আইডি {u_id} তে {amount}৳ অ্যাড হয়েছে।")
    except: await update.message.reply_text("❌ ফরম্যাট: `/add আইডি টাকা`")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_balance))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == '__main__': main()
