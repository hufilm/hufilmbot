import asyncio
import logging
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
from flask import Flask, render_template_string, redirect, url_for
from datetime import datetime

# === SOZLAMALAR ===
BOT_TOKEN = "9217478644:AAG4feyRXGijMM4mAMPI-NosT-dbwaCbtl0"
CHANNEL_ID = "@HUFilmlar"  # Majburiy obuna kanali
ADMIN_ID = 6865833003      # Sizning Telegram ID raqamingiz
ADMIN_USERNAME = "HuFilmAdmin"
WEB_APP_URL = "https://hufilmbot.onrender.com"  # Render.com'dagi havolangiz

# Xotira bazalari
MOVIES = {
    "101": {
        "type": "video",
        "file_id": "BQACAgIAAxkBAA...", 
        "title": "Tungi shahar",
        "description": "Shahar tunda uyg'onadi...",
        "language": "O'zbek",
        "genre": "Jangari",
        "access": "Hamma uchun",
        "caption": "🎬 Kino kodi: 101\n📌 Nomi: Tungi shahar\n🌐 Til: O'zbek | 📄 Janr: Jangari",
        "views": 0
    }
}
USERS = set()
ERROR_LOGS = []

# === FSM HOLATLARI (Admin kino qo'shish 7-qadamlik konstruktori) ===
class AddMovieState(StatesGroup):
    waiting_for_file = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_language = State()
    waiting_for_genre = State()
    waiting_for_access = State()
    waiting_for_confirmation = State()

class BroadcastState(StatesGroup):
    waiting_for_ad_content = State()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === MENYULAR ===
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💳 To'lov tizimlari"), KeyboardButton(text="💎 Premium")],
        [KeyboardButton(text="🔗 Referal"), KeyboardButton(text="🆘 So'z")]
    ],
    resize_keyboard=True
)

admin_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="🎬 Kinolar"), KeyboardButton(text="📌 Postlar")],
        [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="🎯 Reklama")],
        [KeyboardButton(text="💳 To'lov tizimlari"), KeyboardButton(text="💎 Premium")],
        [KeyboardButton(text="🔗 Referal"), KeyboardButton(text="⬅️ Chiqish")]
    ],
    resize_keyboard=True
)

async def check_sub_channel(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except TelegramBadRequest as e:
        ERROR_LOGS.append(f"[{datetime.now().strftime('%H:%M:%S')}] Obuna xatosi: {e}")
    return False

def get_sub_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url="https://t.me/HUFilmlar")],
            [InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")]
        ]
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in USERS:
        USERS.add(user_id)

    if not await check_sub_channel(user_id):
        await message.answer(
            "❌ Botdan foydalanish uchun quyidagi kanalga obuna bo'ling:",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    welcome_text = (
        "🎬 **HUFILM BOTIGA XUSH KELIBSIZ!**\n\n"
        "🍿 Sevimli kinolaringizni topish uchun kodni yuboring va tomosha qilishni boshlang! ❤️"
    )
    await message.answer(welcome_text, reply_markup=main_menu_kb, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await check_sub_channel(user_id):
        await callback.message.delete()
        welcome_text = (
            "🎬 **HUFILM BOTIGA XUSH KELIBSIZ!**\n\n"
            "🍿 Sevimli kinolaringizni topish uchun kodni yuboring va tomosha qilishni boshlang! ❤️"
        )
        await callback.message.answer(welcome_text, reply_markup=main_menu_kb, parse_mode="Markdown")
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

# === ADMIN PANEL ===
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Kechirasiz, bu buyruq faqat bot admini uchun.")
        return
    
    total_views = sum(m.get("views", 0) for m in MOVIES.values())
    admin_panel_text = (
        "🎬 **HUFilmBot 💎**\n"
        "<i>Kino boshqaruv paneli</i>\n\n"
        f"🎬 <b>{len(MOVIES)}</b> kino  •  👥 <b>{len(USERS)}</b> obunachi  •  👁 <b>{total_views}</b> ko'rish\n\n"
        "Hammasini shu yerdan yoki quyidagi Web Panel orqali boshqarasiz:"
    )
    
    web_panel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Web Panelga o'tish", url=WEB_APP_URL)]
        ]
    )
    
    await message.answer(admin_panel_text, reply_markup=admin_menu_kb, parse_mode="HTML")
    await message.answer("🔗 Boshqaruv uchun maxsus veb-havola:", reply_markup=web_panel_kb)

@dp.message(F.text == "⬅️ Chiqish")
async def back_to_main(message: types.Message):
    await message.answer("🏠 Bosh menyu", reply_markup=main_menu_kb)

@dp.message(F.text == "🆘 So'z")
async def contact_admin(message: types.Message):
    user_id = message.from_user.id
    if not await check_sub_channel(user_id):
        await message.answer("❌ Avval kanalga obuna bo'ling!", reply_markup=get_sub_keyboard(), parse_mode="Markdown")
        return
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨‍💻 Adminga yozish", url=f"https://t.me/{ADMIN_USERNAME}")]
        ]
    )
    await message.answer("🆘 Savollar yoki murojaat uchun adminga yozing:", reply_markup=kb)

# Admin tugmalari
@dp.message(F.text == "📊 Statistika")
async def admin_stat(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    total_views = sum(m.get("views", 0) for m in MOVIES.values())
    stat_text = (
        "📊 **To'liq Bot Statistikasi:**\n\n"
        f"👥 Jami obunachilar: {len(USERS)} ta\n"
        f"🎬 Jami kinolar: {len(MOVIES)} ta\n"
        f"👁 Jami kino ko'rishlar: {total_views} marta"
    )
    await message.answer(stat_text, reply_markup=admin_menu_kb, parse_mode="Markdown")

@dp.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(f"👥 **Foydalanuvchilar:**\n\nJami faol: {len(USERS)} ta.", reply_markup=admin_menu_kb, parse_mode="Markdown")

@dp.message(F.text == "🎬 Kinolar")
async def admin_movies_list(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    movies_list = "\n".join([f"🔹 Kod: <code>{code}</code> | Nomi: {m.get('title')} | Ko'rishlar: {m.get('views', 0)}" for code, m in MOVIES.items()]) if MOVIES else "Kinolar yo'q."
    await message.answer(f"🎬 **Kinolar ro'yxati:**\n\n{movies_list}", reply_markup=admin_menu_kb, parse_mode="HTML")

@dp.message(F.text == "📌 Postlar")
async def admin_posts(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📌 Postlar boshqaruvi.", reply_markup=admin_menu_kb)

@dp.message(F.text == "🎯 Reklama")
async def admin_ads_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📢 Barcha obunachilarga yubormoqchi bo'lgan xabar, rasm yoki videongizni yuboring:")
    await state.set_state(BroadcastState.waiting_for_ad_content)

@dp.message(BroadcastState.waiting_for_ad_content)
async def process_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    sent_count, blocked_count = 0, 0
    status_msg = await message.answer("⏳ Reklama tarqatilmoqda...")

    for user_id in USERS:
        try:
            await message.send_copy(chat_id=user_id)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            blocked_count += 1
            ERROR_LOGS.append(f"[{datetime.now().strftime('%H:%M:%S')}] Reklama xatosi: {e}")

    await status_msg.edit_text(f"✅ Yuborildi: {sent_count} ta\n❌ Bloklaganlar: {blocked_count} ta", reply_markup=admin_menu_kb)

# === KINO QO'SHISH KONSTRUKTORI (7-QADAM) ===
@dp.message(F.text == "➕ Kino qo'shish")
async def start_add_movie(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🎬 1-qadam: Kino videosini yuboring (yoki kanaldan forward qiling):")
    await state.set_state(AddMovieState.waiting_for_file)

@dp.message(AddMovieState.waiting_for_file, F.video | F.document)
async def process_movie_file(message: types.Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    file_type = "video" if message.video else "document"
    auto_code = str(100 + len(MOVIES) + 1)
    
    await state.update_data(file_id=file_id, file_type=file_type, code=auto_code)
    await message.answer(f"✅ Avto kod tayyor: <b>{auto_code}</b>\n\n📝 2-qadam: Kino nomini yuboring:", parse_mode="HTML")
    await state.set_state(AddMovieState.waiting_for_title)

@dp.message(AddMovieState.waiting_for_title)
async def process_movie_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("📄 3-qadam: Qisqacha tavsif yozing (o'tkazib yuborish uchun istalgan so'z yozing):")
    await state.set_state(AddMovieState.waiting_for_description)

@dp.message(AddMovieState.waiting_for_description)
async def process_movie_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"), InlineKeyboardButton(text="🇷🇺 Rus", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 Ingliz", callback_data="lang_en"), InlineKeyboardButton(text="🇹🇷 Turk", callback_data="lang_tr")]
    ])
    await message.answer("🌐 4-qadam: Tilni tanlang:", reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_language)

@dp.callback_query(AddMovieState.waiting_for_language, F.data.startswith("lang_"))
async def process_movie_lang(callback: types.CallbackQuery, state: FSMContext):
    lang_map = {"lang_uz": "O'zbek", "lang_ru": "Rus", "lang_en": "Ingliz", "lang_tr": "Turk"}
    lang = lang_map.get(callback.data, "O'zbek")
    await state.update_data(language=lang)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Jangari", callback_data="genre_jangari"), InlineKeyboardButton(text="😂 Komediya", callback_data="genre_komediya")],
        [InlineKeyboardButton(text="🚀 Fantastika", callback_data="genre_fantastika"), InlineKeyboardButton(text="🎭 Drama", callback_data="genre_drama")]
    ])
    await callback.message.edit_text(f"✅ Til: {lang}\n\n🎬 Janrni tanlang:", reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_genre)
    await callback.answer()

@dp.callback_query(AddMovieState.waiting_for_genre, F.data.startswith("genre_"))
async def process_movie_genre(callback: types.CallbackQuery, state: FSMContext):
    genre = callback.data.split("_")[1].capitalize()
    await state.update_data(genre=genre)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Hamma uchun", callback_data="access_all")],
        [InlineKeyboardButton(text="💎 Faqat VIP obunachilar", callback_data="access_vip")],
        [InlineKeyboardButton(text="💳 Pullik", callback_data="access_paid")]
    ])
    await callback.message.edit_text(f"✅ Janr: {genre}\n\n👥 5-qadam: Kimlar uchunligini tanlang:", reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_access)
    await callback.answer()

@dp.callback_query(AddMovieState.waiting_for_access, F.data.startswith("access_"))
async def process_movie_access(callback: types.CallbackQuery, state: FSMContext):
    access_map = {"access_all": "Hamma uchun", "access_vip": "Faqat VIP", "access_paid": "Pullik"}
    access = access_map.get(callback.data, "Hamma uchun")
    await state.update_data(access=access)
    
    data = await state.get_data()
    preview = (
        f"📋 **Kino ma'lumotlari tayyor:**\n"
        f"🔢 Kod: <code>{data['code']}</code>\n"
        f"📌 Nomi: {data['title']}\n"
        f"📄 Tavsif: {data['description']}\n"
        f"🌐 Til: {data['language']} | 🎭 Janr: {data['genre']}\n"
        f"👥 Ruxsat: {access}\n\n"
        f"Kino bazaga qo'yilsinmi?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, joylash", callback_data="pub_yes"), InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pub_no")]
    ])
    await callback.message.edit_text(preview, reply_markup=kb, parse_mode="HTML")
    await state.set_state(AddMovieState.waiting_for_confirmation)
    await callback.answer()

@dp.callback_query(AddMovieState.waiting_for_confirmation, F.data.in_({"pub_yes", "pub_no"}))
async def process_movie_publish(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "pub_yes":
        data = await state.get_data()
        MOVIES[data['code']] = {
            "type": data['file_type'],
            "file_id": data['file_id'],
            "title": data['title'],
            "description": data['description'],
            "language": data['language'],
            "genre": data['genre'],
            "access": data['access'],
            "caption": f"🎬 Kino kodi: {data['code']}\n📌 Nomi: {data['title']}\n🌐 Til: {data['language']} | 📄 Janr: {data['genre']}\n👥 {data['access']}\n👨‍💻 Admin: @{ADMIN_USERNAME}",
            "views": 0
        }
        
        # Tugmalar: Ko'rish, Tahrirlash, Qism qo'shish, O'chirish
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👁 Ko'rish", callback_data=f"m_view_{data['code']}"), InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"m_edit_{data['code']}")],
            [InlineKeyboardButton(text="➕ Qism qo'shish", callback_data=f"m_part_{data['code']}"), InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"m_del_{data['code']}")]
        ])
        await callback.message.edit_text(f"🎉 **{data['title']}** muvaffaqiyatli qo'shildi!", reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text("🔄 Bekor qilindi.", reply_markup=admin_menu_kb)
    await state.clear()
    await callback.answer()

# === KINO QIDIRISH (KOD ORQALI) ===
@dp.message(F.text.regexp(r'^\d+$'))
async def search_movie(message: types.Message):
    user_id = message.from_user.id
    if not await check_sub_channel(user_id):
        await message.answer("❌ Avval kanalga obuna bo'ling!", reply_markup=get_sub_keyboard(), parse_mode="Markdown")
        return

    code = message.text
    if code in MOVIES:
        movie = MOVIES[code]
        movie["views"] += 1
        if movie["type"] == "video":
            await message.answer_video(video=movie["file_id"], caption=movie["caption"])
        else:
            await message.answer_document(document=movie["file_id"], caption=movie["caption"])
    else:
        await message.answer(f"❌ Kechirasiz, bunday kodli kino topilmadi.\n👨‍💻 Admin: @{ADMIN_USERNAME}")


# === FLASK WEB PANEL ===
app = Flask(__name__)

WEB_TEMPLATE = """
<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <title>HUFilmBot - Web Boshqaruv Paneli</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h1, h2 { color: #38bdf8; text-align: center; }
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px; }
        .stat-card { background: #334155; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-card h3 { margin: 0; font-size: 24px; color: #f43f5e; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 10px; border-bottom: 1px solid #475569; text-align: left; }
        th { background: #0284c7; color: white; }
        .btn { background: #e11d48; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; text-decoration: none; }
        .btn:hover { background: #be123c; }
        .logs { background: #000; color: #4ade80; padding: 12px; border-radius: 6px; font-family: monospace; max-height: 150px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 HUFilmBot Web Paneli</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <p>Jami Obunachilar</p>
                <h3>{{ users_count }}</h3>
            </div>
            <div class="stat-card">
                <p>Kinolar Soni</p>
                <h3>{{ movies_count }}</h3>
            </div>
            <div class="stat-card">
                <p>Jami Ko'rishlar</p>
                <h3>{{ total_views }}</h3>
            </div>
        </div>

        <h2>🎬 Kinolar Boshqaruvi</h2>
        <table>
            <tr>
                <th>Kod</th>
                <th>Nomi & Janr</th>
                <th>Ko'rishlar</th>
                <th>Amal</th>
            </tr>
            {% for code, movie in movies.items() %}
            <tr>
                <td><b>{{ code }}</b></td>
                <td>{{ movie.title }} ({{ movie.genre }})</td>
                <td>{{ movie.views }} marta</td>
                <td>
                    <form action="/delete_movie/{{ code }}" method="POST" style="margin:0;">
                        <button class="btn" type="submit">O'chirish</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>

        <h2>⚠️ Xatoliklar Jurnali (Logs)</h2>
        <div class="logs">
            {% if logs %}
                {% for log in logs %}
                    <p>{{ log }}</p>
                {% endfor %}
            {% else %}
                <p>Hozircha xatoliklar mavjud emas. Bot mukammal ishlamoqda! ✅</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def web_dashboard():
    total_views = sum(m.get("views", 0) for m in MOVIES.values())
    return render_template_string(
        WEB_TEMPLATE,
        users_count=len(USERS),
        movies_count=len(MOVIES),
        total_views=total_views,
        movies=MOVIES,
        logs=ERROR_LOGS
    )

@app.route('/delete_movie/<code>', methods=['POST'])
def delete_movie(code):
    if code in MOVIES:
        del MOVIES[code]
        ERROR_LOGS.append(f"[{datetime.now().strftime('%H:%M:%S')}] Kino o'chirildi: Kod {code}")
    return redirect(url_for('web_dashboard'))

def run_flask():
    app.run(host="0.0.0.0", port=10000)

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

