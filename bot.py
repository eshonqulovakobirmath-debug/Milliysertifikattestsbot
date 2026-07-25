import telebot
from telebot import types
import sqlite3
import os
import pandas as pd
import json
from datetime import datetime, timedelta

# --- SOZLAMALAR ---
TOKEN = os.environ.get('BOT_TOKEN', 'Sizning_Tokeningiz')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 5541008041))
CHANNEL_USERNAME = "@eshonqulov_math"
NETLIFY_APP_URL = "https://incredible-meringue-b4becc.netlify.app"

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
user_states = {}

# --- BAZA ---
DB_DIR = '/app/data' if os.path.exists('/app/data') else '.'
DB_PATH = os.path.join(DB_DIR, 'test_system.db')

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, full_name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tests (
                        test_code TEXT PRIMARY KEY, creator_id INTEGER, test_type TEXT, 
                        subject TEXT, test_name TEXT, file_id TEXT, has_file BOOLEAN,
                        deadline DATETIME, reactivation_time DATETIME, 
                        rasch_mode TEXT, html_link TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, test_code TEXT, 
                        correct_count INTEGER, qobiliyat REAL, score REAL, foiz TEXT, grade TEXT, 
                        majburiy REAL, fan_1 REAL, fan_2 REAL, submitted_at DATETIME)''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- UMUMIY KLAVIATURALAR ---
cancel_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
cancel_markup.add("🔙 Bekor qilish")

def check_cancel(message):
    """Foydalanuvchi bekor qilishni bossa yoki buyruq yuborsa, jarayonni to'xtatish."""
    if message.text in ["🔙 Bekor qilish", "/start", "/edit", "/info"]:
        bot.send_message(message.chat.id, "🛑 <b>Amal bekor qilindi.</b>", reply_markup=types.ReplyKeyboardRemove())
        if message.text.startswith('/'):
            if message.text == '/start': start_command(message)
            elif message.text == '/edit': edit_command(message)
            elif message.text == '/info': info_command(message)
        else:
            bot.send_message(message.chat.id, "Asosiy menyuga qaytish uchun /start ni bosing.")
        return True
    return False

# --- BUYRUQLAR (MENU) ---
bot.set_my_commands([
    types.BotCommand("/start", "🔄 Qayta ishga tushirish"),
    types.BotCommand("/edit", "✏️ Ism familiyani o'zgartirish"),
    types.BotCommand("/info", "ℹ️ Bot haqida ma'lumot")
])

# --- INLINE MENYULAR ---
def get_main_inline_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📝 MS Test", callback_data="menu_ms"),
        types.InlineKeyboardButton("📋 Oddiy Test", callback_data="menu_oddiy")
    )
    markup.add(
        types.InlineKeyboardButton("📚 Test Baza", callback_data="menu_baza"),
        types.InlineKeyboardButton("📊 Natijalarim", callback_data="menu_my_results")
    )
    markup.add(
        types.InlineKeyboardButton("📥 Natija Olish", callback_data="menu_get_results"),
        types.InlineKeyboardButton("🗣 Speaking Mock", callback_data="menu_speaking")
    )
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🌐 HTML Test (Admin)", callback_data="menu_html_admin"))
    return markup

def get_action_menu(test_type):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⚡️ Testga javob berish ⚡️", callback_data=f"solve_{test_type}"),
        types.InlineKeyboardButton("⚡️ Test yaratish ⚡️", callback_data=f"create_{test_type}"),
        types.InlineKeyboardButton("🔙 Orqaga", callback_data="menu_main")
    )
    return markup

# --- RO'YXATDAN O'TISH VA TEKSHIRUV ---
def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def check_auth(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
        bot.send_message(message.chat.id, "⚠️ <b>Botdan foydalanish uchun kanalga obuna bo'ling!</b>", reply_markup=markup)
        return False
    
    cursor.execute('SELECT full_name FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        msg = bot.send_message(message.chat.id, "👤 <b>Iltimos, botdan foydalanish uchun ism va familiyangizni kiriting</b>\n<i>(Masalan: Eshonqulov Akobir):</i>", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, register_user)
        return False
    return True

def register_user(message):
    if message.text.startswith('/'):
        msg = bot.send_message(message.chat.id, "❌ Iltimos, buyruq kiritmang. Haqiqiy ism va familiyangizni yozing:")
        bot.register_next_step_handler(msg, register_user)
        return

    cursor.execute('INSERT OR REPLACE INTO users (user_id, full_name) VALUES (?, ?)', (message.from_user.id, message.text))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ <b>Xush kelibsiz, {message.text}!</b>\nQuyidagi menyudan kerakli bo'limni tanlang:", reply_markup=get_main_inline_menu(message.from_user.id))

# --- ASOSIY BUYRUQLAR ---
@bot.message_handler(commands=['start'])
def start_command(message):
    if check_auth(message):
        bot.send_message(message.chat.id, "🎯 <b>Ixtisoslashtirilgan Test Tizimi</b>\nKategoriyani tanlang:", reply_markup=get_main_inline_menu(message.from_user.id))

@bot.message_handler(commands=['edit'])
def edit_command(message):
    if not check_auth(message): return
    msg = bot.send_message(message.chat.id, "✏️ Yangi ism va familiyangizni kiriting:", reply_markup=cancel_markup)
    bot.register_next_step_handler(msg, register_user)

@bot.message_handler(commands=['info'])
def info_command(message):
    bot.send_message(message.chat.id, "ℹ️ <b>Ma'lumot:</b>\nBu tizim DTM, Milliy Sertifikat va ixtisoslashtirilgan testlarga moslashtirilgan.\n👨‍💻 <b>Yaratuvchi:</b> Eshonqulov Akobir.")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    if is_subscribed(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        if check_auth(call.message):
            bot.send_message(call.message.chat.id, "✅ Obuna tasdiqlandi!", reply_markup=get_main_inline_menu(call.from_user.id))
    else:
        bot.answer_callback_query(call.id, "❌ Hali obuna bo'lmadingiz!", show_alert=True)

# --- ICHMA-ICH MENYULARNI BOSHQARISH ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def menu_navigation(call):
    action = call.data.split('_', 1)[1]
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    user_id = call.from_user.id

    if action == "main":
        bot.edit_message_text("🎯 <b>Asosiy Menyu</b>\nKategoriyani tanlang:", chat_id, msg_id, reply_markup=get_main_inline_menu(user_id))
    
    elif action == "ms":
        text = "<b>📝 MS Test bo'limi</b>\nMilliy Sertifikat va murakkab standartidagi testlar.\n\nTanlang:"
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=get_action_menu('ms'))
        
    elif action == "oddiy":
        text = "<b>📋 Oddiy Test bo'limi</b>\nDTM standartidagi aralash va oddiy testlar.\n\nTanlang:"
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=get_action_menu('normal'))
        
    elif action == "baza":
        subjects = ["Matematika", "Ingliz tili", "O'zbek tili", "Fizika", "Kimyo", "Biologiya"]
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(*[types.InlineKeyboardButton(s, callback_data=f"baza_{s}") for s in subjects])
        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="menu_main"))
        bot.edit_message_text("📂 <b>Arxivdagi testlar bazasi.</b>\nFanni tanlang:", chat_id, msg_id, reply_markup=markup)

    elif action == "my_results":
        cursor.execute('SELECT test_code, correct_count, score, grade FROM results WHERE user_id = ? ORDER BY id DESC LIMIT 10', (user_id,))
        results = cursor.fetchall()
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="menu_main"))
        if results:
            text = "📈 <b>Sizning oxirgi natijalaringiz:</b>\n\n"
            for r in results:
                daraja = f" | Daraja: <b>{r[3]}</b>" if r[3] else ""
                text += f"🔖 Kod: <code>{r[0]}</code> | ✅: {r[1]} | 🏆: {r[2]}{daraja}\n"
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)
        else:
            bot.edit_message_text("📭 Siz hali test ishlamagansiz.", chat_id, msg_id, reply_markup=markup)

    elif action == "get_results":
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "📊 Qaysi testning natijalari kerak?\n<b>Test kodini kiriting:</b>", reply_markup=cancel_markup)
        bot.register_next_step_handler(msg, process_get_results)

    elif action == "speaking":
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="menu_main"))
        bot.edit_message_text("🎙 <b>Speaking Mock</b> tizimi tez kunda ishga tushadi. Yangiliklarni kuzatib boring!", chat_id, msg_id, reply_markup=markup)

    elif action == "html_admin":
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "🔗 HTML test uchun maxsus <b>Test Kodini</b> o'ylab toping:", reply_markup=cancel_markup)
        bot.register_next_step_handler(msg, process_html_code)


# --- TEST YECHISH ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("solve_"))
def ask_solve_code(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, "✍️ <b>Test kodini kiriting:</b>", reply_markup=cancel_markup)
    bot.register_next_step_handler(msg, process_solve_test)

def check_test_status(test_data):
    if not test_data[7]: return True, "Active"
    deadline = datetime.strptime(test_data[7], "%Y-%m-%d %H:%M:%S")
    reactivation = datetime.strptime(test_data[8], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    if deadline < now < reactivation:
        return False, f"🔒 Test vaqti tugagan. Natijalar hisoblanmoqda.\nTest {reactivation.strftime('%H:%M')} da arxivga tushadi."
    return True, "Active"

def process_solve_test(message):
    if check_cancel(message): return
    
    code = message.text
    cursor.execute('SELECT test_type, html_link, has_file, test_name, subject, file_id, creator_id, deadline, reactivation_time FROM tests WHERE test_code = ?', (code,))
    test = cursor.fetchone()
    
    if not test:
        bot.send_message(message.chat.id, "❌ Bunday test topilmadi.", reply_markup=get_main_inline_menu(message.from_user.id))
        return
        
    is_active, status_msg = check_test_status(test)
    if not is_active:
        bot.send_message(message.chat.id, status_msg, reply_markup=get_main_inline_menu(message.from_user.id))
        return

    test_type, html_link, has_file, test_name, subject, file_id = test[0], test[1], test[2], test[3], test[4], test[5]
    
    # Klaviatura orqaga qaytishni tozalash
    bot.send_message(message.chat.id, "Yuklanmoqda...", reply_markup=types.ReplyKeyboardRemove()).delete()

    if test_type == 'html':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌐 Testni ishlash", web_app=types.WebAppInfo(url=f"{html_link}?user_id={message.from_user.id}")))
        markup.add(types.InlineKeyboardButton("🔙 Asosiy Menyu", callback_data="menu_main"))
        bot.send_message(message.chat.id, f"📝 <b>Maxsus HTML Test topildi!</b>\nKod: <code>{code}</code>", reply_markup=markup)
        return

    mini_app_url = f"{NETLIFY_APP_URL}/?test_code={code}&user_id={message.from_user.id}&type={test_type}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📝 Javoblarni Kiritish", web_app=types.WebAppInfo(url=mini_app_url)))
    markup.add(types.InlineKeyboardButton("🔙 Asosiy Menyu", callback_data="menu_main"))

    if not has_file:
        bot.send_message(message.chat.id, f"✅ <b>{subject} - {test_name}</b> topildi.\n(Faylsiz test).\n\nJavoblarni kiritish uchun tugmani bosing:", reply_markup=markup)
    else:
        try:
            bot.send_document(message.chat.id, file_id, caption=f"✅ <b>{test_name}</b>\nFaylni ochib ishlang va javoblarni kiriting.", reply_markup=markup)
        except:
            bot.send_photo(message.chat.id, file_id, caption=f"✅ <b>{test_name}</b>\nRasm orqali ishlab, javoblaringizni yozing.", reply_markup=markup)

# --- WEB APP MA'LUMOTLARINI QABUL QILISH ---
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    """Mini app dan qaytgan javoblar va ballarni bazaga saqlaydi va foydalanuvchiga xabar beradi."""
    try:
        data = json.loads(message.web_app_data.data)
        
        test_code = data.get('test_code')
        correct_count = data.get('correct_count', 0)
        score = data.get('score', 0.0)
        qobiliyat = data.get('qobiliyat', 0.0)
        foiz = data.get('foiz', '0%')
        grade = data.get('grade', '')
        majburiy = data.get('majburiy', 0.0)
        fan_1 = data.get('fan_1', 0.0)
        fan_2 = data.get('fan_2', 0.0)
        submitted_at = datetime.now().strftime("%Y.%m.%d %H:%M")

        cursor.execute('''INSERT INTO results 
                          (user_id, test_code, correct_count, qobiliyat, score, foiz, grade, majburiy, fan_1, fan_2, submitted_at) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                       (message.from_user.id, test_code, correct_count, qobiliyat, score, foiz, grade, majburiy, fan_1, fan_2, submitted_at))
        conn.commit()

        # Test turiga qarab foydalanuvchiga chiroyli javob ko'rsatamiz
        cursor.execute('SELECT test_type FROM tests WHERE test_code = ?', (test_code,))
        test_type_data = cursor.fetchone()
        t_type = test_type_data[0] if test_type_data else 'normal'

        if t_type == 'ms':
            msg_text = (f"✅ <b>Javoblaringiz muvaffaqiyatli qabul qilindi!</b>\n\n"
                        f"🔖 Test kodi: <code>{test_code}</code>\n"
                        f"🎯 To'g'ri javoblar: <b>{correct_count}</b> ta\n"
                        f"📊 Foiz: <b>{foiz}</b>\n"
                        f"🏆 Umumiy ball: <b>{score}</b>\n"
                        f"📈 Daraja: <b>{grade}</b>")
        else:
            msg_text = (f"✅ <b>Javoblaringiz qabul qilindi!</b>\n\n"
                        f"🔖 Test kodi: <code>{test_code}</code>\n"
                        f"🎯 To'g'ri javoblar: <b>{correct_count}</b> ta\n"
                        f"🏆 Ball: <b>{score}</b>")

        bot.send_message(message.chat.id, msg_text, reply_markup=get_main_inline_menu(message.from_user.id))

    except Exception as e:
        bot.send_message(message.chat.id, "❌ Javoblarni tahlil qilishda xatolik yuz berdi. Iltimos qayta urinib ko'ring.", reply_markup=get_main_inline_menu(message.from_user.id))


# --- TEST YARATISH ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("create_"))
def create_test_start(call):
    test_type = call.data.split('_')[1]
    user_states[call.message.chat.id] = {'type': test_type, 'creator': call.from_user.id}
    
    subjects = ["Matematika", "Ingliz tili", "O'zbek tili", "Fizika", "Kimyo", "Biologiya"]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(s, callback_data=f"setsub_{s}") for s in subjects])
    markup.add(types.InlineKeyboardButton("🔙 Bekor qilish", callback_data="menu_main"))
    
    bot.edit_message_text("📚 Test qaysi fandan? Tanlang:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("setsub_"))
def create_test_subject(call):
    subject = call.data.split('_')[1]
    user_states[call.message.chat.id]['subject'] = subject
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, "🏷 <b>Testga nom bering:</b>", reply_markup=cancel_markup)
    bot.register_next_step_handler(msg, create_test_name)

def create_test_name(message):
    if check_cancel(message): return
    user_states[message.chat.id]['name'] = message.text
    msg = bot.send_message(message.chat.id, "🔑 <b>Noyob test kodini kiriting:</b>", reply_markup=cancel_markup)
    bot.register_next_step_handler(msg, create_test_code)

def create_test_code(message):
    if check_cancel(message): return
    user_states[message.chat.id]['code'] = message.text
    msg = bot.send_message(message.chat.id, "📎 <b>Test faylini (PDF/Rasm) yuboring.</b>\nFaylsiz test uchun <b>0</b> yuboring.", reply_markup=cancel_markup)
    bot.register_next_step_handler(msg, create_test_file)

def create_test_file(message):
    if check_cancel(message): return
    data = user_states[message.chat.id]
    
    if message.text == "0":
        data['has_file'] = False; data['file_id'] = None
    elif message.document:
        data['has_file'] = True; data['file_id'] = message.document.file_id
    elif message.photo:
        data['has_file'] = True; data['file_id'] = message.photo[-1].file_id
    else:
        msg = bot.send_message(message.chat.id, "❌ Iltimos, fayl yuboring yoki 0 deb yozing:", reply_markup=cancel_markup)
        bot.register_next_step_handler(msg, create_test_file)
        return

    msg = bot.send_message(message.chat.id, "⏳ <b>Test qachon yakunlanadi?</b>\nFormat: <code>DD.MM.YYYY HH:MM</code>\nCheksiz bo'lsa <b>0</b> deb yuboring.", reply_markup=cancel_markup)
    bot.register_next_step_handler(msg, create_test_deadline)

def create_test_deadline(message):
    if check_cancel(message): return
    data = user_states[message.chat.id]
    
    if message.text == "0":
        data['deadline'] = None; data['reactivation'] = None
    else:
        try:
            deadline = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
            data['deadline'] = deadline
            data['reactivation'] = deadline + timedelta(hours=2)
        except ValueError:
            msg = bot.send_message(message.chat.id, "❌ Xato format. To'g'ri yozing yoki 0:", reply_markup=cancel_markup)
            bot.register_next_step_handler(msg, create_test_deadline)
            return

    # Rasch mode ni so'ramasdan avtomatik to'liq Rasch (full) saqlaymiz. Oddiy test uchun o'zimiz moslashtiramiz
    data['rasch_mode'] = 'full'
    
    bot.send_message(message.chat.id, "⏳ Saqlanmoqda...", reply_markup=types.ReplyKeyboardRemove()).delete()
    finalize_test_creation(message.chat.id)

def finalize_test_creation(chat_id):
    data = user_states.get(chat_id)
    try:
        cursor.execute('''INSERT INTO tests 
                          (test_code, creator_id, test_type, subject, test_name, file_id, has_file, deadline, reactivation_time, rasch_mode)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                       (data['code'], data['creator'], data['type'], data.get('subject'), data['name'], 
                        data['file_id'], data['has_file'], data['deadline'], data['reactivation'], data['rasch_mode']))
        conn.commit()
        bot.send_message(chat_id, f"✅ <b>Test muvaffaqiyatli saqlandi!</b>\n\n📌 <b>Kod:</b> <code>{data['code']}</code>\n📚 <b>Fan:</b> {data.get('subject')}", reply_markup=get_main_inline_menu(data['creator']))
    except sqlite3.IntegrityError:
        bot.send_message(chat_id, "⚠️ Bu test kodi band. Boshqasini yozib qayta urinib ko'ring.", reply_markup=get_main_inline_menu(data['creator']))

# --- BAZA ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("baza_"))
def show_baza_tests(call):
    subject = call.data.split('_')[1]
    now = datetime.now()
    cursor.execute('''SELECT test_code, test_name, test_type FROM tests 
                      WHERE subject = ? AND (deadline IS NULL OR reactivation_time <= ?)''', (subject, now))
    tests = cursor.fetchall()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    if tests:
        for t_code, t_name, t_type in tests:
            markup.add(types.InlineKeyboardButton(f"📝 {t_name} ({t_type.upper()})", callback_data=f"getbaza_{t_code}"))
        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="menu_baza"))
        bot.edit_message_text(f"📚 <b>{subject}</b> testlari:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="menu_baza"))
        bot.edit_message_text(f"📭 {subject} bo'yicha arxivda hozircha test yo'q.", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("getbaza_"))
def get_test_from_baza(call):
    code = call.data.split('_')[1]
    call.message.text = code
    bot.delete_message(call.message.chat.id, call.message.message_id)
    process_solve_test(call.message)

# --- NATIJA OLIH VA EXCEL ---
def process_get_results(message):
    if check_cancel(message): return
    code = message.text
    cursor.execute('SELECT creator_id, test_type FROM tests WHERE test_code = ?', (code,))
    test = cursor.fetchone()
    
    bot.send_message(message.chat.id, "Yuklanmoqda...", reply_markup=types.ReplyKeyboardRemove()).delete()

    if not test:
        bot.send_message(message.chat.id, "❌ Bunday kod topilmadi.", reply_markup=get_main_inline_menu(message.from_user.id))
        return
        
    if test[0] != message.from_user.id and message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ Siz faqat o'zingiz yaratgan test natijalarini ololasiz.", reply_markup=get_main_inline_menu(message.from_user.id))
        return

    test_type = test[1]
    if test_type == 'ms':
        cursor.execute('''SELECT u.full_name, r.correct_count, r.qobiliyat, r.score, r.foiz, r.grade, r.majburiy, r.fan_1, r.fan_2, r.submitted_at 
                          FROM results r JOIN users u ON r.user_id = u.user_id 
                          WHERE r.test_code = ? ORDER BY r.score DESC''', (code,))
        res = cursor.fetchall()
        if res:
            # Reyting raqamini qo'shib chiqamiz
            formatted_res = []
            for i, r in enumerate(res, 1):
                formatted_res.append((i,) + r)
            
            # EXCEL fayl rasmdagi ustunlarga to'liq moslashtirilgan 
            cols = ["#", "Ismi", "To'g'ri", "Qobiliyat", "Ball", "Foiz", "Daraja", "Majburiy", "Birinchi fan", "Ikkinchi fan", "Vaqt"]
            df = pd.DataFrame(formatted_res, columns=cols)
            filepath = f"MS_Natija_{code}.xlsx"
            df.to_excel(filepath, index=False)
            
            with open(filepath, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"📈 <b>{code}</b> MS Test natijalari\n<i>To'liq Rasch Tahlili</i>", reply_markup=get_main_inline_menu(message.from_user.id))
            os.remove(filepath)
        else:
            bot.send_message(message.chat.id, "📭 Bu testni hali hech kim ishlamadi.", reply_markup=get_main_inline_menu(message.from_user.id))
    else:
        cursor.execute('''SELECT u.full_name, r.correct_count, r.score 
                          FROM results r JOIN users u ON r.user_id = u.user_id 
                          WHERE r.test_code = ? ORDER BY r.score DESC''', (code,))
        res = cursor.fetchall()
        if res:
            text = f"📊 <b>{code}</b> - Natijalar ro'yxati:\n\n"
            for i, r in enumerate(res, 1):
                # Oddiy testda to'g'ri javoblar va yonida bal yoziladi
                text += f"<b>{i}.</b> 👤 {r[0]} | ✅: {r[1]} ta | 🏆: {r[2]:.1f} ball\n"
            bot.send_message(message.chat.id, text, reply_markup=get_main_inline_menu(message.from_user.id))
        else:
            bot.send_message(message.chat.id, "📭 Bu testni hali hech kim ishlamadi.", reply_markup=get_main_inline_menu(message.from_user.id))

# --- HTML ADMIN ---
def process_html_code(message):
    if check_cancel(message): return
    user_states[message.chat.id] = {'code': message.text, 'type': 'html'}
    msg = bot.send_message(message.chat.id, "🌐 Endi ushbu testning <b>URL linkini</b> (sayt manzilini) tashlang:", reply_markup=cancel_markup)
    bot.register_next_step_handler(msg, process_html_link)

def process_html_link(message):
    if check_cancel(message): return
    data = user_states.get(message.chat.id)
    bot.send_message(message.chat.id, "Saqlanmoqda...", reply_markup=types.ReplyKeyboardRemove()).delete()
    
    try:
        cursor.execute('''INSERT INTO tests (test_code, creator_id, test_type, test_name, has_file, html_link)
                          VALUES (?, ?, ?, ?, ?, ?)''', 
                       (data['code'], ADMIN_ID, 'html', 'HTML Maxsus Test', False, message.text))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ <b>HTML test saqlandi!</b>\nKod: <code>{data['code']}</code>", reply_markup=get_main_inline_menu(message.from_user.id))
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, "⚠️ Bu test kodi mavjud.", reply_markup=get_main_inline_menu(message.from_user.id))

if __name__ == '__main__':
    print("🚀 Bot ishga tushdi...")
    bot.infinity_polling()
