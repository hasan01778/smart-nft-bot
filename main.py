import logging
import sqlite3
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- মালিকের তথ্য ---
TOKEN = '8298395996:AAGNXNlNAbJcnC1GRzFXo1tDKlH-MbsPU98'
ADMIN_ID = 6004236595  # আপনার আইডি
BIKASH_NO = '01619779327'
NAGAD_NO = '01987926484'
SUPPORT_LINK = "https://t.me/snaieliza69"

# --- ডাটাবেজ ---
def init_db():
    conn = sqlite3.connect('smart_nft.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)''')
    conn.commit()
    conn.close()

# --- মেইন মেনু ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("👤 একাউন্ট", callback_data='account')],
        [InlineKeyboardButton("💰 ডিপোজিট", callback_data='deposit'), InlineKeyboardButton("💸 উত্তোলন", callback_data='withdraw')],
        [InlineKeyboardButton("📦 প্যাকেজ", callback_data='packages')],
        [InlineKeyboardButton("📞 সাপোর্ট", url=SUPPORT_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    init_db()
    conn = sqlite3.connect('smart_nft.db')
    if not conn.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,)).fetchone():
        conn.execute("INSERT INTO users (user_id) VALUES (?)", (user.id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"স্বাগতম {user.first_name}!", reply_markup=main_menu())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'deposit':
        await query.edit_message_text(f"💰 বিকাশ/নগদ (P): {BIKASH_NO}\n\nটাকা পাঠানোর পর আপনার TrxID এবং টাকার পরিমাণ এখানে লিখে পাঠান।\n\n(মিনিমাম ১০০০৳)")
        context.user_data['state'] = 'waiting_dep_info'
    
    elif query.data == 'withdraw':
        bd_tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(bd_tz)
        if 12 <= now.hour < 22:
            await query.edit_message_text("💸 কত টাকা তুলতে চান এবং কোন নাম্বারে? বিস্তারিত লিখে পাঠান।")
            context.user_data['state'] = 'waiting_with_info'
        else:
            await query.edit_message_text("❌ উত্তোলন এখন বন্ধ। সকাল ১২টা থেকে রাত ১০টা পর্যন্ত চেষ্টা করুন।")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get('state')

    if state == 'waiting_dep_info':
        # মালিকের কাছে পাঠানো রিপোর্ট
        report = (f"🔔 **নতুন ডিপোজিট রিকোয়েস্ট!**\n\n"
                  f"👤 ইউজার আইডি: `{u_id}`\n"
                  f"📝 তথ্য: {text}\n\n"
                  f"টাকা এড করতে লিখুন:\n`/add {u_id} টাকার_পরিমাণ`")
        
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=report, parse_mode='Markdown')
            # ইউজারকে আপনার পছন্দের মেসেজটি দেখানো হচ্ছে
            await update.message.reply_text("✅ ধন্যবাদ! আপনার তথ্যটি পাওয়া গেছে। কিছুক্ষণের ভেতর চেক করে পেমেন্টটি সফল করা হবে।")
        except:
            await update.message.reply_text("❌ কারিগরি সমস্যা! মালিকের সাথে সরাসরি যোগাযোগ করুন।")
        context.user_data['state'] = None

    elif state == 'waiting_with_info':
        report = (f"💸 **নতুন উত্তোলন রিকোয়েস্ট!**\n\n"
                  f"👤 ইউজার আইডি: `{u_id}`\n"
                  f"📝 তথ্য: {text}")
        await context.bot.send_message(chat_id=ADMIN_ID, text=report, parse_mode='Markdown')
        await update.message.reply_text("✅ ধন্যবাদ! আপনার উত্তোলনের তথ্য পাওয়া গেছে। কিছুক্ষণের ভেতর চেক করে পেমেন্টটি সফল করা হবে।")
        context.user_data['state'] = None

# --- এডমিন কমান্ড ---
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        conn = sqlite3.connect('smart_nft.db')
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ সফল! আইডি {target_id} তে {amount}৳ এড হয়েছে।")
        await context.bot.send_message(chat_id=target_id, text=f"🎉 অভিনন্দন! আপনার একাউন্টে {amount}৳ এড করা হয়েছে।")
    except:
        await update.message.reply_text("ফরম্যাট: `/add আইডি টাকা`")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_balance))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == '__main__':
    main()
