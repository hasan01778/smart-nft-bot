import sqlite3
import logging
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- সেটিংস (আপনার তথ্য বসানো হয়েছে) ---
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

# --- ডাটাবেজ ফাংশন ---
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

# --- লাভ দেওয়ার অটোমেটিক ইঞ্জিন ---
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

# --- কিবোর্ডসমূহ ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("👤 একাউন্ট", callback_data='account'), InlineKeyboardButton("👥 রেফার", callback_data='refer')],
        [InlineKeyboardButton("📦 প্যাকেজ কিনুন", callback_data='packages'), InlineKeyboardButton("💰 ডিপোজিট", callback_data='deposit')],
        [InlineKeyboardButton("💸 উত্তোলন", callback_data='withdraw'), InlineKeyboardButton("📞 সাপোর্ট", url=SUPPORT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_main_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')]])

# --- হ্যান্ডলার ফাংশনস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    u_id = update.effective_user.id
    args = context.args # রেফারেল আইডি চেক
    
    conn = sqlite3.connect('smart_nft.db')
    if not conn.execute("SELECT user_id FROM users WHERE user_id=?", (u_id,)).fetchone():
        ref_id = int(args[0]) if args and args[0].isdigit() else 0
        conn.execute("INSERT INTO users (user_id, referred_by) VALUES (?,?)", (u_id, ref_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"স্বাগতম {update.effective_user.first_name}!\nস্মার্ট এনএফটি বোটে আপনার যাত্রা শুরু হোক।", reply_markup=main_menu_keyboard())

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    u_id = query.from_user.id
    await query.answer()

    if query.data == 'main_menu':
        context.user_data['state'] = None
        await query.edit_message_text("মেনু থেকে একটি অপশন বেছে নিন:", reply_markup=main_menu_keyboard())

    elif query.data == 'account':
        conn = sqlite3.connect('smart_nft.db')
        d = conn.execute("SELECT balance, total_dep, total_with FROM users WHERE user_id=?", (u_id,)).fetchone()
        conn.close()
        text = f"👤 **ইউজার আইডি:** `{u_id}`\n💰 **ব্যালেন্স:** {d[0]}৳\n📥 **মোট ডিপোজিট:** {d[1]}৳\n📤 **মোট উত্তোলন:** {d[2]}৳"
        await query.edit_message_text(text, reply_markup=back_to_main_button(), parse_mode='Markdown')

    elif query.data == 'refer':
        bot_user = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_user}?start={u_id}"
        text = f"👥 **রেফারেল কমিশন ১৫%**\n\nআপনার লিংক দিয়ে কেউ জয়েন করে প্যাকেজ কিনলে আপনি সাথে সাথে কমিশন পাবেন।\n\n🔗 **আপনার লিংক:**\n{ref_link}"
        await query.edit_message_text(text, reply_markup=back_to_main_button())

    elif query.data == 'packages':
        kb = [[InlineKeyboardButton(f"🛒 কিনুন {v['display']} ({v['price']}৳)", callback_data=f"buy_{k}")] for k, v in PACKAGES.items()]
        kb.append([InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')])
        await query.edit_message_text("📦 **প্যাকেজ কিনলে প্রতি ৭২ ঘণ্টা পর লাভ পাবেন:**", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("buy_"):
        pkg_key = query.data.replace("buy_", "")
        pkg = PACKAGES[pkg_key]
        conn = sqlite3.connect('smart_nft.db')
        user_info = conn.execute("SELECT balance, referred_by FROM users WHERE user_id=?", (u_id,)).fetchone()
        
        if user_info[0] >= pkg['price']:
            conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (pkg['price'], u_id))
            conn.execute("INSERT INTO investments (user_id, pkg_name, amount, last_profit_time) VALUES (?,?,?,?)", 
                         (u_id, pkg_key, pkg['price'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            # ১৫% রেফার কমিশন
            ref_id = user_info[1]
            if ref_id and ref_id != 0:
                comm = pkg['price'] * 0.15
                conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (comm, ref_id))
                try: await context.bot.send_message(chat_id=ref_id, text=f"🎉 আপনার রেফারেল প্যাকেজ কিনেছে! আপনি {comm}৳ কমিশন পেয়েছেন।")
                except: pass
            
            conn.commit()
            await query.edit_message_text(f"✅ সফল! {pkg['display']} কেনা হয়েছে। ৭২ ঘণ্টা পর লাভ যোগ হবে।", reply_markup=back_to_main_button())
        else:
            await query.edit_message_text("❌ ব্যালেন্স নেই! আগে ডিপোজিট করুন।", reply_markup=back_to_main_button())
        conn.close()

    elif query.data == 'deposit':
        text = f"💰 **ডিপোজিট করুন (Personal):**\n\n🔸 বিকাশ: `{BIKASH_NO}`\n🔸 নগদ: `{NAGAD_NO}`\n\nটাকা পাঠানোর পর TrxID এবং পরিমাণ লিখে পাঠান।"
        await query.edit_message_text(text, reply_markup=back_to_main_button(), parse_mode='Markdown')
        context.user_data['state'] = 'waiting_dep'

    elif query.data == 'withdraw':
        bd_tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(bd_tz)
        if 12 <= now.hour < 22:
            await query.edit_message_text("💸 কত টাকা তুলতে চান এবং কোন নাম্বারে? বিস্তারিত লিখে পাঠান।", reply_markup=back_to_main_button())
            context.user_data['state'] = 'waiting_with'
        else:
            await query.edit_message_text("❌ উত্তোলন বন্ধ! সময়: দুপুর ১২টা থেকে রাত ১০টা পর্যন্ত।", reply_markup=back_to_main_button())

# --- টেক্সট মেসেজ হ্যান্ডলার ---
async def handle_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    msg = update.message.text
    state = context.user_data.get('state')

    if state == 'waiting_dep':
        report = f"📥 **নতুন ডিপোজিট রিকোয়েস্ট!**\nID: `{u_id}`\nতথ্য: {msg}\n\nঅ্যাড করতে: `/add {u_id} পরিমাণ`"
        await context.bot.send_message(chat_id=ADMIN_ID, text=report, parse_mode='Markdown')
        await update.message.reply_text("✅ ধন্যবাদ! আপনার তথ্য পাঠানো হয়েছে। খুব দ্রুত ব্যালেন্স যোগ করা হবে।", reply_markup=back_to_main_button())
        context.user_data['state'] = None

    elif state == 'waiting_with':
        report = f"💸 **নতুন উত্তোলন রিকোয়েস্ট!**\nID: `{u_id}`\nতথ্য: {msg}"
        await context.bot.send_message(chat_id=ADMIN_ID, text=report, parse_mode='Markdown')
        await update.message.reply_text("✅ আপনার উত্তোলনের তথ্য পাওয়া গেছে। কিছুক্ষণের মধ্যে পেমেন্ট করা হবে।", reply_markup=back_to_main_button())
        context.user_data['state'] = None

# --- অ্যাডমিন কমান্ড ---
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        t_id, amt = int(context.args[0]), float(context.args[1])
        conn = sqlite3.connect('smart_nft.db')
        conn.execute("UPDATE users SET balance = balance + ?, total_dep = total_dep + ? WHERE user_id = ?", (amt, amt, t_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ সফল! আইডি {t_id} তে {amt}৳ অ্যাড হয়েছে।")
        await context.bot.send_message(chat_id=t_id, text=f"🎉 অভিনন্দন! আপনার একাউন্টে {amt}৳ অ্যাড করা হয়েছে।")
    except: await update.message.reply_text("সঠিক ফরম্যাট: `/add আইডি টাকা`")

# --- মেইন ফাংশন ---
def main():
    init_db()
    
    # প্রফিট টাইমার (প্রতি ৩০ মিনিটে চেক করবে)
    scheduler = BackgroundScheduler()
    scheduler.add_job(give_profit, 'interval', minutes=30)
    scheduler.start()

    app = Application.builder().token(TOKEN).build()

    # হ্যান্ডলার রেজিস্ট্রেশন
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_balance))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
