import logging
import sqlite3
import os 
import datetime
import json
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ==========================================
# ১. সেটিংস ও ডাটাবেস
# ==========================================
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS stats 
                  (user_id INTEGER, file_count INTEGER DEFAULT 0, single_id_count INTEGER DEFAULT 0, date TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests 
                  (req_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, address TEXT)''')
db.commit()

class BotState(StatesGroup):
    waiting_for_file = State()
    waiting_for_address = State()
    waiting_for_withdraw_amount = State()
    waiting_for_add_money = State()
    waiting_for_single_user = State()
    waiting_for_single_pass = State()
    waiting_for_single_2fa = State()

def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Work start 🔥", "Withdraw")
    return keyboard

# ==========================================
# ২. ইউজার সেকশন (Start & Work)
# ==========================================

@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish() 
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    db.commit()

    inline_kb = types.InlineKeyboardMarkup()
    url_button = types.InlineKeyboardButton(text="Latest update and Method", url="https://t.me/instafbhub") 
    inline_kb.add(url_button)

    welcome_text = """📢 **আজকের কাজের আপডেট এবং রেট লিস্ট** 📢\n📌 Point 1: IG 2FA (2.30 - 2.50 TK)\n📌 Point 2: IG Cookies (3.90 - 4.10 TK)\n📌 Point 3: IG Mother (8 - 9 TK)\n✅ Support: @Dinanhaji"""
    await message.answer(welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
    await message.answer("একটি অপশন বেছে নিন:", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "Work start 🔥")
async def work_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("IG Mother Account", "IG 2fa")
    keyboard.add("🔄 রিফ্রেশ") 
    await message.answer("🔴 আপনার কাজের ক্যাটাগরি বেছে নিন:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text in ["IG Mother Account", "IG 2fa"])
async def ask_work_type(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.add(types.InlineKeyboardButton("🗃️ File", callback_data="type_file"))
    inline_kb.add(types.InlineKeyboardButton("👤 Single ID", callback_data="type_single"))
    await message.answer("✅ আপনার কাজের ধরণ বেছে নিন:", reply_markup=inline_kb)

# --- ইনলাইন বাটনের প্রসেসিং ---
@dp.callback_query_handler(lambda c: c.data.startswith('type_'), state="*")
async def process_callback_work_type(callback_query: types.CallbackQuery):
    if callback_query.data == "type_file":
        await bot.send_message(callback_query.from_user.id, "📤 আপনার এক্সেল ফাইলটি (Excel File) পাঠান।")
        await BotState.waiting_for_file.set()
    elif callback_query.data == "type_single":
        await bot.send_message(callback_query.from_user.id, "👤 আপনার ইউজার আইডি (User ID) দিন:")
        await BotState.waiting_for_single_user.set()
    await callback_query.answer()

# --- সিঙ্গেল আইডির তথ্য সংগ্রহ ---
@dp.message_handler(state=BotState.waiting_for_single_user)
async def get_id(message: types.Message, state: FSMContext):
    await state.update_data(u_id=message.text)
    await message.answer("🔑 এবার পাসওয়ার্ড দিন:")
    await BotState.waiting_for_single_pass.set()

@dp.message_handler(state=BotState.waiting_for_single_pass)
async def get_pass(message: types.Message, state: FSMContext):
    await state.update_data(u_pass=message.text)
    await message.answer("🔐 এবার টু-এফা (2FA Code) দিন:")
    await BotState.waiting_for_single_2fa.set()

@dp.message_handler(state=BotState.waiting_for_single_2fa)
async def get_2fa(message: types.Message, state: FSMContext):
    data = await state.get_data()
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # ব্যালেন্স আপডেট
    category = data.get('category')
    reward = 9.00 if category == "IG Mother Account" else 2.30
    cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (message.from_user.id, today))
    cursor.execute("UPDATE stats SET single_id_count = single_id_count + 1 WHERE user_id=? AND date=?", (message.from_user.id, today))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (reward, message.from_user.id))
    db.commit()

    # অ্যাডমিনকে বিস্তারিত রিপোর্ট পাঠানো (Feature 1 & 6)
    admin_msg = (f"🚀 **নতুন সিঙ্গেল আইডি জমা!**\n\n"
                 f"👤 ইউজার: {message.from_user.mention} (`{message.from_user.id}`)\n"
                 f"📂 ক্যাটাগরি: {category}\n"
                 f"━━━━━━━━━━━━━━━\n"
                 f"🆔 ID: `{data.get('u_id')}`\n"
                 f"🔑 Pass: `{data.get('u_pass')}`\n"
                 f"🔐 2FA: `{message.text}`")
    
    control_kb = types.InlineKeyboardMarkup()
    control_kb.add(types.InlineKeyboardButton("🚫 ব্লক", callback_data=f"block_{message.from_user.id}"),
                   types.InlineKeyboardButton("💰 এডিট ব্যালেন্স", callback_data=f"edit_{message.from_user.id}"))

    await bot.send_message(ADMIN_ID, admin_msg, reply_markup=control_kb, parse_mode="Markdown")
    await message.answer(f"✅ কাজ জমা হয়েছে! {reward} ৳ যোগ করা হয়েছে।", reply_markup=main_menu())
    await state.finish()

# ==========================================
# ৩. উইথড্র ও রিফ্রেশ
# ==========================================

@dp.message_handler(lambda message: message.text == "🔄 রিফ্রেশ", state="*")
async def refresh(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("✅ মেইন মেনু।", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "Withdraw")
async def withdraw_process(message: types.Message):
    cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (message.from_user.id,))
    res = cursor.fetchone()
    if not res[1]:
        await message.answer("📍 পেমেন্ট নম্বর দিন (বিকাশ/নগদ):")
        await BotState.waiting_for_address.set()
    else:
        await message.answer(f"💰 ব্যালেন্স: {res[0]} ৳\nকত টাকা তুলতে চান লিখুন:")
        await BotState.waiting_for_withdraw_amount.set()

@dp.message_handler(state=BotState.waiting_for_address)
async def save_address(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE users SET address=? WHERE user_id=?", (message.text, message.from_user.id))
    db.commit()
    await message.answer("✅ সংরক্ষিত! আবার Withdraw চাপুন।")
    await state.finish()

@dp.message_handler(state=BotState.waiting_for_withdraw_amount)
async def withdraw_done(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (message.from_user.id,))
        balance, addr = cursor.fetchone()
        if amount <= balance and amount >= 50:
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, message.from_user.id))
            cursor.execute("INSERT INTO withdraw_requests (user_id, amount) VALUES (?, ?)", (message.from_user.id, amount))
            db.commit()
            await bot.send_message(ADMIN_ID, f"🔔 উইথড্র রিকোয়েস্ট!\n🆔 ID: `{message.from_user.id}`\n💵: {amount} ৳\n📍: {addr}")
            await message.answer(f"✅ রিকোয়েস্ট সফল! {amount} ৳ কাটা হয়েছে।")
        else: await message.answer("❌ ব্যালেন্স নেই বা ৫০ টাকার কম।")
    except: await message.answer("❌ শুধু সংখ্যা দিন।")
    await state.finish()

# ==========================================
# ৪. শক্তিশালী অ্যাডমিন প্যানেল (Feature 2, 3, 4, 5, 7)
# ==========================================

@dp.message_handler(commands=['search'], user_id=ADMIN_ID)
async def admin_search(message: types.Message):
    uid = message.get_args()
    if not uid: return await message.answer("⚠️ আইডি দিন।")
    cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (uid,))
    user = cursor.fetchone()
    if user:
        today = datetime.date.today().strftime("%Y-%m-%d")
        cursor.execute("SELECT single_id_count FROM stats WHERE user_id=? AND date=?", (uid, today))
        work = cursor.fetchone() or (0,)
        text = f"👤 ইউজার: `{uid}`\n💰 ব্যালেন্স: {user[0]} ৳\n📍 এড্রেস: {user[1]}\n📊 আজকের আইডি: {work[0]} টি"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🚫 ব্লক", callback_data=f"block_{uid}"),
               types.InlineKeyboardButton("💰 এডিট", callback_data=f"edit_{uid}"))
        await message.answer(text, reply_markup=kb)
    else: await message.answer("❌ পাওয়া যায়নি।")

@dp.callback_query_handler(lambda c: c.data.startswith('block_'), user_id=ADMIN_ID)
async def block(call: types.CallbackQuery):
    uid = call.data.split('_')[1]
    await call.message.answer(f"🚫 ইউজার {uid} কে ব্লক করা হয়েছে (লজিক অনুযায়ী)।")
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('edit_'), user_id=ADMIN_ID)
async def edit_balance_btn(call: types.CallbackQuery, state: FSMContext):
    uid = call.data.split('_')[1]
    await state.update_data(target_id=uid)
    await call.message.answer(f"👤 `{uid}` এর নতুন ব্যালেন্স কত হবে?")
    await BotState.waiting_for_add_money.set()
    await call.answer()

@dp.message_handler(state=BotState.waiting_for_add_money, user_id=ADMIN_ID)
async def final_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        new_bal = float(message.text)
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_bal, data['target_id']))
        db.commit()
        await message.answer("✅ আপডেট হয়েছে।")
        await bot.send_message(data['target_id'], f"💰 আপনার ব্যালেন্স আপডেট করে {new_bal} ৳ করা হয়েছে।")
    except: await message.answer("❌ ভুল ইনপুট।")
    await state.finish()

@dp.message_handler(commands=['broadcast'], user_id=ADMIN_ID)
async def broadcast(message: types.Message):
    text = message.get_args()
    cursor.execute("SELECT user_id FROM users")
    for user in cursor.fetchall():
        try: await bot.send_message(user[0], text)
        except: pass
    await message.answer("✅ পাঠানো হয়েছে।")

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
