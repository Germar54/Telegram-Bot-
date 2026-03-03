import logging
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from datetime import datetime

# --- সেটিংস ---
API_TOKEN = '8738793331:AAFgPq769kEeUUnUf2X1nkHjYSGE2cbohU4'  # এখানে আপনার বট টোকেন দিন
ADMIN_ID = 8474225355  # এখানে আপনার নিজের টেলিগ্রাম আইডি দিন (সংখ্যায়)

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO)

# বট এবং স্টোরেজ ইনিশিয়ালাইজেশন
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- ডাটাবেস সেটআপ ---
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, payment_method TEXT, payment_address TEXT)''')
db.commit()

# --- কীবোর্ড বাটন (Main Menu) ---
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Work start 🔥", "price rules and other")
    keyboard.add("Withdraw", "Refresh")
    return keyboard

# উইথড্র সাব-মেনু
def withdraw_menu():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("বিকাশ", callback_data="method_Bikash"),
        types.InlineKeyboardButton("নগদ", callback_data="method_Nagad"),
        types.InlineKeyboardButton("রকেট", callback_data="method_Rocket"),
        types.InlineKeyboardButton("বাইনান্স", callback_data="method_Binance"),
        types.InlineKeyboardButton("Save Payment Method", callback_data="save_method"),
        types.InlineKeyboardButton("Withdraw 💰", callback_data="confirm_withdraw")
    ]
    keyboard.add(*buttons)
    return keyboard

# --- কমান্ড হ্যান্ডলার ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    
    # নতুন ইউজার হলে ডাটাবেসে যোগ করা
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    db.commit()
    
    await message.answer(f"স্বাগতম! আপনার আইডি: `{user_id}`\nকাজ শুরু করতে নিচের বাটন চাপুন।", 
                         reply_markup=main_menu(), parse_mode="Markdown")

# উইথড্র বাটনে ক্লিক করলে
@dp.message_handler(lambda message: message.text == "Withdraw")
async def show_withdraw_options(message: types.Message):
    await message.answer("আপনার পেমেন্ট মেথড সিলেক্ট করুন অথবা উইথড্র রিকোয়েস্ট পাঠান:", reply_markup=withdraw_menu())

# পেমেন্ট মেথড হ্যান্ডলার (বিকাশ/নগদ ইত্যাদি)
@dp.callback_query_handler(lambda c: c.data.startswith('method_'))
async def set_method(callback_query: types.CallbackQuery):
    method_name = callback_query.data.split("_")[1]
    # সাময়িকভাবে মেমোরিতে মেথড সেভ করা
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"আপনার {method_name} নাম্বারটি লিখে সেন্ড করুন।")
    # এখানে FSM ব্যবহার করে স্টেট সেভ করা উচিত, সংক্ষেপে আমরা মেসেজ হ্যান্ডলারে ধরবো

# সেভ পেমেন্ট মেথড লজিক (সরাসরি এডমিনকে পাঠানো)
@dp.callback_query_handler(text="save_method")
async def save_process(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    date = datetime.now().strftime("%d/%m/%Y")
    
    await bot.send_message(ADMIN_ID, f"🔔 **পেমেন্ট মেথড সেভ রিকোয়েস্ট**\nইউজার: @{username}\nআইডি: `{user_id}`\nতারিখ: {date}", parse_mode="Markdown")
    await bot.answer_callback_query(callback_query.id, "তথ্য এডমিন প্যানেলে পাঠানো হয়েছে।")

# উইথড্র বাটন (মেইন লজিক)
@dp.callback_query_handler(text="confirm_withdraw")
async def final_withdraw(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    # ডাটাবেস থেকে ব্যালেন্স চেক
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    balance = res[0] if res else 0
    
    if balance < 50:
        await bot.send_message(user_id, f"❌ দুঃখিত! আপনার ব্যালেন্স মাত্র {balance} ৳।\nউইথড্র করতে কমপক্ষে ৫০ ৳ প্রয়োজন।")
    else:
        await bot.send_message(user_id, f"✅ আপনার বর্তমান ব্যালেন্স: {balance} ৳।\nকত টাকা উইথড্রো করতে চান তা লিখে পাঠান।")

# এডমিন দ্বারা ব্যালেন্স এডিট করার কমান্ড (উদাহরণ: /add 1234567 100)
@dp.message_handler(commands=['add'])
async def add_balance(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        args = message.get_args().split()
        if len(args) == 2:
            u_id, amount = args
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (float(amount), int(u_id)))
            db.commit()
            await message.answer(f"ইউজার `{u_id}` এর ব্যালেন্সে {amount} ৳ যোগ করা হয়েছে।")

# --- বট স্টার্ট ---
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
