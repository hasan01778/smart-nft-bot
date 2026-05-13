import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- কনফিগারেশন ---
TOKEN = '8298395996:AAGNXNlNAbJcnC1GRzFXo1tDKlH-MbsPU98'
BIKASH_NO = '01619779327'
NAGAD_NO = '01987926484'
ADMIN_USERNAME = "HasanAhmed730"
ADMIN_ID = 1867145881  # আপনার আইডি
SUPPORT_LINK = "https://t.me/snaieliza69" # আপনার দেওয়া নতুন সাপোর্ট লিংক

PACKAGES = {
    "Silver NFT": {"price": 1000, "profit": 100},
    "Gold NFT": {"price": 3000, "profit": 300},
    "Diamond NFT": {"price": 5000, "profit": 500},
    "VIP NFT": {"price": 10000, "profit": 1000}
}

# --- ডেটাবেজ সেটআপ ---
def init_db():
    conn = sqlite3.connect('smart_nft.db')
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

# --- অটো প্রফিট লজিক (প্রতি ৩ দিন পর পর লাভ) ---
def auto_profit_job():
    conn = sqlite3.connect('smart_nft.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM investments WHERE days_done < 30")
    for inv in cursor.fetchall():
        inv_id, u_id, pkg_name, amt, last_p, days = inv
        last_dt = datetime.strptime(last_p, '%Y-%m-%d %H:%M:%S')
        if datetime.now() >= last_dt + timedelta(hours=72):
            profit = PACKAGES[pkg_name]['profit']
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (profit, u_id))
            cursor.execute("UPDATE investments SET last_profit = ?, days_done = days_done + 3 WHERE id = ?", 
                           (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inv_id))
    conn.commit()
    conn.close()

# --- হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    init_db()
    conn = sqlite3.connect('smart_nft.db')
    user_exists = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,)).fetchone()
    if not user_exists:
        ref_id = int(args[0]) if args and args[0].isdigit() else None
        conn.execute("INSERT INTO users (user_id, referred_by) VALUES (?,?)", (user.id, ref_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"স্বাগতম {user.first_name}! আমাদের স্মার্ট এনএফটি সিস্টেমে আপনার ইনভেস্টমেন্ট শুরু করুন।", reply_markup=main_menu())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    u_id = query.from_user.id
    await query.answer()

    if query.data == 'account':
        conn = sqlite3.connect('smart_nft.db')
        d = conn.execute("SELECT balance, total_dep, total_with FROM users WHERE user_id=?", (u_id,)).fetchone()
        invs = conn.execute("SELECT pkg_name FROM investments WHERE user_id=?", (u_id,)).fetchall()
        conn.close()
        pkg_list = ", ".join([i[0] for i in invs]) if invs else "কোনোটি নেই"
        text = f"👤 আইডি: `{u_id}`\n💰 ব্যালেন্স: {d[0]}৳\n📦 একটিভ প্যাকেজ: {pkg_list}\n📥 মোট ডিপোজিট: {d[1]}৳\n📤 মোট উত্তোলন: {d[2]}৳"
        await query.edit_message_text(text, reply_markup=main_menu(), parse_mode='Markdown')

    elif query.data == 'refer':
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={u_id}"
        await query.edit_message_text(f"👥 **রেফারেল প্রোগ্রাম**\n\nআপনার রেফারে কেউ জয়েন করে ডিপোজিট করলে আপনি পাবেন **১৫% কমিশন** (ম্যানুয়ালি এড করা হবে)।\n\n🔗 আপনার লিংক: {ref_link}", reply_markup=main_menu())

    elif query.data == 'deposit':
        await query.edit_message_text("💰 কত টাকা ডিপোজিট করতে চান? (মিনিমাম ১০০০ টাকা):")
        context.user_data['state'] = 'dep_amt'

    elif query.data == 'withdraw':
        await query.edit_message_text("💸 **উত্তোলন শর্তাবলী:**\n- মিনিমাম ১০০০ টাকা\n- এডমিন চার্জ ১০%\n- পেমেন্ট সময় ১-২ ঘণ্টা\n\nকত টাকা তুলতে চান লিখুন:")
        context.user_data['state'] = 'with_amt'

    elif query.data == 'packages':
        kb = [[InlineKeyboardButton(f"{k} - {v['price']}৳", callback_data=f"buy_{k}")] for k, v in PACKAGES.items()]
        await query.edit_message_text("📦 ৩০ দিনে টাকা ডাবল! প্রতি ৩ দিন (৭২ ঘণ্টা) পর পর অটো লাভ এড হবে। প্যাকেজ বেছে নিন:", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("buy_"):
        pkg = query.data.split("_")[1]
        price = PACKAGES[pkg]['price']
        conn = sqlite3.connect('smart_nft.db')
        bal = conn.execute("SELECT balance FROM users WHERE user_id=?", (u_id,)).fetchone()[0]
        if bal >= price:
            conn.execute("UPDATE users SET balance = balance - ?, total_dep = total_dep + ? WHERE user_id=?", (price, price, u_id))
            conn.execute("INSERT INTO investments (user_id, pkg_name, amount, last_profit) VALUES (?,?,?,?)", 
                         (u_id, pkg, price, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            await query.edit_message_text(f"✅ সফল! {pkg} একটিভ হয়েছে। প্রতি ৩ দিন পর লাভ পাবেন।")
        else: await query.edit_message_text("❌ ব্যালেন্স পর্যাপ্ত নয়। আগে ডিপোজিট করুন।")
        conn.close()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state, text, u_id = context.user_data.get('state'), update.message.text, update.effective_user.id

    if state == 'dep_amt':
        if text.isdigit() and int(text) >= 1000:
            context.user_data['d_amt'] = text
            await update.message.reply_text(f"✅ পরিমাণ: {text}৳\n\nনিচের নাম্বারে টাকা পাঠিয়ে TrxID দিন:\n🔸 বিকাশ (P): {BIKASH_NO}\n🔸 নগদ (P): {NAGAD_NO}")
            context.user_data['state'] = 'dep_trx'
        else: await update.message.reply_text("❌ মিনিমাম ১০০০ টাকা হতে হবে।")

    elif state == 'dep_trx':
        msg = f"📥 **নতুন ডিপোজিট রিকোয়েস্ট!**\nইউজার আইডি: {u_id}\nপরিমাণ: {context.user_data['d_amt']}৳\nTrxID: {text}\n\n(চেক করে রেফার কমিশন ম্যানুয়ালি দিন)"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
        await update.message.reply_text("✅ রিকোয়েস্ট পাঠানো হয়েছে। চেক করে দ্রুত এড করা হবে।")
        context.user_data['state'] = None

    elif state == 'with_amt':
        if text.isdigit() and int(text) >= 1000:
            amt = int(text)
            conn = sqlite3.connect('smart_nft.db')
            bal = conn.execute("SELECT balance FROM users WHERE user_id=?", (u_id,)).fetchone()[0]
            if bal >= amt:
                context.user_data['w_amt'] = amt
                await update.message.reply_text(f"পরিমাণ: {amt}৳\nচার্জ (১০%): {amt*0.1}৳\nআপনি পাবেন: {amt*0.9}৳\n\nটাকা নেওয়ার জন্য বিকাশ/নগদ নাম্বার দিন:")
                context.user_data['state'] = 'with_no'
            else: await update.message.reply_text("❌ ব্যালেন্স পর্যাপ্ত নয়।")
            conn.close()

    elif state == 'with_no':
        msg = f"💸 **নতুন উত্তোলন রিকোয়েস্ট!**\nআইডি: {u_id}\nপরিমাণ: {context.user_data['w_amt']}৳\nপেমেন্ট নাম্বার: {text}"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
        await update.message.reply_text("✅ পেমেন্ট রিকোয়েস্ট পাঠানো হয়েছে। ১-২ ঘণ্টায় পেমেন্ট পাবেন।")
        context.user_data['state'] = None

def main():
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_profit_job, 'interval', hours=1)
    scheduler.start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == '__main__': main()
