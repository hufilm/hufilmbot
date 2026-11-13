
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
from flask import Flask, render_template_string, request, redirect, url_for
from datetime import datetime

# === SOZLAMALAR ===
BOT_TOKEN = "9217478644:AAG4feyRXGijMM4mAMPI-NosT-dbwaCbtl0"
CHANNEL_ID = "@HUFilmlar"  # Majburiy obuna kanali
ADMIN_USERNAME = "HuFilmAdmin"
ADMIN_ID = 6865833003      # Sizning Telegram ID raqamingiz
PAYMENT_CARD = "8600 0000 0000 0000"
WEB_APP_URL = "https://hufilmbot.onrender.com"  # Render.com'dagi havolangiz

# Xotira bazalari
MOVIES = {
    "5": {
        "type": "text",
        "caption": "🎬 Kino: Forsaj 9\n📄 Janr: Jangari",
        "views": 0
    }
}
USERS = set()
REFERRALS = {}
ERROR_LOGS = []

# FSM holatlari
class AddMovieState(StatesGroup):
    waiting_for_movie_file = State()
    waiting_for_code_choice = State()
    waiting_for_custom_code = State()
    waiting_for_genre = State()
    waiting_for_cover_choice = State()
    waiting_for_custom_cover = State()
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

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].split("_")[1])
            if referrer_id != user_id and referrer_id not in REFERRALS:
                REFERRALS[referrer_id] = REFERRALS.get(referrer_id, 0) + 1
        except ValueError as e:
            ERROR_LOGS.append(f"[{datetime.now().strftime('%H:%M:%S')}] Referal xatosi: {e}")

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

# === ADMIN PANEL (Faqat sizga Web Panel tugmasi bilan chiqadi) ===
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
    movies_list = "\n".join([f"🔹 Kod: <code>{code}</code> | Ko'rishlar: {m.get('views', 0)}" for code, m in MOVIES.items()]) if MOVIES else "Kinolar yo'q."
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

# Foydalanuvchi bo'limlari
@dp.message(F.text == "💳 To'lov tizimlari")
async def payment_handler(message: types.Message):
    pay_text = (
        "💳 **To'lov Tizimlari va Rekvizitlar:**\n\n"
        "Premium obuna uchun to'lovni quyidagi karta raqamiga o'tkazing:\n\n"
        f"💳 <code>{PAYMENT_CARD}</code>\n\n"
        f"Chekni adminga yuboring: @{ADMIN_USERNAME}"
    )
    await message.answer(pay_text, reply_markup=main_menu_kb, parse_mode="HTML")

@dp.message(F.text == "💎 Premium")
async def premium_handler(message: types.Message):
    await message.answer(f"💎 **Premium Obuna**\n\nImkoniyatlarni kengaytirish uchun @{ADMIN_USERNAME} bilan bog'laning.")

@dp.message(F.text == "🔗 Referal")
async def referral_handler(message: types.Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    invited_count = REFERRALS.get(user_id, 0)
    
    ref_text = (
        "🔗 **Referal Tizimi**\n\n"
        "Do'stlaringizni taklif qiling!\n\n"
        f"📎 **Sizning havolangiz:**\n{ref_link}\n\n"
        f"👥 Taklif qilinganlar: <b>{invited_count} ta</b>"
    )
    await message.answer(ref_text, reply_markup=main_menu_kb, parse_mode="HTML")

# Kino qo'shish FSM
@dp.message(F.text == "➕ Kino qo'shish")
async def start_add_movie(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🎬 Kinoni (video yoki fayl) yuboring:")
    await state.set_state(AddMovieState.waiting_for_movie_file)

@dp.message(AddMovieState.waiting_for_movie_file, F.video | F.document)
async def process_movie_file(message: types.Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    file_type = "video" if message.video else "document"
    auto_code = str(len(MOVIES) + 1)
    
    await state.update_data(file_id=file_id, file_type=file_type, auto_code=auto_code)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ha", callback_data="code_yes"), InlineKeyboardButton(text="Yo'q", callback_data="code_no")]
    ])
    await message.answer(f"✅ Kod: <b>{auto_code}</b>. Shu kod qolsinmi?", reply_markup=kb, parse_mode="HTML")
    await state.set_state(AddMovieState.waiting_for_code_choice)

@dp.callback_query(AddMovieState.waiting_for_code_choice, F.data.in_({"code_yes", "code_no"}))
async def process_code_choice(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if callback.data == "code_yes":
        await state.update_data(final_code=data['auto_code'])
        await callback.message.answer("✍️ Janrni kiriting:")
        await state.set_state(AddMovieState.waiting_for_genre)
    else:
        await callback.message.answer("✍️ O'zingiz kod kiriting:")
        await state.set_state(AddMovieState.waiting_for_custom_code)
    await callback.answer()

@dp.message(AddMovieState.waiting_for_custom_code)
async def process_custom_code(message: types.Message, state: FSMContext):
    await state.update_data(final_code=message.text)
    await message.answer("✍️ Janrni kiriting:")
    await state.set_state(AddMovieState.waiting_for_genre)

@dp.message(AddMovieState.waiting_for_genre)
async def process_genre(message: types.Message, state: FSMContext):
    await state.update_data(genre=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ha", callback_data="cover_yes"), InlineKeyboardButton(text="Yo'q", callback_data="cover_no")]
    ])
    await message.answer("🖼️ Cover bo'ladimi?", reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_cover_choice)

@dp.callback_query(AddMovieState.waiting_for_cover_choice, F.data.in_({"cover_yes", "cover_no"}))
async def process_cover_choice(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cover_yes":
        await state.update_data(cover="default")
        await show_preview(callback.message, state)
    else:
        await callback.message.answer("📸 Rasm yuboring:")
        await state.set_state(AddMovieState.waiting_for_custom_cover)
    await callback.answer()

@dp.message(AddMovieState.waiting_for_custom_cover, F.photo)
async def process_custom_cover(message: types.Message, state: FSMContext):
    await state.update_data(cover=message.photo[-1].file_id)
    await show_preview(message, state)

async def show_preview(message: types.Message, state: FSMContext):
    data = await state.get_data()
    preview_text = f"🔢 Kod: {data['final_code']}\n📄 Janr: {data['genre']}\n\nQo'yilsinmi?"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha", callback_data="publish_yes"), InlineKeyboardButton(text="✏️ Edit", callback_data="publish_edit")]
    ])
    await message.answer(preview_text, reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_confirmation)

@dp.callback_query(AddMovieState.waiting_for_confirmation, F.data.in_({"publish_yes", "publish_edit"}))
async def process_final_publish(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "publish_yes":
        data = await state.get_data()
        MOVIES[data['final_code']] = {
            "type": data['file_type'],
            "file_id": data['file_id'],
            "caption": f"🎬 Kino kodi: {data['final_code']}\n📄 Janr: {data['genre']}\n👨‍💻 Admin: @{ADMIN_USERNAME}",
            "views": 0
        }
        await callback.message.answer("🎉 Kino qo'shildi!", reply_markup=admin_menu_kb)
    else:
        await callback.message.answer("🔄 Bekor qilindi.", reply_markup=admin_menu_kb)
    await state.clear()
    await callback.answer()

# Kino qidirish
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
        await message.answer(f"❌ Kino topilmadi.\n👨‍💻 Admin: @{ADMIN_USERNAME}")


# === FLASK VEB-PANEL ===
app = Flask(__name__)

WEB_TEMPLATE = """
<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <title>HUFilmBot - Veb Boshqaruv Paneli</title>
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
        <h1>🎬 HUFilmBot Veb Paneli</h1>
        
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
                <th>Janr / Ma'lumot</th>
                <th>Ko'rishlar</th>
                <th>Amal</th>
            </tr>
            {% for code, movie in movies.items() %}
            <tr>
                <td><b>{{ code }}</b></td>
                <td>{{ movie.caption }}</td>
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
    
