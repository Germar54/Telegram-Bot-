import logging
import sqlite3
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# --- সেটিংস ---
API_TOKEN = '8738793331:AAFgPq769kEeUUnUf2X1nkHjYSGE2cbohU4'
ADMIN_ID = 8474225355

# Flask Web Server
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# বট সেটিংস
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class WithdrawState(StatesGroup):
    waiting_for_amount = State()

# ডাটাবেস
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0)")
db.commit()

# --- কীবোর্ড মেনুসমূহ ---

# ১. মেইন মেনু (রিফ্রেশ বাটন নিচে)
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Work start 🔥", "price rules and other")
    keyboard.add("Withdraw")
    keyboard.add("Refresh") # আপনার চাহিদা অনুযায়ী সব নিচে
    return keyboard

# ২. ওয়ার্ক স্টার্ট মেনু (IG 2fa, Ig Mother Account, Refresh)
def work_start_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("IG 2fa", "Ig Mother Account")
    keyboard.add("Refresh") # এই রিফ্রেশ মেইন মেনুতে নিয়ে যাবে
    return keyboard

# ৩. উইথড্র ইনলাইন মেনু (বিকাশ, নগদ, রকেট, বাইনান্স)
def withdraw_inline_menu():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("বিকাশ", callback_data="method_Bikash"),
        types.InlineKeyboardButton("নগদ", callback_data="method_Nagad"),
        types.InlineKeyboardButton("রকেট", callback_data="method_Rocket"),
        types.InlineKeyboardButton("বাইনান্স", callback_data="method_Binance"),
        types.InlineKeyboardButton("উইথড্র করুন 💰", callback_data="conf_withdraw")
    ]
    keyboard.add(*buttons)
    return keyboard

# --- হ্যান্ডলারসমূহ ---

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, message.from_user.username))
    db.commit()
    await message.answer(f"বটে আপনাকে স্বাগতম!\nআপনার আইডি: `{user_id}`", reply_markup=main_menu(), parse_mode="Markdown")

# সমস্যা ১ সমাধান: ওয়ার্ক স্টার্ট বাটনের কাজ
@dp.message_handler(lambda message: message.text == "Work start 🔥")
async def work_start(message: types.Message):
    await message.answer("আপনার কাজের ক্যাটাগরি বেছে নিন:", reply_markup=work_start_menu())

# সমস্যা ৩ সমাধান: রিফ্রেশ বাটনের কাজ (মেইন মেনুতে ফেরা)
@dp.message_handler(lambda message: message.text == "Refresh")
async def refresh_to_main(message: types.Message):
    await message.answer("মেইন মেনুতে ফিরে আসা হয়েছে।", reply_markup=main_menu())

# সমস্যা ২ সমাধান: পেমেন্ট মেথড বাটনের রেসপন্স
@dp.message_handler(lambda message: message.text == "Withdraw")
async def show_withdraw(message: types.Message):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    balance = cursor.fetchone()[0]
    await message.answer(f"💰 বর্তমান ব্যালেন্স: {balance} ৳\nএকটি মেথড সিলেক্ট করুন:", reply_markup=withdraw_inline_menu())

@dp.callback_query_handler(lambda c: c.data.startswith('method_'))
async def payment_method_response(call: types.CallbackQuery):
    method = call.data.split('_')[1]
    await bot.answer_callback_query(call.id)
    await call.message.answer(f"✅ আপনি **{method}** সিলেক্ট করেছেন। উইথড্র করতে 'উইথড্র করুন 💰' বাটনে ক্লিক করুন।", parse_mode="Markdown")

# উইথড্র কনফার্মেশন ও টাকা বিয়োগ (Auto Minus)
@dp.callback_query_handler(text="conf_withdraw")
async def ask_amount(call: types.CallbackQuery):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    balance = cursor.fetchone()[0]
    if balance < 50:
        await bot.answer_callback_query(call.id, "❌ সর্বনিম্ন উইথড্র ৫০ টাকা!", show_alert=True)
    else:
        await call.message.answer("কত টাকা উইথড্র করতে চান? পরিমাণটি লিখুন:")
        await WithdrawState.waiting_for_amount.set()

@dp.message_handler(state=WithdrawState.waiting_for_amount)
async def process_withdraw(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
        balance = cursor.fetchone()[0]
        
        if amount >= 50 and amount <= balance:
            new_balance = balance - amount
            cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, message.from_user.id))
            db.commit()
            
            # এডমিনকে নোটিফিকেশন
            await bot.send_message(ADMIN_ID, f"🔔 **নতুন উইথড্র!**\nআইডি: `{message.from_user.id}`\nপরিমাণ: {amount} ৳", parse_mode="Markdown")
            await message.answer(f"✅ সফল! {amount} ৳ কেটে নেওয়া হয়েছে। বর্তমান ব্যালেন্স: {new_balance} ৳", reply_markup=main_menu())
        else:
            await message.answer("❌ পর্যাপ্ত ব্যালেন্স নেই বা ভুল পরিমাণ।")
        await state.finish()
    except ValueError:
        await message.answer("❌ সংখ্যা লিখুন।")

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
    
