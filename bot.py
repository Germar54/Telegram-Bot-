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
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, address TEXT)''')
db.commit()

class BotState(StatesGroup):
    waiting_for_file = State()
    waiting_for_address = State()
    waiting_for_withdraw_amount = State()
    waiting_for_add_money = State()

def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Work start 🔥", "Withdraw")
    return keyboard
# /start কমান্ডে মেইন মেনু ও ফ্রী ফায়ার বাটন
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish() 
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    db.commit()

    # ১. এখানে বাটন তৈরি হচ্ছে
    inline_kb = types.InlineKeyboardMarkup()
    
    # নিচের লাইনে 'url' এর জায়গায় আপনার গ্রুপের লিংক বসান
    url_button = types.InlineKeyboardButton(text="All Method And Update", url="https://t.me/your_group_link") 
    inline_kb.add(url_button)

    # ২. এখানে আপনার মেসেজটি লিখুন (লাইন ব্রেক বা ইন্টার দিতে \n ব্যবহার করুন)
    welcome_text = "যদদৎ\n্যধৃ\n\nবটে স্বাগতম! নিচের বাটনে ক্লিক করুন।"
    
    # ৩. মেসেজ পাঠানো হচ্ছে (বাটনসহ)
    await message.answer(welcome_text, reply_markup=inline_kb)
    
    # ৪. মেইন মেনু (Work Start/Withdraw) দেখানো
    await message.answer("📢 **আজকের কাজের আপডেট এবং রেট লিস্ট** 📢\n**নিচের পয়েন্টগুলো মনোযোগ দিয়ে পড়ুন এবং নিয়ম মেনে কাজ সাবমিট করুন।**\n\n📌 `**পয়েন্ট ১: 📸 Instagram 00 Follower (2FA)**\n\n💸 **প্রাইস:** প্রতি পিস ২.৩০ টাকা (১০০+ হলে ২.৫০ টাকা)\n\n⚠️ **নিয়ম:** * 🚫 Resell ID Not Allowed.\n\n❌ **পাসওয়ার্ডের শেষে কোনো তারিখ দেওয়া যাবে না।**\n\n📄 **শীট ফরম্যাট:** User-pass-2fa\n\n⏰ **আইডি সাবমিট লাস্ট টাইম:** রাত ০৮:১৫ মিনিট।`\n\n`📌 **পয়েন্ট ২: 📸 Instagram Cookies 00 Follower**\n\n💸 **প্রাইস:** প্রতি পিস ৩.৯০ টাকা (১০০+ হলে ৪.১০ টাকা)\n\n⚠️ **নিয়ম:** * ⚡ আইডি করার সাথে সাথে সাবমিট দিতে হবে।\n\n.⏳ **২০ মিনিট পার হয়ে গেলে সাবমিট নেওয়া হবে না।**\n\n📄 **শীট ফরম্যাট:** User-pass\n\n⏰ **ফাইল সাবমিট লাস্ট টাইম:** সকাল ১০:৩০ মিনিট।`\n\n`📌 **পয়েন্ট ৩: 📸 Instagram Mother Account (2FA) [V. Important]**\n\n💸 **প্রাইস:** প্রতি পিস ৮ টাকা (৫০+ হলে ৯ টাকা)\n\n⚠️ **নিয়ম:** * ❗ একটি নাম্বার দিয়ে একটি আইডিই খুলতে হবে, না হলে আইডি রিজেক্ট।\n\n⏰ **আইডি সাবমিট লাস্ট টাইম:** যেকোনো সময় (Anytime)।`\n\n|📌 **পয়েন্ট ৪: 🔵 Facebook (FBc00Fnd 2fa)**\n\n💸 **প্রাইস:** প্রতি পিস ৫.৮০ টাকা (৫০+ হলে ৬ টাকা)\n\n⚠️ **নিয়ম:** * ❌ **পাসওয়ার্ডের শেষে কোনো তারিখ দেওয়া যাবে না।**\n\n⏰ **আইডি সাবমিট লাস্ট টাইম:** রাত ১০:০০ মিনিট।|`\n\n**✅ সবাই নিয়ম মেনে সঠিক সময়ে কাজ জমা দিন। ধন্যবাদ!**\n\n**Support:** @Dinanhaji
    ", reply_markup=main_menu())
                    

# ==========================================
# ২. ওয়ার্ক স্টার্ট লজিক (Work Start)
# ==========================================
@dp.message_handler(lambda message: message.text == "Work start 🔥")
async def work_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("IG Mother Account", "IG 2fa")
    await message.answer("যেকোনো সমস্যাই :@Dinanhaji । আমাদের গ্রুপে জয়েন হয়ে নেন প্রাইস এবং রুলস জানতে :https://t.me/instafbhub      আপনার কাজের ক্যাটাগরি বেছে নিন:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text in ["IG Mother Account", "IG 2fa"])
async def ask_file(message: types.Message):
    await message.answer("আপনার এক্সেল ফাইলটি (Excel File) পাঠান। প্রাইস এবং রুলস আপডেট জানতে :https://t.me/instafbhub")
    await BotState.waiting_for_file.set()

@dp.message_handler(content_types=['document'], state=BotState.waiting_for_file)
async def handle_file(message: types.Message, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Add Money 💰", callback_data=f"adminadd_{message.from_user.id}"))
    
    await bot.send_document(ADMIN_ID, message.document.file_id, 
                           caption=f"📩 নতুন ফাইল জমা পড়েছে!\n👤 ইউজার আইডি: `{message.from_user.id}`", 
                           reply_markup=keyboard, parse_mode="Markdown")
    
    await message.answer("✅ আপনার ফাইলটি জমা হয়েছে। এডমিন চেক করে ব্যালেন্স দিয়ে দিবে। আর ২৪ ঘণ্টার মধ্যে রিপোর্ট চলে আসবে!", reply_markup=main_menu())
    await state.finish()

# ==========================================
# ৩. উইথড্র ও পেমেন্ট মেথড চেঞ্জ লজিক
# ==========================================
@dp.message_handler(lambda message: message.text == "Withdraw")
async def withdraw_process(message: types.Message):
    cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (message.from_user.id,))
    res = cursor.fetchone()
    balance, address = res[0], res[1]

    if not address:
        await message.answer("আপনার পেমেন্ট মেথড দিন (যেমন: বিকাশ/নগদ/রকেট/বাইনান্স এড্রেস) মেথড পাঠানোর ফরমেট: Bikash :01789***** Nagad :0197976*** Binance : 0givkbgbj****")
        await BotState.waiting_for_address.set()
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Change Payment Method ⚙️", callback_data="change_method"))
        
        await message.answer(f"💰 আপনার বর্তমান ব্যালেন্স: {balance} ৳\n📍 বর্তমান পেমেন্ট এড্রেস: {address}\n\nআপনি কত টাকা উইথড্র করতে চান লিখুন (অথবা নিচে থেকে মেথড পরিবর্তন করুন):", reply_markup=keyboard)
        await BotState.waiting_for_withdraw_amount.set()

@dp.callback_query_handler(text="change_method", state="*")
async def change_method_callback(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.answer("আপনার নতুন পেমেন্ট মেথড বা নম্বরটি দিন:")
    await BotState.waiting_for_address.set()
    await call.answer()

@dp.message_handler(state=BotState.waiting_for_address)
async def save_address(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE users SET address=? WHERE user_id=?", (message.text, message.from_user.id))
    db.commit()
    await message.answer(f"✅ সফল! আপনার পেমেন্ট এড্রেস আপডেট হয়েছে।🔥\nএখন আবার 'Withdraw' বাটনে ক্লিক করে টাকা তুলতে পারেন।", reply_markup=main_menu())
    await state.finish()

@dp.message_handler(state=BotState.waiting_for_withdraw_amount)
async def withdraw_done(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (message.from_user.id,))
        balance, address = cursor.fetchone()

        if amount > balance:
            await message.answer("❌ পর্যাপ্ত ব্যালেন্স নেই!")
        else:
            new_balance = balance - amount
            cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_balance, message.from_user.id))
            db.commit()
            
            await bot.send_message(ADMIN_ID, f"🔔 উইথড্র রিকোয়েস্ট!\n🆔 আইডি: `{message.from_user.id}`\n💵 পরিমাণ: {amount} ৳\n📍 এড্রেস: {address}")
            await message.answer(f"✅ উইথড্র সফল! {amount} ৳ কেটে নেওয়া হয়েছে।\nবর্তমান ব্যালেন্স: {new_balance} ৳", reply_markup=main_menu())
        await state.finish()
    except:
        await message.answer("❌ শুধু সংখ্যা লিখুন। অথবা মেথড চেঞ্জ বাটনে ক্লিক করুন।")

# ==========================================
# ৪. এডমিন প্যানেল
# ==========================================
@dp.message_handler(commands=['check'])
async def admin_check(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        uid = message.get_args()
        cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (uid,))
        res = cursor.fetchone()
        if res: await message.answer(f"👤 ইউজার: `{uid}`\n💰 ব্যালেন্স: {res[0]} ৳\n📍 এড্রেস: {res[1]}")
        else: await message.answer("❌ ইউজার পাওয়া যায়নি।")

@dp.message_handler(commands=['edit'])
async def admin_edit(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            args = message.get_args().split()
            cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (args[1], args[0]))
            db.commit()
            await message.answer(f"✅ ইউজার {args[0]} এর ব্যালেন্স এডিট করা হয়েছে।")
        except: await message.answer("ফরম্যাট: /edit আইডি টাকা")

@dp.message_handler(commands=['broadcast'])
async def admin_broadcast(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        text = message.get_args()
        cursor.execute("SELECT user_id FROM users")
        all_users = cursor.fetchall()
        for user in all_users:
            try: await bot.send_message(user[0], text)
            except: pass
        await message.answer("✅ সবার কাছে মেসেজ পাঠানো হয়েছে।")

@dp.callback_query_handler(lambda c: c.data.startswith('adminadd_'))
async def add_money_btn(call: types.CallbackQuery, state: FSMContext):
    target_id = call.data.split('_')[1]
    await state.update_data(target_id=target_id)
    await call.message.answer(f"ইউজার `{target_id}` কে কত টাকা পাঠাতে চান?")
    await BotState.waiting_for_add_money.set()

@dp.message_handler(state=BotState.waiting_for_add_money)
async def final_add_money(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        try:
            data = await state.get_data()
            amount = float(message.text)
            uid = data['target_id']
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
            db.commit()
            await bot.send_message(uid, f"✅আপনার একাউন্টে {amount} ৳ যোগ করেছে।")
            await message.answer(f"✅ {amount} ৳ সফলভাবে যোগ করা হয়েছে।")
        except: await message.answer("❌ ভুল ইনপুট।")
        await state.finish()

# ==========================================
# ৫. রান করা
# ==========================================
if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
