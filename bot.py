import logging
import sqlite3
from flask import Flask
from threading import Thread
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- সেটিংস ---
API_TOKEN = 'YOUR_BOT_TOKEN_HERE' # আপনার টোকেন দিন
ADMIN_ID = 123456789 # আপনার আইডি দিন

# Flask সার্ভার (বট ২৪ ঘণ্টা চালু রাখতে)
app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# বট সেটিংস
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ডাটাবেস সেটআপ
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0)''')
db.commit()

# --- মেইন মেনু বাটন ---
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Work start 🔥", "price rules and other")
    keyboard.add("Withdraw", "Refresh")
    return keyboard

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, message.from_user.username))
    db.commit()
    await message.answer("বটে আপনাকে স্বাগতম!", reply_markup=main_menu())

# --- আপনার কাঙ্ক্ষিত উইথড্র লজিক ---
@dp.message_handler(lambda message: message.text == "Withdraw")
async def withdraw_options(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("বিকাশ", callback_data="w_Bikash"),
        types.InlineKeyboardButton("নগদ", callback_data="w_Nagad"),
        types.InlineKeyboardButton("রকেট", callback_data="w_Rocket"),
        types.InlineKeyboardButton("বাইনান্স", callback_data="w_Binance"),
        types.InlineKeyboardButton("সেভ পেমেন্ট মেথড", callback_data="save_p"),
        types.InlineKeyboardButton("কনফার্ম উইথড্র", callback_data="conf_w")
    ]
    keyboard.add(*buttons)
    
    # ব্যালেন্স চেক
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    res = cursor.fetchone()
    balance = res[0] if res else 0
    await message.answer(f"💰 আপনার বর্তমান ব্যালেন্স: {balance} ৳\nএকটি অপশন বেছে নিন:", reply_markup=keyboard)

# উইথড্র কনফার্ম এবং অটো-মাইনাস লজিক
@dp.callback_query_handler(text="conf_w")
async def process_withdraw(call: types.CallbackQuery):
    user_id = call.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]

    if balance < 50:
        await call.message.answer("❌ আপনার ব্যালেন্স ৫০ টাকার নিচে!")
    else:
        await call.message.answer("আপনার উইথড্র অ্যামাউন্টটি লিখুন (যেমন: ১০০):")
        # এখানে স্টেট ব্যবহার করে অ্যামাউন্ট ইনপুট নেওয়া হবে

# এডমিন দ্বারা ব্যালেন্স অ্যাড করার কমান্ড: /add [ID] [Amount]
@dp.message_handler(commands=['add'])
async def add_bal(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        args = message.get_args().split()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (float(args[1]), int(args[0])))
        db.commit()
        await message.answer("ব্যালেন্স আপডেট হয়েছে!")

if __name__ == '__main__':
    keep_alive() # ২৪ ঘণ্টা চালু রাখার জন্য
    executor.start_polling(dp, skip_updates=True)
