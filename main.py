import asyncio
import logging
import os
import threading
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
from flask import Flask, render_template_string, redirect, url_for

# === SOZLAMALAR ===
BOT_TOKEN = "9217478644:AAG4feyRXGijMM4mAMPI-NosT-dbwaCbtl0"
CHANNEL_ID = "@HUFilmlar"
ADMIN_ID = 6865833003
ADMIN_USERNAME = "HuFilmAdmin"
PAYMENT_CARD = "8600 0000 0000 0000"
WEB_APP_URL = "https://hufilmbot.onrender.com"

# === BAZALAR ===
MOVIES = {}  # Faqat siz qo'shgan haqiqiy kinolar shu yerda saqlanadi
USERS = set()
REFERRALS = {}
ERROR_LOGS = []


def add_log(text: str):
    ERROR_LOGS.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")
    if len(ERROR_LOGS) > 50:
        ERROR_LOGS.pop(0)


# === FSM HOLATLARI ===
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
        [KeyboardButton(text="🔗 Referal"), KeyboardButton(text="🆘 So'z")],
    ],
    resize_keyboard=True,
)

admin_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="🎬 Kinolar"), KeyboardButton(text="📌 Postlar")],
        [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="🎯 Reklama")],
        [KeyboardButton(text="💳 To'lov tizimlari"), KeyboardButton(text="💎 Premium")],
        [KeyboardButton(text="🔗 Referal"), KeyboardButton(text="⬅️ Chiqish")],
    ],
    resize_keyboard=True,
)

ADMIN_BUTTON_TEXTS = {
    "📊 Statistika",
    "👥 Foydalanuvchilar",
    "🎬 Kinolar",
    "📌 Postlar",
    "➕ Kino qo'shish",
    "🎯 Reklama",
    "💳 To'lov tizimlari",
    "💎 Premium",
    "🔗 Referal",
    "🆘 So'z",
    "⬅️ Chiqish",
}


async def check_sub_channel(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in {"member", "administrator", "creator"}
    except TelegramBadRequest as e:
        add_log(f"Obuna tekshirish xatosi: {e}")
        return False
    except Exception as e:
        add_log(f"Noma'lum obuna xatosi: {e}")
        return False


def get_sub_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url="https://t.me/HUFilmlar")],
            [InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")],
        ]
    )


WELCOME_TEXT = (
    "🎬 <b>HUFILM BOTIGA XUSH KELIBSIZ!</b>\n\n"
    "🍿 Sevimli kinolaringizni topish uchun kodni yuboring va tomosha qilishni boshlang! ❤️"
)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    USERS.add(user_id)

    args = (message.text or "").split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].split("_", 1)[1])
            if referrer_id != user_id:
                REFERRALS[referrer_id] = REFERRALS.get(referrer_id, 0) + 1
        except ValueError:
            pass

    if not await check_sub_channel(user_id):
        await message.answer(
            "❌ Botdan foydalanish uchun quyidagi kanalga obuna bo'ling:",
            reply_markup=get_sub_keyboard(),
        )
        return

    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb, parse_mode="HTML")


@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    USERS.add(user_id)
    if await check_sub_channel(user_id):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(WELCOME_TEXT, reply_markup=main_menu_kb, parse_mode="HTML")
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Bu bo'lim faqat admin uchun.")
        return

    total_views = sum(m.get("views", 0) for m in MOVIES.values())
    panel_text = (
        "🎬 <b>HUFilmBot 💎</b>\n"
        "<i>Kino boshqaruv paneli</i>\n\n"
        f"🎬 <b>{len(MOVIES)}</b> kino  •  👥 <b>{len(USERS)}</b> obunachi  •  👁 <b>{total_views}</b> ko'rish"
    )
    web_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🌐 Web Panelga o'tish", url=WEB_APP_URL)]]
    )
    await message.answer(panel_text, reply_markup=admin_menu_kb, parse_mode="HTML")
    await message.answer("🔗 Boshqaruv veb-paneli:", reply_markup=web_kb)


@dp.message(F.text == "⬅️ Chiqish")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Bosh menyu", reply_markup=main_menu_kb)


@dp.message(F.text == "🆘 So'z")
async def contact_admin(message: types.Message):
    if not await check_sub_channel(message.from_user.id):
        await message.answer("❌ Avval kanalga obuna bo'ling!", reply_markup=get_sub_keyboard())
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="👨‍💻 Adminga yozish", url=f"https://t.me/{ADMIN_USERNAME}")]]
    )
    await message.answer("🆘 Savol yoki murojaat uchun adminga yozing:", reply_markup=kb)


@dp.message(F.text == "💳 To'lov tizimlari")
async def payment_handler(message: types.Message):
    text = (
        "💳 <b>To'lov tizimlari</b>\n\n"
        f"Karta raqami: <code>{PAYMENT_CARD}</code>\n"
        f"To'lov chekini yuboring: @{ADMIN_USERNAME}"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "💎 Premium")
async def premium_handler(message: types.Message):
    await message.answer(f"💎 <b>Premium obuna</b> uchun @{ADMIN_USERNAME} bilan bog'laning.", parse_mode="HTML")


@dp.message(F.text == "🔗 Referal")
async def referral_handler(message: types.Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    count = REFERRALS.get(user_id, 0)
    await message.answer(
        f"🔗 <b>Referal havolangiz:</b>\n{ref_link}\n\n👥 Taklif qilganlaringiz: <b>{count} ta</b>",
        parse_mode="HTML",
    )


# === ADMIN BO'LIMLARI ===
@dp.message(F.text == "📊 Statistika")
async def admin_stat(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total_views = sum(m.get("views", 0) for m in MOVIES.values())
    await message.answer(
        f"📊 <b>Statistika:</b>\n\n"
        f"👥 Obunachilar: <b>{len(USERS)}</b>\n"
        f"🎬 Kinolar: <b>{len(MOVIES)}</b>\n"
        f"👁 Ko'rishlar: <b>{total_views}</b>",
        parse_mode="HTML",
    )


@dp.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(f"👥 Jami foydalanuvchilar: <b>{len(USERS)} ta</b>", parse_mode="HTML")


@dp.message(F.text == "🎬 Kinolar")
async def admin_movies_list(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not MOVIES:
        await message.answer("🎬 Hozircha kinolar qo'shilmagan.")
        return
    lines = [
        f"🔹 Kod: <code>{code}</code> | {m['title']} | 👁 {m.get('views', 0)}"
        for code, m in MOVIES.items()
    ]
    await message.answer("🎬 <b>Kinolar ro'yxati:</b>\n\n" + "\n".join(lines), parse_mode="HTML")


@dp.message(F.text == "📌 Postlar")
async def admin_posts(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(f"📌 Majburiy obuna kanali: {CHANNEL_ID}")


@dp.message(F.text == "🎯 Reklama")
async def admin_ads_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📢 Obunachilarga yuboriladigan xabar, rasm yoki videoni yuboring:")
    await state.set_state(BroadcastState.waiting_for_ad_content)


@dp.message(BroadcastState.waiting_for_ad_content)
async def process_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    sent, failed = 0, 0
    status = await message.answer("⏳ Reklama yuborilmoqda...")
    for uid in list(USERS):
        try:
            await message.send_copy(chat_id=uid)
            sent += 1
            await asyncio.sleep(0.04)
        except Exception as e:
            failed += 1
            add_log(f"Reklama xatosi ({uid}): {e}")
    await status.edit_text(f"✅ Yuborildi: {sent} ta\n❌ Yetib bormadi: {failed} ta")


# === 7-QADAMLIK KINO KONSTRUKTORI ===
@dp.message(F.text == "➕ Kino qo'shish")
async def start_add_movie(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🎬 1-qadam: Kino videosini yoki faylini yuboring:")
    await state.set_state(AddMovieState.waiting_for_file)


@dp.message(AddMovieState.waiting_for_file, F.video | F.document)
async def process_movie_file(message: types.Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    file_type = "video" if message.video else "document"
    code = str(101 + len(MOVIES))
    while code in MOVIES:
        code = str(int(code) + 1)

    await state.update_data(file_id=file_id, file_type=file_type, code=code)
    await message.answer(f"✅ Kod: <b>{code}</b>\n\n📝 2-qadam: Kino nomini kiriting:", parse_mode="HTML")
    await state.set_state(AddMovieState.waiting_for_title)


@dp.message(AddMovieState.waiting_for_title, F.text)
async def process_movie_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("📄 3-qadam: Qisqacha tavsif kiriting:")
    await state.set_state(AddMovieState.waiting_for_description)


@dp.message(AddMovieState.waiting_for_description, F.text)
async def process_movie_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_O'zbek"),
                InlineKeyboardButton(text="🇷🇺 Rus", callback_data="lang_Rus"),
            ],
            [
                InlineKeyboardButton(text="🇬🇧 Ingliz", callback_data="lang_Ingliz"),
                InlineKeyboardButton(text="🇹🇷 Turk", callback_data="lang_Turk"),
            ],
        ]
    )
    await message.answer("🌐 4-qadam: Tilni tanlang:", reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_language)


@dp.callback_query(AddMovieState.waiting_for_language, F.data.startswith("lang_"))
async def process_movie_lang(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_", 1)[1]
    await state.update_data(language=lang)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔥 Jangari", callback_data="genre_Jangari"),
                InlineKeyboardButton(text="😂 Komediya", callback_data="genre_Komediya"),
            ],
            [
                InlineKeyboardButton(text="🚀 Fantastika", callback_data="genre_Fantastika"),
                InlineKeyboardButton(text="🎭 Drama", callback_data="genre_Drama"),
            ],
        ]
    )
    await callback.message.edit_text(f"✅ Til: {lang}\n\n🎭 5-qadam: Janrni tanlang:", reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_genre)
    await callback.answer()


@dp.callback_query(AddMovieState.waiting_for_genre, F.data.startswith("genre_"))
async def process_movie_genre(callback: types.CallbackQuery, state: FSMContext):
    genre = callback.data.split("_", 1)[1]
    await state.update_data(genre=genre)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Hamma uchun", callback_data="access_Hamma uchun")],
            [InlineKeyboardButton(text="💎 Faqat VIP", callback_data="access_Faqat VIP")],
        ]
    )
    await callback.message.edit_text(f"✅ Janr: {genre}\n\n👥 6-qadam: Ruxsat turini tanlang:", reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_access)
    await callback.answer()


@dp.callback_query(AddMovieState.waiting_for_access, F.data.startswith("access_"))
async def process_movie_access(callback: types.CallbackQuery, state: FSMContext):
    access = callback.data.split("_", 1)[1]
    await state.update_data(access=access)
    data = await state.get_data()

    preview = (
        "📋 <b>7-qadam: Tasdiqlash</b>\n\n"
        f"🔢 Kod: <code>{data['code']}</code>\n"
        f"📌 Nomi: <b>{data['title']}</b>\n"
        f"📄 Tavsif: {data['description']}\n"
        f"🌐 Til: {data['language']} | 🎭 Janr: {data['genre']}\n"
        f"👥 Ruxsat: {access}\n\n"
        "Kino qo'shilsinmi?"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data="pub_yes"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pub_no"),
            ]
        ]
    )
    await callback.message.edit_text(preview, reply_markup=kb, parse_mode="HTML")
    await state.set_state(AddMovieState.waiting_for_confirmation)
    await callback.answer()


@dp.callback_query(AddMovieState.waiting_for_confirmation, F.data.in_({"pub_yes", "pub_no"}))
async def process_movie_publish(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "pub_yes":
        data = await state.get_data()
        code = data["code"]
        caption = (
            f"🎬 <b>{data['title']}</b>\n"
            f"🔢 Kod: <code>{code}</code>\n"
            f"🌐 Til: {data['language']} | 🎭 Janr: {data['genre']}\n"
            f"📄 {data['description']}\n"
            f"👨‍💻 Admin: @{ADMIN_USERNAME}"
        )
        MOVIES[code] = {
            "type": data["file_type"],
            "file_id": data["file_id"],
            "title": data["title"],
            "genre": data["genre"],
            "caption": caption,
            "views": 0,
        }
        await callback.message.edit_text(
            f"🎉 <b>{data['title']}</b> qo'shildi! Kodi: <code>{code}</code>",
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text("🔄 Qo'shish bekor qilindi.")
    await state.clear()
    await callback.answer()


# === KOD ORQALI KINO YUBORISH ===
@dp.message(F.text)
async def search_movie_by_code(message: types.Message):
    text = (message.text or "").strip()
    if text in ADMIN_BUTTON_TEXTS or text.startswith("/"):
        return

    user_id = message.from_user.id
    USERS.add(user_id)

    if not await check_sub_channel(user_id):
        await message.answer("❌ Avval kanalga obuna bo'ling!", reply_markup=get_sub_keyboard())
        return

    if text in MOVIES:
        movie = MOVIES[text]
        movie["views"] += 1
        try:
            if movie["type"] == "video":
                await message.answer_video(
                    video=movie["file_id"], caption=movie["caption"], parse_mode="HTML"
                )
            else:
                await message.answer_document(
                    document=movie["file_id"], caption=movie["caption"], parse_mode="HTML"
                )
        except Exception as e:
            add_log(f"Kino yuborish xatosi (kod {text}): {e}")
            await message.answer(f"❌ Kinoni yuborishda xatolik yuz berdi. Admin: @{ADMIN_USERNAME}")
    elif text.isdigit():
        await message.answer(f"❌ Bunday kodli kino topilmadi. Admin: @{ADMIN_USERNAME}")


# === FLASK WEB PANEL ===
app = Flask(__name__)

WEB_TEMPLATE = """
<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <title>HUFilmBot - Web Panel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: #1e293b; padding: 20px; border-radius: 12px; }
        h1, h2 { color: #38bdf8; text-align: center; }
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #334155; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-card h3 { margin: 5px 0 0; font-size: 24px; color: #38bdf8; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; border-bottom: 1px solid #475569; text-align: left; }
        th { background: #0284c7; }
        .btn { background: #e11d48; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
        .logs { background: #000; color: #4ade80; padding: 12px; border-radius: 6px; font-family: monospace; max-height: 180px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 HUFilmBot Web Panel</h1>
        <div class="stats-grid">
            <div class="stat-card"><p>Obunachilar</p><h3>{{ users_count }}</h3></div>
            <div class="stat-card"><p>Kinolar</p><h3>{{ movies_count }}</h3></div>
            <div class="stat-card"><p>Ko'rishlar</p><h3>{{ total_views }}</h3></div>
        </div>
        <h2>🎬 Kinolar</h2>
        <table>
            <tr><th>Kod</th><th>Nomi</th><th>Ko'rishlar</th><th>Amal</th></tr>
            {% for code, movie in movies.items() %}
            <tr>
                <td><b>{{ code }}</b></td>
                <td>{{ movie.title }}</td>
                <td>{{ movie.views }}</td>
                <td>
                    <form action="/delete_movie/{{ code }}" method="POST" style="margin:0;">
                        <button class="btn" type="submit">O'chirish</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
        <h2>⚠️ Xatoliklar jurnali</h2>
        <div class="logs">
            {% if logs %}
                {% for log in logs %}<div>{{ log }}</div>{% endfor %}
            {% else %}
                <div>Xatoliklar yo'q ✅</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""


@app.route("/")
def web_dashboard():
    total_views = sum(m.get("views", 0) for m in MOVIES.values())
    return render_template_string(
        WEB_TEMPLATE,
        users_count=len(USERS),
        movies_count=len(MOVIES),
        total_views=total_views,
        movies=MOVIES,
        logs=ERROR_LOGS,
    )


@app.route("/delete_movie/<code>", methods=["POST"])
def delete_movie(code):
    if code in MOVIES:
        del MOVIES[code]
        add_log(f"Kino o'chirildi: {code}")
    return redirect(url_for("web_dashboard"))


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
        
