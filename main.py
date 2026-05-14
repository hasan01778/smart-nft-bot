import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- কনফিগারেশন ---
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

# --- ডাটাবেজ সেটআপ ---
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

# --- ৭২ ঘণ্টা পর অটো লাভ যোগ করার ইঞ্জিন ---
def give_profit():
    conn = sqlite3.connect('smart_nft.db')
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("SELECT id, user_id, pkg_name, last_profit_time FROM investments")
    for inv in cursor.fetchall():
        inv_id, u_id, pkg, last_time = inv
        last_time_dt = datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')
        if now >= last_time_dt + timedelta(hours=72):
            profit_amt = PACKAGES[pkg]['profit']
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (profit_amt, u_id))
            cursor.execute("UPDATE investments SET last_profit_time = ? WHERE id = ?", (now.strftime('%Y-%m-%d %H:%M:%S'), inv_id))
    conn.commit()
    conn.close()

# --- মেনু ও বাটন ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("👤 একাউন্ট", callback_data='account'), InlineKeyboardButton("👥 রেফার", callback_data='refer')],
        [InlineKeyboardButton("📦 প্যাকেজ কিনুন", callback_data='packages'), InlineKeyboardButton("💰 ডিপোজিট", callback_data='deposit')],
        [InlineKeyboardButton("💸 উত্তোলন", callback_data='withdraw'), InlineKeyboardButton("📞 সাপোর্ট", url=SUPPORT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')]])

# --- হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    u_id = update.effective_user.id
    args = context.args # রেফার চেক
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
        await query.edit_message_text("একটি অপশন বেছে নিন:", reply_markup=main_menu())

    elif query.data == 'packages':
        kb = [[InlineKeyboardButton(f"🛒 কিনুন {val['display']} ({val['price']}৳)", callback_data=f"buy_{key}")] for key, val in PACKAGES.items()]
        kb.append([InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')])
        await query.edit_message_text("📦 আমাদের প্যাকেজসমূহ (৭২ ঘণ্টা পর লাভ + ১৫% রেফার কমিশন):", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("buy_"):
        pkg_key = query.data.replace("buy_", "")
        pkg = PACKAGES[pkg_key]
        conn = sqlite3.connect('smart_nft.db')
        user_info = conn.execute("SELECT balance, referred_by FROM users WHERE user_id=?", (u_id,)).fetchone()
        
        if user_info[0] >= pkg['price']:
            # ব্যালেন্স কাটা
            conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (pkg['price'], u_id))
            conn.execute("INSERT INTO investments (user_id, pkg_name, amount, last_profit_time) VALUES (?,?,?,?)", 
                         (u_id, pkg_key, pkg['price'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            # --- ১৫% রেফার কমিশন লজিক ---
            ref_id = user_info[1]
            if ref_id != 0:
                commission = pkg['price'] * 0.15
                conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (commission, ref_id))
                try:
                    await context.bot.send_message(chat_id=ref_id, text=f"🎉 অভিনন্দন! আপনার রেফারেল একটি প্যাকেজ কিনেছে। আপনি ১৫% কমিশন হিসেবে {commission}৳ পেয়েছেন!")
                except: pass
            
            conn.commit()
            await query.edit_message_text(f"✅ সফল! আপনি {pkg['display']} কিনেছেন।", reply_markup=back_button())
        else:
            await query.edit_message_text("❌ ব্যালেন্স নেই! আগে ডিপোজিট করুন।", reply_markup=back_button())
        conn.close()

    elif query.data == 'refer':
        bot_user = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_user}?start={u_id}"
        await query.edit_message_text(f"👥 **রেফারেল প্রোগ্রাম**\n\nআপনার লিংকে কেউ জয়েন করে প্যাকেজ কিনলে আপনি সরাসরি **১৫% কমিশন** পাবেন।\n\n🔗 আপনার লিংক: {ref_link}", reply_markup=back_button())

    elif query.data == 'account':
        conn = sqlite3.connect('smart_nft.db')
        d = conn.execute("SELECT balance, total_dep, total_with FROM users WHERE user_id=?", (u_id,)).fetchone()
        conn.close()
        await query.edit_message_text(f"👤 আইডি: `{u_id}`\n💰 ব্যালেন্স: {d[0]}৳\n📥 ডিপোজিট: {d[1]}৳\n📤 উত্তোলন: {d[2]}৳", reply_markup=back_button(), parse_mode='Markdown')

    # ... ডিপোজিট ও অন্যান্য আগের মতোই আছে ...

def main():
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(give_profit, 'interval', minutes=30)
    scheduler.start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: None)) # টেক্সট হ্যান্ডলার এখানে যোগ করে নিন প্রয়োজন মতো
    app.run_polling()

if __name__ == '__main__': main()
