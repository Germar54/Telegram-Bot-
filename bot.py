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
cursor.execute('''CREATE TABLE IF NOT EXISTS stats 
                  (user_id INTEGER, file_count INTEGER DEFAULT 0, single_id_count INTEGER DEFAULT 0, date TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests 
                  (req_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT DEFAULT 'pending')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, address TEXT)''')
db.commit()
cursor.execute('''CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)''')
db.commit()

cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, address TEXT)''')
db.commit()

class BotState(StatesGroup):
    waiting_for_file = State()
    waiting_for_payment_address = State()  # এই লাইনটি আপনার ক্লাসে থাকতে হবে
    waiting_for_withdraw_amount = State()
    waiting_for_add_money = State()
    waiting_for_single_user = State()
    waiting_for_single_pass = State()
    waiting_for_single_2fa = State()
    waiting_for_block_reason = State()

async def is_blocked(user_id):
    cursor.execute("SELECT user_id FROM blacklist WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Work start 🔥", "💳Withdraw")
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
    url_button = types.InlineKeyboardButton(text="Latest update and Method", url="https://t.me/instafbhub") 
    inline_kb.add(url_button)

    # ২. এখানে আপনার মেসেজটি লিখুন (লাইন ব্রেক বা ইন্টার দিতে \n ব্যবহার করুন)
        # ২. এখানে আপনার বড় মেসেজটি (রেট লিস্ট) বসাবেন
    welcome_text = """📢 **আজকের কাজের আপডেট এবং রেট লিস্ট** 📢
নিচের পয়েন্টগুলো মনোযোগ দিয়ে পড়ুন।

📌 **`পয়েন্ট ১: 📸 Instagram 00 Follower (2FA)`**
💸 **প্রাইস:** প্রতি পিস **`২.৩০`** টাকা (১০০+ হলে **`২.৫০`** টাকা)
📄 **শীট ফরম্যাট:** **`User-pass-2fa`**
⏰ **টাইম:** রাত **`০৮:১৫`** মিনিট।

📌 **`পয়েন্ট ২: 📸 Instagram Cookies 00 Follower`**
💸 **প্রাইস:** প্রতি পিস **`৩.৯০`** টাকা (১০০+ হলে **`৪.১০`** টাকা)
📄 **শীট ফরম্যাট:** **`User-pass`**
⏰ **টাইম:** সকাল **`১০:৩০`** মিনিট।

📌 **`পয়েন্ট ৩: 📸 Instagram Mother Account (2FA)`**
💸 **প্রাইস:** প্রতি পিস **`৮`** টাকা (৫০+ হলে **`৯`** টাকা)
⏰ **টাইম:** **`Anytime`**

📌 **`পয়েন্ট ৪: 🔵 Facebook (FBc00Fnd 2fa)`**
💸 **প্রাইস:** প্রতি পিস **`৫.৮০`** টাকা (৫০+ হলে **`৬`** টাকা)
⏰ **টাইম:** রাত **`১০:০০`** PM।

✅ সবাই নিয়ম মেনে সঠিক সময়ে কাজ জমা দিন।
**Support:** @Dinanhaji"""

    # ৩. মেসেজ পাঠানো (বাটনসহ এবং parse_mode যোগ করে)
    await message.answer(welcome_text, reply_markup=inline_kb, parse_mode="Markdown")
    
    # ৪. মেইন মেনু দেখানো
    await message.answer("একটি অপশন বেছে নিন:", reply_markup=main_menu())

# =========================================
@dp.message_handler(lambda message: message.text in ["IG Mother Account", "IG 2fa"])
async def ask_work_type(message: types.Message, state: FSMContext):
    # এই লাইনগুলো বাম দিক থেকে ৪টি স্পেস ডানে থাকবে
    await state.update_data(category=message.text)
    
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.add(types.InlineKeyboardButton("🗃️ File", callback_data="type_file"))
    inline_kb.add(types.InlineKeyboardButton("👤 Single ID", callback_data="type_single"))
    
    await message.answer("✅ আপনার কাজের ধরণ বেছে নিন:", reply_markup=inline_kb)
@dp.message_handler(lambda message: message.text == "Work start 🔥")
async def work_start(message: types.Message):
    if await is_blocked(message.from_user.id):
        return await message.answer("❌ দুঃখিত, আপনি ব্লকড! আপনি আর কাজ জমা দিতে পারবেন না।")
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Work start 🔥", "💳Withdraw")
    keyboard.add("🔄 রিফ্রেশ")
    
    msg = "👍 যেকোনো সমস্যায়: @Dinanhaji !\n🔴 আপনার কাজের ক্যাটাগরি বেছে নিন:"
    await message.answer(msg, reply_markup=keyboard)
@dp.message_handler(lambda message: message.text == "💳Withdraw")
async def withdraw_main(message: types.Message):
    if await is_blocked(message.from_user.id):
        return await message.answer("❌ আপনি ব্লকড থাকার কারণে উইথড্র করতে পারবেন না।")
        
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("➕ অ্যাড পেমেন্ট মেথড", callback_data="add_method"),
        types.InlineKeyboardButton("💸 উইথড্র করুন", callback_data="confirm_withdraw")
    )
    await message.answer("💰 **উইথড্র মেনু**\nনিচের অপশন থেকে বেছে নিন:", reply_markup=keyboard)


# --- ইনলাইন বাটনের প্রসেসিং (File vs Single ID) ---
@dp.callback_query_handler(lambda c: c.data.startswith('type_'), state="*")
async def process_callback_work_type(callback_query: types.CallbackQuery):
    if callback_query.data == "type_file":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "📤 আপনার এক্সেল ফাইলটি (Excel File) পাঠান।")
        await BotState.waiting_for_file.set()
    elif callback_query.data == "type_single":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "👤 আপনার ইউজার আইডি (User ID) দিন:")
        await BotState.waiting_for_single_user.set()

# --- সিঙ্গেল আইডির তথ্য এক এক করে নেওয়ার হ্যান্ডলার ---
@dp.message_handler(state=BotState.waiting_for_single_user)
async def get_id(message: types.Message, state: FSMContext):
    await state.update_data(u_id=message.text)
    await message.answer("🔑 এবার পাসওয়ার্ড (Password) দিন:")
    await BotState.waiting_for_single_pass.set()

@dp.message_handler(state=BotState.waiting_for_single_pass)
async def get_pass(message: types.Message, state: FSMContext):
    await state.update_data(u_pass=message.text)
    await message.answer("🔐 এবার টু-এফা (2FA Code) দিন:")
    await BotState.waiting_for_single_2fa.set()

@dp.message_handler(state=BotState.waiting_for_single_2fa)
async def get_2fa(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # এডমিন প্যানেলে বিস্তারিত রিপোর্ট পাঠানো
    admin_msg = (f"🚀 **নতুন সিঙ্গেল আইডি জমা পড়েছে!**\n\n"
                 f"👤 **ইউজার আইডি:** `{message.from_user.id}`\n"
                 f"📂 **ক্যাটাগরি:** {data.get('category')}\n"
                 f"━━━━━━━━━━━━━━━\n"
                 f"🆔 **ID:** `{data.get('u_id')}`\n"
                 f"🔑 **Pass:** `{data.get('u_pass')}`\n"
                 f"🔐 **2FA:** `{message.text}`")
    import datetime
    today = datetime.date.today().strftime("%Y-%m-%d")
    cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (message.from_user.id, today))
    cursor.execute("UPDATE stats SET single_id_count = single_id_count + 1 WHERE user_id=? AND date=?", (message.from_user.id, today))
    
    # ক্যাটাগরি অনুযায়ী ব্যালেন্স যোগ করার লজিক
    category = data.get('category')
    amount_to_add = 0

    if category == "IG Mother Account":
        amount_to_add = 9.00
    elif category == "IG 2FA":
        amount_to_add = 2.30

    if amount_to_add > 0:
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount_to_add, message.from_user.id))
    
    db.commit()
    await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    await message.answer("✅ আপনার তথ্য জমা হয়েছে।")
    await state.finish()
    
    
# ৩. রিফ্রেশ বাটনের লজিক (state="*" যোগ করা হয়েছে যাতে যেকোনো অবস্থায় এটি কাজ করে)
@dp.message_handler(lambda message: message.text == "🔄 রিফ্রেশ", state="*")
async def refresh_to_main(message: types.Message, state: FSMContext):
    # ইউজার যদি ফাইল দেওয়ার স্টেটে থাকে তবে তা ক্লিয়ার করবে
    await state.finish() 
    # মেইন মেনুতে ফিরিয়ে নিবে
    await message.answer("✅ আপনি মেইন মেনুতে ফিরে এসেছেন।", reply_markup=main_menu())
    
@dp.message_handler(content_types=['document'], state=BotState.waiting_for_file)
async def handle_file(message: types.Message, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Add Money 💰", callback_data=f"adminadd_{message.from_user.id}"))
    import datetime
    today = datetime.date.today().strftime("%Y-%m-%d")
    cursor.execute("INSERT OR IGNORE INTO stats (user_id, date) VALUES (?, ?)", (message.from_user.id, today))
    cursor.execute("UPDATE stats SET file_count = file_count + 1 WHERE user_id=? AND date=?", (message.from_user.id, today))
    db.commit()

    await bot.send_document(ADMIN_ID, message.document.file_id, 
                           caption=f"📩 নতুন ফাইল জমা পড়েছে!\n👤 ইউজার আইডি: **`{message.from_user.id}`**", 
                           reply_markup=keyboard, parse_mode="Markdown")
    
    await message.answer("✅ আপনার ফাইলটি জমা হয়েছে। \nএডমিন চেক করে ব্যালেন্স দিয়ে দিবে। আর ২৪ ঘণ্টার মধ্যে রিপোর্ট চলে আসবে!/n🚨 রিপোর্ট বটের মধ্যে চলে আসবে!!", reply_markup=main_menu())
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
        await message.answer("💌আপনার পেমেন্ট মেথড দিন ।\n 🗣️(যেমন: বিকাশ/নগদ/রকেট/বাইনান্স এড্রেস)\n👀 মেথড পাঠানোর ফরমেট: \n🟢 Bikash :01789*****\n 🟢Nagad :0197976***\n 🟢Binance : 0givkbgbj****")
        await BotState.waiting_for_address.set()
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Change Payment Method ⚙️", callback_data="change_method"))
        
        await message.answer(f"💰 আপনার বর্তমান ব্যালেন্স: {balance} ৳\n📍 বর্তমান পেমেন্ট এড্রেস: {address}\n\nআপনি কত টাকা উইথড্র করতে চান লিখুন (অবশ্যই ৫০ টাকার উপরে হতে হবে ।):", reply_markup=keyboard)
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
# --- অ্যাডমিন প্যানেল: ইউজার সার্চ ও বিস্তারিত রিপোর্ট ---
@dp.message_handler(commands=['search'], user_id=ADMIN_ID)
async def admin_search(message: types.Message):
    args = message.get_args()
    if not args: return await message.answer("⚠️ আইডি দিন। যেমন: `/search 12345678`")
    
    try:
        target_id = int(args)
        cursor.execute("SELECT balance, address FROM users WHERE user_id=?", (target_id,))
        user = cursor.fetchone()
        
        if user:
            import datetime
            today = datetime.date.today().strftime("%Y-%m-%d")
            # আজকের কাজের হিসাব
            cursor.execute("SELECT file_count, single_id_count FROM stats WHERE user_id=? AND date=?", (target_id, today))
            s = cursor.fetchone() or (0, 0)
            
            text = (f"👤 **ইউজার রিপোর্ট (ID: `{target_id}`)**\n\n"
                    f"💵 ব্যালেন্স: {user[0]} টাকা\n"
                    f"💳 পেমেন্ট মেথড: `{user[1] or 'নেই'}`\n"
                    f"📊 আজ জমা দিয়েছে:\n"
                    f"📁 ফাইল: {s[0]} টি\n"
                    f"👤 সিঙ্গেল আইডি: {s[1]} টি")
            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("❌ ডাটাবেসে এই ইউজার পাওয়া যায়নি।")
    except ValueError:
        await message.answer("❌ আইডি শুধুমাত্র সংখ্যা হতে হবে।")
        # ১. কমান্ড দিয়ে ব্লক করা: /block 12345678
@dp.message_handler(commands=['block'], user_id=ADMIN_ID)
@dp.message_handler(commands=['block'], user_id=ADMIN_ID)
async def admin_block(message: types.Message, state: FSMContext):
    try:
        # কমান্ড থেকে ইউজার আইডি নেওয়া
        uid = int(message.get_args())
        
        # ডাটাবেসে ব্লক হিসেবে সেভ করা
        cursor.execute("INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)", (uid,))
        db.commit()
        
        # কারণ পাঠানোর জন্য আইডিটি সাময়িকভাবে সেভ রাখা
        await state.update_data(blocking_user_id=uid)
        
        await message.answer(f"🚫 ইউজার `{uid}` ব্লক করা হয়েছে।\nএখন ব্লক করার কারণটি লিখে পাঠান:")
        
        # কারণ নেওয়ার জন্য স্টেট সেট করা
        await BotState.waiting_for_block_reason.set()
        
    except:
        await message.answer("⚠️ সঠিক ফরম্যাট: `/block ইউজার_আইডি` লিখুন।")
        

# ২. কমান্ড দিয়ে আনব্লক করা: /unblock 12345678
@dp.message_handler(commands=['unblock'], user_id=ADMIN_ID)
async def admin_unblock(message: types.Message):
    try:
        uid = int(message.get_args())
        cursor.execute("DELETE FROM blacklist WHERE user_id=?", (uid,))
        db.commit()
        await message.answer(f"✅ ইউজার `{uid}` এখন আনব্লক।")
        await bot.send_message(uid, "✅ আপনাকে আনব্লক করা হয়েছে।")
        
    except: await message.answer("সঠিক ফরম্যাট: `/unblock আইডি`")
@dp.callback_query_handler(lambda c: c.data.startswith('block_'), user_id=ADMIN_ID)
async def block_callback(call: types.CallbackQuery, state: FSMContext):
    uid = int(call.data.split('_')[1])
    # ডাটাবেসে ব্লক করা
    cursor.execute("INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)", (uid,))
    db.commit()
    
    # ইউজার আইডি সেভ রাখা
    await state.update_data(blocking_user_id=uid)
    
    await call.message.answer(f"🚫 ইউজার `{uid}` ব্লকড।\nএখন ব্লক করার কারণটি লিখে পাঠান:")
    await BotState.waiting_for_block_reason.set()
    await call.answer()
    
@dp.message_handler(state=BotState.waiting_for_block_reason, user_id=ADMIN_ID)
async def send_block_reason(message: types.Message, state: FSMContext):
    # সেভ করা আইডিটি ফিরিয়ে আনা
    data = await state.get_data()
    uid = data.get('blocking_user_id')
    reason = message.text # আপনি যা লিখে পাঠাবেন
    
    try:
        # ইউজারের কাছে কারণসহ মেসেজ পাঠানো
        msg_text = f"❌ আপনাকে বট থেকে ব্লক করা হয়েছে।\n📝 কারণ: {reason}"
        await bot.send_message(uid, msg_text)
        await message.answer(f"✅ ইউজার `{uid}` কে কারণসহ ব্লক মেসেজ পাঠানো হয়েছে।")
    except:
        await message.answer(f"⚠️ ইউজার `{uid}` কে মেসেজ পাঠানো যায়নি।")
    
    # স্টেট ক্লিয়ার করা
    await state.finish()
    # ৫টি পেমেন্ট মেথড দেখানোর হ্যান্ডলার (বিকাশ, নগদ ইত্যাদি)
@dp.callback_query_handler(lambda c: c.data == "add_method")
async def show_payment_methods(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    methods = ["Bkash", "Nagad", "Rocket", "Binance", "Upay"]
    for m in methods:
        keyboard.insert(types.InlineKeyboardButton(m, callback_data=f"set_{m.lower()}"))
    await call.message.edit_text("💳 **কোন মেথডটি অ্যাড করতে চান?**", reply_markup=keyboard)

# মেথড সিলেক্ট করলে নম্বর চাওয়ার হ্যান্ডলার
@dp.callback_query_handler(lambda c: c.data.startswith('set_'))
async def ask_for_address(call: types.CallbackQuery, state: FSMContext):
    method_name = call.data.split('_')[1].capitalize()
    await state.update_data(current_method=method_name)
    await call.message.answer(f"✅ আপনি **{method_name}** সিলেক্ট করেছেন।\nআপনার নম্বর বা অ্যাড্রেসটি লিখে পাঠান:")
    await BotState.waiting_for_payment_address.set()
    await call.answer()
@dp.message_handler(state=BotState.waiting_for_payment_address)

async def save_payment_address(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    method = user_data.get('current_method')
    address = message.text

    # ডাটাবেসে নম্বর সেভ করার সঠিক কোড
    cursor.execute("UPDATE users SET address=? WHERE user_id=?", (address, message.from_user.id))
    db.commit()

    await message.answer(f"✅ সফল! আপনার {method} নম্বর ({address}) সেভ হয়েছে।")
    await state.finish()
    
    # আবার ৫টি মেথড দেখানোর জন্য মেনু কল করা
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    methods = ["Bkash", "Nagad", "Rocket", "Binance", "Upay"]
    for m in methods:
        keyboard.insert(types.InlineKeyboardButton(m, callback_data=f"set_{m.lower()}"))
    await message.answer("💳 **আরো কোনো মেথড অ্যাড করতে চাইলে সিলেক্ট করুন:**", reply_markup=keyboard)
    await state.set_state(None)
    
                  
if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
