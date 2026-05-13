import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- আপনার দেওয়া তথ্য (কনফিগারেশন) ---
TOKEN = '8298395996:AAGNXNlNAbJcnC1GRzFXo1tDKlH-MbsPU98'
BIKASH_NO = '01619779327'
NAGAD_NO = '01987926484'
ADMIN_USERNAME = "HasanAhmed730" # আপনার টেলিগ্রাম ইউজারনেম
ADMIN_ID = None # প্রথমবার /start দিলে এটি অটো সেট হবে

# প্যাকেজ লিস্ট (ওস্তাদ, আপনার বলা সেই ৪টি প্যাকেজ)
PACKAGES = {
    "Silver NFT": {"price": 1000, "profit": 100},
    "Gold NFT": {"price": 3000, "profit": 300},
    "Diamond NFT": {"price": 5000, "profit": 500},
    "VIP NFT": {"price": 10000, "profit": 1000}
}

# লগিং সেটিংস
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- ডেটাবেজ কানেকশন ---
def init_db():
    conn = sqlite3.connect('smart_nft.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, total_dep REAL DEFAULT 0, total_with REAL DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS investments 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, pkg_name TEXT, amount REAL, last_profit TEXT, days_done INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# --- মেইন কিবোর্ড মেনু ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("👤 একাউন্ট", callback_data='account'), InlineKeyboardButton("👥 রেফার", callback_data='refer')],
        [InlineKeyboardButton("📦 প্যাকেজ", callback_data='packages'), InlineKeyboardButton("💰 ডিপোজিট", callback_data='deposit')],
        [InlineKeyboardButton("💸 উত্তোলন", callback_data='withdraw'), InlineKeyboardButton("📞 সাপোর্ট", url="https://t.me/snaieliza69")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- অটো প্রফিট সিস্টেম (প্রতি ৩ দিন পর লাভ যোগ হবে) ---
def auto_profit_check():
    conn = sqlite3.connect('smart_nft.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM investments WHERE days_done < 30")
    for inv in cursor.fetchall():
        inv_id, u_id, pkg_name, amt, last_p, days = inv
        last_dt = datetime.strptime(last_p, '%Y-%m-%d %H:%M:%S')
        
        # ৭২ ঘণ্টা (৩ দিন) পার হলে লাভ দিবে
        if datetime.now() >= last_dt + timedelta(hours=72):
            profit_amt = PACKAGES[pkg_name]['profit']
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (profit_amt, u_id))
            cursor.execute("UPDATE investments SET last_profit = ?, days_done = days_done + 3 WHERE id = ?", 
                           (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inv_id))
    conn.commit()
    conn.close()

# --- কমান্ড হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user = update.effective_user
    init_db()
    
    conn = sqlite3.connect('smart_nft.db')
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user.id,))
    conn.commit()
    conn.close()

    if user.username == ADMIN_USERNAME:
        ADMIN_ID = user.id
        await update.message.reply_text("✅ স্বাগতম ওস্তাদ! আপনি এখন এই বোটের অ্যাডমিন।")

    await update.message.reply_text(f"স্বাগতম {user.first_name}!\nSmart NFT বোটে ইনভেস্ট করে আয় শুরু করুন।", reply_markup=main_menu())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    u_id = query.from_user.id
    await query.answer()

    if query.data == 'account':
        conn = sqlite3.connect('smart_nft.db')
        data = conn.execute("SELECT balance, total_dep, total_with FROM users WHERE user_id=?", (u_id,)).fetchone()
        conn.close()
        text = f"👤 ইউজার: {query.from_user.first_name}\n💰 ব্যালেন্স: {data[0]}৳\n📥 মোট ডিপোজিট: {data[1]}৳\n📤 মোট উত্তোলন: {data[2]}৳"
        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == 'deposit':
        await query.edit_message_text("💰 কত টাকা ডিপোজিট করতে চান?\n(নূন্যতম ১০০০ টাকা লিখে পাঠান):")
        context.user_data['state'] = 'waiting_amount'

    elif query.data == 'packages':
        kb = [[InlineKeyboardButton(f"{k} - {v['price']}৳", callback_data=f"buy_{k}")] for k, v in PACKAGES.items()]
        await query.edit_message_text("📦 প্যাকেজ কিনুন (৩০ দিনে লাভ ডাবল):", reply_markup=InlineKeyboardMarkup(kb))

# --- মেসেজ প্রসেসিং ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    text = update.message.text
    user = update.effective_user

    if state == 'waiting_amount':
        try:
            amt = int(text)
            if amt >= 1000:
                context.user_data['d_amt'] = amt
                await update.message.reply_text(f"✅ পরিমাণ: {amt}৳\n\nনিচের নাম্বারে টাকা পাঠিয়ে TrxID দিন:\n🔸 বিকাশ (P): {BIKASH_NO}\n🔸 নগদ (P): {NAGAD_NO}")
                context.user_data['state'] = 'waiting_trx'
            else: await update.message.reply_text("❌ নূন্যতম ১০০০ টাকা হতে হবে।")
        except: await update.message.reply_text("❌ শুধু সংখ্যায় লিখুন।")

    elif state == 'waiting_trx':
        if ADMIN_ID:
            msg = f"📥 **নতুন ডিপোজিট!**\nইউজার: {user.first_name}\nপরিমাণ: {context.user_data['d_amt']}৳\nTrxID: {text}"
            await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
            await update.message.reply_text("✅ আপনার রিকোয়েস্ট পাঠানো হয়েছে।")
        context.user_data['state'] = None

# --- মেইন রানার ---
def main():
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_profit_check, 'interval', minutes=30)
    scheduler.start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("বোট চালু হয়েছে ওস্তাদ!")
    app.run_polling()

if __name__ == '__main__':
    main()
