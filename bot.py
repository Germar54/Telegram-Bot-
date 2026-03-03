import logging
import sqlite3
import os
from flask import Flask
from threading import Thread
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# --- সেটিংস (Render Environment থেকে টোকেন নেবে) ---
API_TOKEN = os.getenv('8738793331:AAFgPq769kEeUUnUf2X1nkHjYSGE2cbohU4') 
ADMIN_ID = int(os.getenv('8474225355', '0')) 

# Flask Web Server (২৪ ঘণ্টা চালু রাখতে)
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# বট সেটিংস
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# উইথড্র স্টেট হ্যান্ডলিং
class WithdrawState(StatesGroup):
    waiting_for_amount = State()

# ডাটাবেস সেটআপ (ইউজার ব্যালেন্স সেভ রাখার জন্য)
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0)''')
db.commit()

# --- কীবোর্ড মেনু ---
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
    await message.answer(f"বটে আপনাকে স্বাগতম!\nআপনার আইডি: `{user_id}`", reply_markup=main_menu(), parse_mode="Markdown")

# --- উইথড্র লজিক ---
@dp.message_handler(lambda message: message.text == "Withdraw")
async def withdraw_process(message: types.Message):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    res = cursor.fetchone()
    balance = res[0] if res else 0
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("বিকাশ", callback_data="w_Bikash"),
        types.InlineKeyboardButton("নগদ", callback_data="w_Nagad"),
        types.InlineKeyboardButton("রকেট", callback_data="w_Rocket"),
        types.InlineKeyboardButton("বাইনান্স", callback_data="w_Binance"),
        types.InlineKeyboardButton("সেভ পেমেন্ট মেথড", callback_data="save_p"),
        types.InlineKeyboardButton("উইথড্র করুন 💰", callback_data="conf_withdraw")
    ]
    keyboard.add(*buttons)
    await message.answer(f"💰 বর্তমান ব্যালেন্স: {balance} ৳\nউইথড্র করার জন্য মেথড বেছে নিন:", reply_markup=keyboard)

# উইথড্র বাটন ক্লিক করলে
@dp.callback_query_handler(text="conf_withdraw")
async def ask_amount(call: types.CallbackQuery):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    balance = cursor.fetchone()[0]
    
    if balance < 50:
        await bot.answer_callback_query(call.id, "❌ সর্বনিম্ন উইথড্র ৫০ টাকা!", show_alert=True)
    else:
        await call.message.answer("আপনি কত টাকা উইথড্র করতে চান? পরিমাণটি লিখুন (যেমন: ১০০):")
        await WithdrawState.waiting_for_amount.set()

# অটো-মাইনাস এবং এডমিন নোটিফিকেশন
@dp.message_handler(state=WithdrawState.waiting_for_amount)
async def final_payout(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        user_id = message.from_user.id
        
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]
        
        if amount < 50:
            await message.answer("❌ সর্বনিম্ন ৫০ টাকা দিতে হবে।")
        elif amount > balance:
            await message.answer(f"❌ ব্যালেন্স নেই! আপনার আছে {balance} ৳।")
        else:
            # টাকা বিয়োগ করা (Auto Minus)
            new_balance = balance - amount
            cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
            db.commit()
            
            # এডমিনকে তথ্য পাঠানো
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            admin_text = (f"🔔 **নতুন উইথড্র রিকোয়েস্ট**\n\n"
                          f"👤 ইউজার: @{message.from_user.username}\n"
                          f"🆔 আইডি: `{user_id}`\n"
                          f"💵 পরিমাণ: {amount} ৳\n"
                          f"📅 তারিখ: {now}")
            
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
            await message.answer(f"✅ সফলভাবে {amount} ৳ উইথড্র রিকোয়েস্ট পাঠানো হয়েছে। আপনার বর্তমান ব্যালেন্স: {new_balance} ৳")
            
        await state.finish()
    except ValueError:
        await message.answer("❌ দয়া করে শুধু সংখ্যা লিখুন।")

# এডমিন দ্বারা ব্যালেন্স অ্যাড করার কমান্ড: /add [ID] [Amount]
@dp.message_handler(commands=['add'])
async def add_money(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            args = message.get_args().split()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (float(args[1]), int(args[0])))
            db.commit()
            await message.answer("ব্যালেন্স আপডেট করা হয়েছে!")
        except:
            await message.answer("সঠিক ফরম্যাট: `/add ইউজার_আইডি পরিমাণ`", parse_mode="Markdown")

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
    
