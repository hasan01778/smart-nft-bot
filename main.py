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
ADMIN_ID = 1867145881  # আপনার আইডি
SUPPORT_LINK = "https://t.me/snaieliza69"

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

# --- ব্যাক বাটন কিবোর্ড ---
def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')]])

# --- টাকা অ্যাড করার কমান্ড ---
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        u_id, amount = int(context.args[0]), float(context.args[1])
        conn = sqlite3.connect('smart_nft.db')
        conn.execute("UPDATE users SET balance = balance + ?, total_dep = total_dep + ? WHERE user_id = ?", (amount, amount, u_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ সফল! আইডি `{u_id}` তে {amount}৳ অ্যাড করা হয়েছে।")
        try: await context.bot.send_message(chat_id=u_id, text=f"🎉 অভিনন্দন! আপনার একাউন্টে {amount}৳ ডিপোজিট সাকসেসফুল।")
        except: pass
    except: await update.message.reply_text("❌ ফরম্যাট: `/add 1234567 1000`")

# --- অটো প্রফিট জব ---
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
    user, args = update.effective_user, context.args
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

    if query.data == 'main_menu':
        await query.edit_message_text(f"স্বাগতম! মেনু থেকে একটি অপশন বেছে নিন।", reply_markup=main_menu())

    elif query.data == 'account':
        conn = sqlite3.connect('smart_nft.db')
        d = conn.execute("SELECT balance, total_dep, total_with FROM users WHERE user_id=?", (u_id,)).fetchone()
        invs = conn.execute("SELECT pkg_name FROM investments WHERE user_id=?", (u_id,)).fetchall()
        conn.close()
        pkg_list = ", ".join([i[0] for i in invs]) if invs else "কোনোটি নেই"
        text = f"👤 আইডি: `{u_id}`\n💰 ব্যালেন্স: {d[0]}৳\n📦 প্যাকেজ: {pkg_list}\n📥 ডিপোজিট: {d[1]}৳\n📤 উত্তোলন: {d[2]}৳"
        await query.edit_message_text(text, reply_markup=back_button(), parse_mode='Markdown')

    elif query.data == 'refer':
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={u_id}"
        await query.edit_message_text(f"👥 **রেফারেল প্রোগ্রাম**\n\nপ্রতিটি ডিপোজিটে পাবেন ১৫% কমিশন!\n\n🔗 লিংক: {ref_link}", reply_markup=back_button())

    elif query.data == 'deposit':
        await query.edit_message_text("💰 কত টাকা ডিপোজিট করতে চান? (মিনিমাম ১০০০ টাকা):", reply_markup=back_button())
        context.user_data['state'] = 'dep_amt'

    elif query.data == 'withdraw':
        await query.edit_message_text("💸 নূন্যতম ১০০০ টাকা। এডমিন চার্জ ১০%। কত টাকা তুলতে চান?", reply_markup=back_button())
        context.user_data['state'] = 'with_amt'

    elif query.data == 'packages':
        kb = [[InlineKeyboardButton(f"{k} - {v['price']}৳", callback_data=f"buy_{k}")] for k, v in PACKAGES.items()]
        kb.append([InlineKeyboardButton("🔙 ফিরে যান", callback_data='main_menu')])
        await query.edit_message_text("📦 প্যাকেজ বেছে নিন (প্রতি ৩ দিনে লাভ):", reply_markup=InlineKeyboardMarkup(kb))

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
            await query.edit_message_text(f"✅ সফল! {pkg} একটিভ হয়েছে।", reply_markup=back_button())
        else: await query.edit_message_text("❌ ব্যালেন্স নেই।", reply_markup=back_button())
        conn.close()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state, text, u_id = context.user_data.get('state'), update.message.text, update.effective_user.id
    if state == 'dep_amt':
        if text.isdigit() and int(text) >= 1000:
            context.user_data['d_amt'] = text
            await update.message.reply_text(f"✅ পরিমাণ: {text}৳\n\nবিকাশ/নগদ (P): {BIKASH_NO}\nটাকা পাঠিয়ে TrxID দিন।", reply_markup=back_button())
            context.user_data['state'] = 'dep_trx'
        else: await update.message.reply_text("❌ নূন্যতম ১০০০ টাকা লিখুন।")
    elif state == 'dep_trx':
        msg = f"📥 **নতুন ডিপোজিট!**\nআইডি: `{u_id}`\nপরিমাণ: {context.user_data['d_amt']}৳\nTrxID: `{text}`\n\n`/add {u_id} {context.user_data['d_amt']}`"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode='Markdown')
        await update.message.reply_text("✅ রিকোয়েস্ট পাঠানো হয়েছে।", reply_markup=back_button())
        context.user_data['state'] = None
    elif state == 'with_amt':
        if text.isdigit() and int(text) >= 1000:
            context.user_data['w_amt'] = int(text)
            await update.message.reply_text(f"চার্জ বাদে আপনি পাবেন: {int(text)*0.9}৳\n\nবিকাশ/নগদ নাম্বার দিন:", reply_markup=back_button())
            context.user_data['state'] = 'with_no'
        else: await update.message.reply_text("❌ নূন্যতম ১০০০ টাকা।")
    elif state == 'with_no':
        msg = f"💸 **উত্তোলন রিকোয়েস্ট!**\nআইডি: `{u_id}`\nপরিমাণ: {context.user_data['w_amt']}৳\nনাম্বার: `{text}`"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode='Markdown')
        await update.message.reply_text("✅ রিকোয়েস্ট পাঠানো হয়েছে।", reply_markup=back_button())
        context.user_data['state'] = None

def main():
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_profit_job, 'interval', hours=1)
    scheduler.start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_balance))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == '__main__': main()
