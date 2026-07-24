import telebot
from telebot import types
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

# Muhit o'zgaruvchilari (To'g'rilangan)
TOKEN = os.environ.get('BOT_TOKEN', '8954403610:AAFqfr5wenWMk8hZf8u9QTOqmsm-emL-Xsw')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 5541008041))
CHANNEL_USERNAME = "@eshonqulov_math"

bot = telebot.TeleBot(TOKEN)
user_data = {}

# Ma'lumotlar bazasi manzili
DB_DIR = '/app/data' if os.path.exists('/app/data') else '.'
DB_PATH = os.path.join(DB_DIR, 'test_system.db')

# --- 1. MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            test_code TEXT PRIMARY KEY,
            creator_id INTEGER,
            test_type TEXT,
            subject TEXT,
            test_name TEXT,
            file_id TEXT,
            deadline DATETIME,
            reactivation_time DATETIME,
            rasch_mode TEXT,
            html_link TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            test_code TEXT,
            correct_count INTEGER,
            qobiliyat REAL,       
            score REAL,            
            foiz TEXT,            
            grade TEXT,            
            majburiy REAL,        
            fan_1 REAL,            
            fan_2 REAL,            
            submitted_at DATETIME 
        )
    ''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# Menyu buyruqlarini sozlash
bot.set_my_commands([
    types.BotCommand("/start", "Botni qayta ishga tushirish"),
    types.BotCommand("/edit", "Ismni o'zgartirish uchun bosing"),
    types.BotCommand("/info", "Bot ishlatish haqida ma'lumotlar"),
    types.BotCommand("/ms", "Matematika milliy sertifikat"),
    types.BotCommand("/app", "Matematik va aralash test"),
    types.BotCommand("/testlarim", "Testlaringiz haqida ma'lumotlar"),
    types.BotCommand("/baza", "Testlar bazasi (Arxiv)")
])

# --- 2. MAJBURIY OBUNA VA RO'YXATDAN O'TISH ---
def is_subscribed(user_id):
    # Agar foydalanuvchi Admin bo'lsa, tekshirmasdan o'tkazib yuborish
    if user_id == ADMIN_ID:
        return True
        
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def check_registration_and_start(chat_id, user_id):
    cursor.execute('SELECT full_name FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    # Eskirgan pastki tugmalarni olib tashlash uchun
    remove_markup = types.ReplyKeyboardRemove()
    
    if not user:
        msg = bot.send_message(chat_id, "Iltimos, botdan foydalanish uchun ism va familiyangizni kiriting\n(Masalan: Eshonqulov Akobir):", reply_markup=remove_markup)
        bot.register_next_step_handler(msg, process_registration)
    else:
        bot.send_message(chat_id, f"Assalomu alaykum, {user[0]}!\nIxtisoslashtirilgan test tizimiga xush kelibsiz.\n\nBo'limlarni tanlash uchun chatning quyi chap burchagidagi **Menu** tugmasini bosing yoki buyruqlardan birini tanlang (masalan, /app yoki /ms).", reply_markup=remove_markup, parse_mode='Markdown')

def process_registration(message):
    full_name = message.text
    user_id = message.from_user.id
    cursor.execute('INSERT OR REPLACE INTO users (user_id, full_name) VALUES (?, ?)', (user_id, full_name))
    conn.commit()
    bot.send_message(message.chat.id, "✅ Ma'lumotlaringiz saqlandi! Bot menyusidan (/) foydalanishingiz mumkin.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub"))
        bot.send_message(chat_id, "⚠️ Botdan foydalanish uchun iltimos, avval kanalimizga obuna bo'ling!", reply_markup=markup)
        return
    check_registration_and_start(chat_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def verify_subscription(call):
    user_id = call.from_user.id
    if is_subscribed(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")
        check_registration_and_start(call.message.chat.id, user_id)
    else:
        bot.answer_callback_query(call.id, "❌ Siz hali obuna bo'lmadingiz!", show_alert=True)

# --- 3. YANGI INLINE MENYULAR (Buyruqlar) ---
@bot.message_handler(commands=['edit'])
def change_name(message):
    msg = bot.send_message(message.chat.id, "Yangi ism va familiyangizni kiriting:")
    bot.register_next_step_handler(msg, process_registration)

@bot.message_handler(commands=['info'])
def bot_info(message):
    bot.send_message(message.chat.id, "ℹ️ Ushbu bot DTM va Milliy Sertifikat standartlariga moslashtirilgan testlarni yaratish, yechish va chuqur diagnostika qilish uchun mo'ljallangan.")

@bot.message_handler(commands=['app'])
def app_menu(message):
    cursor.execute('SELECT full_name FROM users WHERE user_id = ?', (message.from_user.id,))
    user = cursor.fetchone()
    full_name = user[0] if user else "Foydalanuvchi"
    
    text = (f"👤 Hurmatli {full_name}\n\n"
            f"Siz bu bo'lim orqali aralash testlar va matematik amalli javoblarni yozishingiz mumkin.\n\n"
            f"Ushbu bo'limdan foydalanishda ehtiyot bo'ling. Har bir belgi muhim ro'l o'ynaydi.\n\n"
            f"Bo'lim tekshiruv jarayonida. Agar xatolik sezsangiz bot yaratuvchisiga murojaat qiling.")
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("⚡️ Testga javob berish ⚡️", callback_data="action_solve_app"))
    markup.add(types.InlineKeyboardButton("⚡️ Test yaratish ⚡️", callback_data="action_create_app"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['ms'])
def ms_menu(message):
    cursor.execute('SELECT full_name FROM users WHERE user_id = ?', (message.from_user.id,))
    user = cursor.fetchone()
    full_name = user[0] if user else "Foydalanuvchi"
    
    text = (f"👤 Hurmatli {full_name}\n\n"
            f"Siz bu bo'lim orqali Matematika milliy sertifikat standartidagi testlarni ishlashingiz yoki yaratishingiz mumkin.\n\n"
            f"Bo'lim tekshiruv jarayonida. Agar xatolik sezsangiz bot yaratuvchisiga murojaat qiling.")
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("⚡️ Testga javob berish ⚡️", callback_data="action_solve_ms"))
    markup.add(types.InlineKeyboardButton("⚡️ Test yaratish ⚡️", callback_data="action_create_ms"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["action_solve_app", "action_solve_ms"])
def callback_solve(call):
    msg = bot.send_message(call.message.chat.id, "📝 Javoblarni tekshirish uchun test kodini kiriting:")
    bot.register_next_step_handler(msg, process_solve_code)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data in ["action_create_app", "action_create_ms"])
def callback_create(call):
    test_type = 'ms' if call.data == "action_create_ms" else 'normal'
    user_data[call.message.chat.id] = {'type': test_type, 'creator': call.from_user.id}
    msg = bot.send_message(call.message.chat.id, "Test qaysi fandan? Fan nomini yozing (Masalan: Matematika):")
    bot.register_next_step_handler(msg, process_subject)
    bot.answer_callback_query(call.id)

# --- 4. TEST KIRITISH JARAYONI ---
def process_subject(message):
    user_data[message.chat.id]['subject'] = message.text
    bot.send_message(message.chat.id, "Testga nom bering (Masalan: DTM Blok 1):")
    bot.register_next_step_handler(message, process_test_name)

def process_test_name(message):
    user_data[message.chat.id]['name'] = message.text
    bot.send_message(message.chat.id, "Noyob test kodini kiriting (Masalan: 1001):")
    bot.register_next_step_handler(message, process_test_code)

def process_test_code(message):
    user_data[message.chat.id]['code'] = message.text
    bot.send_message(message.chat.id, "Test faylini (PDF yoki Rasm) yuboring:")
    bot.register_next_step_handler(message, process_test_file)

def process_test_file(message):
    if message.document:
        user_data[message.chat.id]['file_id'] = message.document.file_id
    elif message.photo:
        user_data[message.chat.id]['file_id'] = message.photo[-1].file_id
    else:
        bot.send_message(message.chat.id, "Iltimos, fayl yoki rasm yuboring!")
        bot.register_next_step_handler(message, process_test_file)
        return
    bot.send_message(message.chat.id, "Test tugash vaqtini kiriting (Masalan format: DD.MM.YYYY HH:MM):")
    bot.register_next_step_handler(message, process_deadline)

def process_deadline(message):
    try:
        deadline = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        reactivation_time = deadline + timedelta(hours=2)
        user_data[message.chat.id]['deadline'] = deadline
        user_data[message.chat.id]['reactivation'] = reactivation_time
        
        if user_data[message.chat.id]['type'] == 'ms':
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add("To'liq Rasch", "Hamtest Rasch", "Oddiy")
            bot.send_message(message.chat.id, "MS Test qanday modelda tekshirilsin?", reply_markup=markup)
            bot.register_next_step_handler(message, process_ms_rasch)
        else:
            save_test_to_db(message.chat.id)
    except ValueError:
        bot.send_message(message.chat.id, "Xato format! DD.MM.YYYY HH:MM shaklida kiriting:")
        bot.register_next_step_handler(message, process_deadline)

def process_ms_rasch(message):
    mode_map = {"To'liq Rasch": 'full', "Hamtest Rasch": 'half', "Oddiy": 'none'}
    user_data[message.chat.id]['rasch_mode'] = mode_map.get(message.text, 'none')
    save_test_to_db(message.chat.id)
    bot.send_message(message.chat.id, "Tasdiqlanmoqda...", reply_markup=types.ReplyKeyboardRemove())

def save_test_to_db(chat_id):
    data = user_data.get(chat_id)
    if not data: return
    try:
        cursor.execute('''
            INSERT INTO tests (test_code, creator_id, test_type, subject, test_name, file_id, deadline, reactivation_time, rasch_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['code'], data['creator'], data['type'], data.get('subject'), data['name'], data['file_id'], data['deadline'], data['reactivation'], data.get('rasch_mode', 'none')))
        conn.commit()
        bot.send_message(chat_id, f"✅ Test muvaffaqiyatli saqlandi! Kod: {data['code']}")
    except sqlite3.IntegrityError:
        bot.send_message(chat_id, "⚠️ Bu test kodi band. Boshqa kod bilan qayta urinib ko'ring.")
    user_data.pop(chat_id, None)

# --- 5. TEST ISHLASH JARAYONI ---
def process_solve_code(message):
    code = message.text
    cursor.execute('SELECT test_type FROM tests WHERE test_code = ?', (code,))
    test = cursor.fetchone()
    
    if test:
        mini_app_url = f"https://SIZNING-NETLIFY-SAYTINGIZ.netlify.app/?test_code={code}&user_id={message.from_user.id}"
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton(text="Javoblarni kiritish ✍️", web_app=types.WebAppInfo(url=mini_app_url))
        markup.add(btn)
        bot.send_message(message.chat.id, f"✅ `{code}` - kodli test topildi!\n\nPastdagi tugmani bosib javoblaringizni kiriting:", reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Bunday test kodi topilmadi. Iltimos, kodni tekshirib qayta kiriting.")

# --- 6. TEST BAZA (/baza) ---
def get_subjects_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    subjects = ["Matematika", "Ingliz tili", "O'zbek tili", "Fizika", "Kimyo", "Biologiya"]
    buttons = [types.InlineKeyboardButton(sub, callback_data=f"sub_{sub}") for sub in subjects]
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['baza'])
def test_baza(message):
    bot.send_message(message.chat.id, "Qaysi fan bo'yicha testlarni ko'rmoqchisiz?", reply_markup=get_subjects_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def show_subject_tests(call):
    subject = call.data.split("_")[1]
    now = datetime.now()
    cursor.execute('''
        SELECT test_code, test_name, test_type 
        FROM tests 
        WHERE subject = ? AND (deadline > ? OR reactivation_time <= ?)
    ''', (subject, now, now))
    tests = cursor.fetchall()
    
    if not tests:
        bot.send_message(call.message.chat.id, f"📂 {subject} fani bo'yicha hozircha arxivda testlar yo'q.")
        bot.answer_callback_query(call.id)
        return
        
    markup = types.InlineKeyboardMarkup(row_width=1)
    response = f"📚 **{subject} fanidan mavjud testlar:**\n\nIltimos, ishlamoqchi bo'lgan testingizni tanlang:"
    for t_code, t_name, t_type in tests:
        btn_text = f"📝 {t_name} ({t_type.upper()})"
        callback_data = f"solve_{t_code}" 
        markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=callback_data))
        
    bot.send_message(call.message.chat.id, response, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("solve_"))
def direct_solve_test(call):
    code = call.data.split("_")[1]
    cursor.execute('SELECT file_id, test_type FROM tests WHERE test_code = ?', (code,))
    test = cursor.fetchone()
    
    if test:
        file_id, t_type = test
        caption_text = f"🔖 **Test kodi:** `{code}`\n\n📥 Test fayli yuklandi.\n\nYo'riqnoma: Testni ishlab bo'lgach, **/app** yoki **/ms** menyusi orqali javoblaringizni tekshirib oling."
        try:
            bot.send_document(call.message.chat.id, file_id, caption=caption_text, parse_mode='Markdown')
        except:
            bot.send_photo(call.message.chat.id, file_id, caption=caption_text, parse_mode='Markdown')
    else:
        bot.send_message(call.message.chat.id, "⚠️ Kechirasiz, bu test fayli bazadan topilmadi.")
    bot.answer_callback_query(call.id)

# --- 7. NATIJALAR ---
@bot.message_handler(commands=['testlarim'])
def my_results(message):
    cursor.execute('SELECT test_code, correct_count, score, grade FROM results WHERE user_id = ?', (message.from_user.id,))
    results = cursor.fetchall()
    
    if results:
        res_text = "📈 **Sizning natijalaringiz:**\n\n"
        for r in results:
            grade_str = f"| Daraja: {r[3]}" if r[3] else ""
            res_text += f"🔖 Test: {r[0]} | To'g'ri: {r[1]} | Ball: {r[2]} {grade_str}\n"
        bot.send_message(message.chat.id, res_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "Siz hali test ishlamagansiz.")

# --- 8. ADMIN KONDANDALARI ---
@bot.message_handler(commands=['admin_natija'])
def admin_results(message):
    msg = bot.send_message(message.chat.id, "Siz kiritgan test kodini yozing:")
    bot.register_next_step_handler(msg, process_admin_results)

def generate_ms_results_file(test_code, db_results):
    columns = ["Ismi", "To'g'ri", "Qobiliyat", "Ball", "Foiz", "Daraja", "Majburiy", "Birinchi fan", "Ikkinchi fan", "Vaqt"]
    df = pd.DataFrame(db_results, columns=columns)
    file_path = f"natijalar_{test_code}.xlsx"
    df.to_excel(file_path, index=False)
    return file_path

def process_admin_results(message):
    code = message.text
    cursor.execute('SELECT creator_id, test_type FROM tests WHERE test_code = ?', (code,))
    test = cursor.fetchone()
    
    if not test:
        bot.send_message(message.chat.id, "❌ Bunday test kodi topilmadi.")
        return
        
    creator_id, test_type = test
    if creator_id != message.from_user.id:
        bot.send_message(message.chat.id, "⚠️ Siz faqat o'zingiz yaratgan test natijalarini ko'ra olasiz.")
        return

    if test_type == 'ms':
        cursor.execute('''
            SELECT u.full_name, r.correct_count, r.qobiliyat, r.score, r.foiz, r.grade, r.majburiy, r.fan_1, r.fan_2, r.submitted_at 
            FROM results r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.test_code = ? 
            ORDER BY r.score DESC
        ''', (code,))
        results = cursor.fetchall()
        if results:
            file_path = generate_ms_results_file(code, results)
            with open(file_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"📊 {code} - Excel natijalar")
            os.remove(file_path)
        else:
            bot.send_message(message.chat.id, "Hech kim ishlamagan.")
    else:
        cursor.execute('''
            SELECT u.full_name, r.correct_count, r.score 
            FROM results r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.test_code = ? 
            ORDER BY r.score DESC
        ''', (code,))
        results = cursor.fetchall()
        if results:
            res_text = f"📊 **{code} natijalari:**\n\n"
            for i, r in enumerate(results, 1):
                res_text += f"{i}. 👤 {r[0]} | To'g'ri: {r[1]} | Ball: {r[2]:.2f}\n"
            bot.send_message(message.chat.id, res_text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "Hech kim ishlamagan.")

if __name__ == '__main__':
    print("Bot ishga tushmoqda...")
    bot.polling(none_stop=True)
