import logging
import sqlite3
import os 
import datetime
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

# ডাটাবেস টেবিল তৈরি
cursor.execute('''CREATE TABLE IF NOT EXISTS stats 
                  (user_id INTEGER, file_count INTEGER DEFAULT 0, single_id_count INTEGER DEFAULT 0, date TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, address TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)''')
db.commit()

# ==========================================
# ২. স্টেট ক্লাস (FSM)
# ==========================================
class BotState(StatesGroup):
    waiting_for_file = State()
    waiting_for_address = State()
    waiting_for_withdraw_amount = State()
    waiting_for_add_money = State()
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_2fa = State()
    waiting_for_block_reason = State()

# ব্লক চেক করার ফাংশন
async def is_blocked(user_id):
    cursor.execute("SELECT user_id FROM blacklist WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Work start 🔥", "Withdraw")
    keyboard.add("🔄 রিফ্রেশ")
    return keyboard

# ==========================================
# ৩. কমান্ড ও হ্যান্ডলার
# ==========================================

@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish() 
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    db.commit()

    inline_kb = types.InlineKeyboardMarkup()
    url_button = types.InlineKeyboardButton(text="Latest update and Method", url="https://t.me/instafbhub") 
    inline_kb.add(url_button)

    welcome_text = """📢 **আজকের কাজের আপডেট এবং রেট লিস্ট** 📢
📌 **Instagram 00 Follower (2FA):** ২.৩০ ৳
📌 **Instagram Cookies:** ৩.৯০ ৳
📌 **Instagram Mother:** ৮-৯ ৳
📌 **Facebook FBc00Fnd:** ৫.৮০ ৳

**Support:** @Dinanhaji"""

    await message.answer(welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
    await message.answer("একটি অপশন বেছে নিন:", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "Work start 🔥")
async def work_start(message: types.Message):
    if await is_blocked(message.from_user.id):
        return await message.answer("❌ আপনি ব্লকড থাকার কারণে কাজ জমা দিতে পারবেন না।")
    
    inline_kb = types.InlineKeyboardMarkup(row_width=2)
    inline_kb.add(
        types.InlineKeyboardButton("📸 IG Mother Account", callback_data="type_ig_mother"),
        types.InlineKeyboardButton("🔐 IG 2fa", callback_data="type_ig_2fa"),
        types.InlineKeyboardButton("🔵 FB 0fnd 2fa", callback_data="type_fb_2fa"),
        types.InlineKeyboardButton("🍪 IG Cookies", callback_data="type_ig_cookies")
    )
    await message.answer("🔴 আপনার কাজের ক্যাটাগরি বেছে নিন:", reply_markup=inline_kb)

@dp.callback_query_handler(lambda c: c.data.startswith('type_'))
async def process_work_type(callback_query: types.CallbackQuery, state: FSMContext):
    category_map = {
        "type_ig_mother": "IG Mother Account",
        "type_ig_2fa": "IG 2fa",
        "type_fb_2fa": "FB 0fnd 2fa",
        "type_ig_cookies": "IG Cookies"
    }
    selected = category_map.get(callback_query.data)
    await state.update_data(category=selected)
    
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.add(types.InlineKeyboardButton("📁 File", callback_data="ask_for_file"))
    inline_kb.add(types.InlineKeyboardButton("👤 Single ID", callback_data="ask_for_single"))
    
    await bot.send_message(callback_query.from_user.id, f"✅ আপনি **{selected}** বেছে নিয়েছেন। কাজের ধরণ দিন:", reply_markup=inline_kb)
    await bot.answer_callback_query(callback_query.id)

# --- ফাইল জমা দেওয়া ---
@dp.callback_query_handler(lambda c: c.data == 'ask_for_file')
async def ask_for_file(call: types.CallbackQuery):
    await bot.send_message(call.from_user.id, "📤 আপনার এক্সেল ফাইলটি পাঠান:")
    await BotState.waiting_for_file.set()
    await call.answer()

@dp.message_handler(content_types=['document'], state=BotState.waiting_for_file)
async def handle_file(message: types.Message, state: FSMContext):
    today = datetime.date.today().strftime("%Y-%m-%d")
    cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (message.from_user.id, today))
    cursor.execute("UPDATE stats SET file_count = file_count + 1 WHERE user_id=? AND date=?", (message.from_user.id, today))
    db.commit()

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Add Money 💰", callback_data=f"adminadd_{message.from_user.id}"))
    
    await bot.send_document(ADMIN_ID, message.document.file_id, 
                           caption=f"📩 নতুন ফাইল!\n👤 আইডি: `{message.from_user.id}`", 
                           reply_markup=keyboard, parse_mode="Markdown")
    
    await message.answer("✅ ফাইল জমা হয়েছে। এডমিন চেক করে ব্যালেন্স দিয়ে দিবে।", reply_markup=main_menu())
    await state.finish()

# --- সিঙ্গেল আইডি জমা দেওয়া (ধাপে ধাপে) ---
@dp.callback_query_handler(lambda c: c.data == 'ask_for_single')
async def ask_single(call: types.CallbackQuery):
    await bot.send_message(call.from_user.id, "👤 আপনার **Username** দিন:")
    await BotState.waiting_for_username.set()
    await call.answer()

@dp.message_handler(state=BotState.waiting_for_username)
async def get_username(message: types.Message, state: FSMContext):
    await state.update_data(u_id=message.text)
    await message.answer("🔑 এবার আপনার **Password** দিন:")
    await BotState.waiting_for_password.set()

@dp.message_handler(state=BotState.waiting_for_password)
async def get_password(message: types.Message, state: FSMContext):
    await state.update_data(u_pass=message.text)
    await message.answer("🔐 এবার **2FA Code** দিন:")
    await BotState.waiting_for_2fa.set()

@dp.message_handler(state=BotState.waiting_for_2fa)
async def get_2fa_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    admin_msg = (f"🚀 **নতুন সিঙ্গেল আইডি!**\n\n"
                 f"👤 আইডি: `{message.from_user.id}`\n"
                 f"📂 ক্যাটাগরি: {data.get('category')}\n"
                 f"🆔 ID: `{data.get('u_id')}`\n"
                 f"🔑 Pass: `{data.get('u_pass')}`\n"
                 f"🔐 2FA: `{message.text}`")
    
    cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (message.from_user.id, today))
    cursor.execute("UPDATE stats SET single_id_count = single_id_count + 1 WHERE user_id=? AND date=?", (message.from_user.id, today))
    db.commit()
    
    await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    await message.answer("✅ আপনার তথ্য জমা হয়েছে।", reply_markup=main_menu())
    await state.finish()

# --- উইথড্র লজিক ---
@dp.message_handler(lambda message: message.text == "Withdraw")
async def withdraw(message: types.Message):
    cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (message.from_user.id,))
    res = cursor.fetchone()
    balance, address = res[0], res[1]

    if not address:
        await message.answer("💌 পেমেন্ট মেথড দিন (বিকাশ/নগদ/বাইনান্স):")
        await BotState.waiting_for_address.set()
    else:
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Change Method ⚙️", callback_data="change_method"))
        await message.answer(f"💰 ব্যালেন্স: {balance} ৳\n📍 এড্রেস: {address}\n\nউইথড্র পরিমাণ লিখুন (মিনিমাম ৫০):", reply_markup=kb)
        await BotState.waiting_for_withdraw_amount.set()

@dp.message_handler(state=BotState.waiting_for_address)
async def save_addr(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE users SET address=? WHERE user_id=?", (message.text, message.from_user.id))
    db.commit()
    await message.answer("✅ এড্রেস সেভ হয়েছে। এখন Withdraw বাটনে ক্লিক করুন।")
    await state.finish()

@dp.message_handler(state=BotState.waiting_for_withdraw_amount)
async def process_withdraw(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (message.from_user.id,))
        balance, addr = cursor.fetchone()
        if amount < 50 or amount > balance:
            await message.answer("❌ ভুল পরিমাণ বা পর্যাপ্ত ব্যালেন্স নেই।")
        else:
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, message.from_user.id))
            db.commit()
            await bot.send_message(ADMIN_ID, f"🔔 উইথড্র রিকোয়েস্ট!\n🆔 `{message.from_user.id}`\n💵 {amount} ৳\n📍 {addr}")
            await message.answer(f"✅ উইথড্র সফল! {amount} ৳ কেটে নেওয়া হয়েছে।")
        await state.finish()
    except: await message.answer("❌ সংখ্যা লিখুন।")

# --- রিফ্রেশ ---
@dp.message_handler(lambda message: message.text == "🔄 রিফ্রেশ", state="*")
async def refresh(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("✅ মেনু রিফ্রেশ করা হয়েছে।", reply_markup=main_menu())

# --- এডমিন কমান্ডস ---
@dp.message_handler(commands=['search'], user_id=ADMIN_ID)
async def search(message: types.Message):
    uid = message.get_args()
    cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (uid,))
    u = cursor.fetchone()
    if u: await message.answer(f"🆔 `{uid}`\n💰 ব্যালেন্স: {u[0]}\n📍 এড্রেস: {u[1]}")
    else: await message.answer("❌ নেই।")

@dp.message_handler(commands=['block'], user_id=ADMIN_ID)
async def block(message: types.Message):
    uid = message.get_args()
    cursor.execute("INSERT OR IGNORE INTO blacklist VALUES (?)", (uid,))
    db.commit()
    await message.answer(f"🚫 {uid} ব্লক।")

@dp.message_handler(commands=['unblock'], user_id=ADMIN_ID)
async def unblock(message: types.Message):
    uid = message.get_args()
    cursor.execute("DELETE FROM blacklist WHERE user_id=?", (uid,))
    db.commit()
    await message.answer(f"✅ {uid} আনব্লক।")

@dp.callback_query_handler(lambda c: c.data.startswith('adminadd_'))
async def admin_add_money(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(target_id=call.data.split('_')[1])
    await call.message.answer("কত টাকা যোগ করবেন?")
    await BotState.waiting_for_add_money.set()

@dp.message_handler(state=BotState.waiting_for_add_money)
async def save_money(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        data = await state.get_data()
        amount, uid = float(message.text), data['target_id']
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
        db.commit()
        await bot.send_message(uid, f"✅ আপনার ব্যালেন্সে {amount} ৳ যোগ হয়েছে।")
        await message.answer("✅ সফল।")
        await state.finish()

# ==========================================
# ৪. রান করা
# ==========================================
if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
