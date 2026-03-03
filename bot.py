import logging
import sqlite3
import os
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ==========================================
# ১. সেটিংস ও কানেকশন (Settings)
# ==========================================
API_TOKEN = '8738793331:AAFgPq769kEeUUnUf2X1nkHjYSGE2cbohU4'
ADMIN_ID = 8474225355

# ২৪ ঘণ্টা চালু রাখার জন্য Flask Server
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# বট ও মেমোরি সেটআপ
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ডাটাবেস সেটআপ
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, payment_method TEXT, payment_address TEXT)''')
db.commit()

# স্টেট ম্যানেজমেন্ট
class BotState(StatesGroup):
    waiting_for_file = State()
    waiting_for_payment_address = State()
    waiting_for_withdraw_amount = State()

# ==========================================
# ২. কিবোর্ড মেনু (Keyboards)
# ==========================================
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Work start 🔥", "Withdraw")
    keyboard.add("Refresh")
    return keyboard

def work_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("IG 2fa", "IG Mother Account")
    keyboard.add("Refresh")
    return keyboard

# ==========================================
# ৩. মেইন মেনু বাটনের কাজ (Main Logic)
# ==========================================

# --- START COMMAND ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, message.from_user.username))
    db.commit()
    await message.answer(f"বটে স্বাগতম! আপনার আইডি: `{user_id}`", reply_markup=main_menu(), parse_mode="Markdown")

# --- WORK START BUTTON ---
@dp.message_handler(lambda message: message.text == "Work start 🔥")
async def work_start(message: types.Message):
    await message.answer("আপনার কাজের ক্যাটাগরি বেছে নিন:", reply_markup=work_menu())

@dp.message_handler(lambda message: message.text in ["IG 2fa", "IG Mother Account"])
async def ask_file(message: types.Message, state: FSMContext):
    await state.update_data(work_type=message.text)
    await message.answer(f"✅ আপনি {message.text} বেছে নিয়েছেন। এখন আপনার Excel ফাইলটি পাঠান।")
    await BotState.waiting_for_file.set()

# ফাইল হ্যান্ডলিং (এডমিন প্যানেলে যাবে)
@dp.message_handler(content_types=['document'], state=BotState.waiting_for_file)
async def handle_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("SELECT payment_method, payment_address FROM users WHERE user_id=?", (message.from_user.id,))
    res = cursor.fetchone()
    p_info = f"{res[0]}: {res[1]}" if res[0] else "পেমেন্ট তথ্য যোগ করা হয়নি"

    caption = (f"📩 **নতুন ফাইল জমা!**\n\n🆔 আইডি: `{message.from_user.id}`\n📂 টাইপ: {data['work_type']}\n💳 পেমেন্ট: {p_info}")
    await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, parse_mode="Markdown")
    await message.answer("✅ আপনার ফাইলটি এডমিন প্যানেলে পাঠানো হয়েছে।", reply_markup=main_menu())
    await state.finish()

# ==========================================
# ৪. উইথড্র বাটন লজিক (Withdrawal)
# ==========================================
@dp.message_handler(lambda message: message.text == "Withdraw")
async def withdraw_section(message: types.Message):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    balance = cursor.fetchone()[0]
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("বিকাশ", callback_data="set_Bikash"),
        types.InlineKeyboardButton("নগদ", callback_data="set_Nagad"),
        types.InlineKeyboardButton("রকেট", callback_data="set_Rocket"),
        types.InlineKeyboardButton("বাইনান্স", callback_data="set_Binance"),
        types.InlineKeyboardButton("Save Payment Method", callback_data="set_Save"),
        types.InlineKeyboardButton("Withdraw 💰", callback_data="init_withdraw")
    )
    await message.answer(f"💰 বর্তমান ব্যালেন্স: {balance} ৳\nপেমেন্ট মেথড সেট করুন অথবা উইথড্র দিন:", reply_markup=keyboard)

# পেমেন্ট এড্রেস সেভ করা
@dp.callback_query_handler(lambda c: c.data.startswith('set_'))
async def set_payment(call: types.CallbackQuery, state: FSMContext):
    if call.data == "set_Save":
        await call.message.answer("আগে উপরের যেকোনো একটি মেথড (বিকাশ/নগদ/বাইনান্স) সিলেক্ট করে নম্বর দিন।")
        return
    method = call.data.split('_')[1]
    await state.update_data(temp_method=method)
    await call.message.answer(f"আপনার {method} নম্বর বা এড্রেসটি লিখে সেন্ড করুন:")
    await BotState.waiting_for_payment_address.set()

@dp.message_handler(state=BotState.waiting_for_payment_address)
async def save_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("UPDATE users SET payment_method=?, payment_address=? WHERE user_id=?", 
                   (data['temp_method'], message.text, message.from_user.id))
    db.commit()
    await message.answer(f"✅ সফল! আপনার {data['temp_method']} এড্রেস সেভ হয়েছে।", reply_markup=main_menu())
    await state.finish()

# উইথড্র রিকোয়েস্ট (Auto-Minus)
@dp.callback_query_handler(text="init_withdraw")
async def process_withdraw_init(call: types.CallbackQuery):
    cursor.execute("SELECT balance, payment_address FROM users WHERE user_id=?", (call.from_user.id,))
    res = cursor.fetchone()
    if not res[1]: 
        await call.message.answer("❌ আপনার পেমেন্ট এড্রেস সেভ করা নেই! আগে মেথড সেট করুন।")
    elif res[0] < 50:
        await call.message.answer("❌ আপনি ৫০ টাকার নিচে উইথড্র করতে পারবেন না।")
    else:
        await call.message.answer("আপনার উইথড্র পরিমাণ লিখুন (কমপক্ষে ৫০):")
        await BotState.waiting_for_withdraw_amount.set()

@dp.message_handler(state=BotState.waiting_for_withdraw_amount)
async def withdraw_final(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        cursor.execute("SELECT balance, payment_method, payment_address FROM users WHERE user_id=?", (message.from_user.id,))
        res = cursor.fetchone()
        
        if amount < 50: await message.answer("❌ ৫০ টাকার নিচে উইথড্র সম্ভব নয়।")
        elif amount > res[0]: await message.answer("❌ পর্যাপ্ত ব্যালেন্স নেই।")
        else:
            # টাকা বিয়োগ করা
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, message.from_user.id))
            db.commit()
            # এডমিনকে জানানো
            await bot.send_message(ADMIN_ID, f"💰 **উইথড্র রিকোয়েস্ট!**\n🆔 আইডি: `{message.from_user.id}`\n💵 পরিমাণ: {amount} ৳\n💳 মেথড: {res[1]}\n📍 এড্রেস: {res[2]}")
            await message.answer(f"✅ উইথড্র সফল! রিকোয়েস্ট এডমিন প্যানেলে পাঠানো হয়েছে।")
        await state.finish()
    except: await message.answer("❌ ভুল ইনপুট! শুধু সংখ্যা লিখুন।")

# ==========================================
# ৫. রিফ্রেশ ও অতিরিক্ত কমান্ড (Extra)
# ==========================================
@dp.message_handler(lambda message: message.text == "Refresh")
async def refresh(message: types.Message):
    await message.answer("মেইন মেনু রিফ্রেশ করা হয়েছে।", reply_markup=main_menu())

# এডমিন ব্যালেন্স অ্যাড কমান্ড: /add [ID] [Amount]
@dp.message_handler(commands=['add'])
async def add_money(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            args = message.get_args().split()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (float(args[1]), int(args[0])))
            db.commit()
            await message.answer("✅ ব্যালেন্স আপডেট হয়েছে!")
        except: await message.answer("ফরম্যাট: `/add আইডি পরিমাণ`")

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
