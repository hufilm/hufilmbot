
import asyncio
import json
import logging
import os
import threading
import urllib.request
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
    MenuButtonCommands,
    WebAppInfo,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramForbiddenError
from flask import Flask, render_template_string, request, redirect, url_for

# === ASOSIY SOZLAMALAR ===
BOT_TOKEN = "9217478644:AAG4feyRXGijMM4mAMPI-NosT-dbwaCbtl0"
ADMIN_ID = 6865833003
WEB_APP_URL = "https://hufilmbot.onrender.com"
DATA_FILE = "bot_data.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# === MA'LUMOTLAR BAZASI (JSON) ===
DEFAULT_DATA = {
    "settings": {
        "welcome_text": "🎬 <b>HUFILM BOTIGA XUSH KELIBSIZ!</b>\n\n🍿 Sevimli kinolaringizni topish uchun kodni yuboring va tomosha qilishni boshlang! ❤️",
        "welcome_photo": "",
        "payment_card": "8600 0000 0000 0000",
        "admin_username": "HuFilmAdmin",
        "vip_price": "25 000 so'm / oy",
        "channels": ["@HUFilmlar"],
    },
    "movies": {},
    "users": {},
    "events": [],
    "logs": [],
}


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_DATA.items():
                    if k not in data:
                        data[k] = v
                for k, v in DEFAULT_DATA["settings"].items():
                    if k not in data["settings"]:
                        data["settings"][k] = v
                return data
        except Exception as e:
            logging.error(f"Baza o'qishda xato: {e}")
    return json.loads(json.dumps(DEFAULT_DATA))


DB = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DB, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Baza saqlashda xato: {e}")


def add_log(text: str):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    DB["logs"].append(f"[{stamp}] {text}")
    if len(DB["logs"]) > 60:
        DB["logs"] = DB["logs"][-60:]
    save_data()


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def register_user(user: types.User):
    uid = str(user.id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    is_new = uid not in DB["users"]
    if is_new:
        DB["users"][uid] = {
            "id": user.id,
            "name": user.full_name,
            "username": user.username or "",
            "joined_at": now,
            "joined_date": today_str(),
            "status": "active",
            "watched_count": 0,
            "watched_movies": [],
            "referrals": 0,
            "is_vip": False,
        }
        DB["events"].append({"type": "join", "user_id": user.id, "date": today_str()})
    else:
        DB["users"][uid]["name"] = user.full_name
        DB["users"][uid]["username"] = user.username or ""
        if DB["users"][uid].get("status") != "active":
            DB["users"][uid]["status"] = "active"
            DB["events"].append({"type": "join", "user_id": user.id, "date": today_str()})
    save_data()


def mark_user_left(user_id: int, reason: str = "left"):
    uid = str(user_id)
    if uid in DB["users"] and DB["users"][uid].get("status") == "active":
        DB["users"][uid]["status"] = reason
        DB["events"].append({"type": "leave", "user_id": user_id, "date": today_str()})
        save_data()


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


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === KLAVIATURALAR ===
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💳 To'lov tizimlari"), KeyboardButton(text="💎 Premium xarid qilish")],
        [KeyboardButton(text="🔗 Referal"), KeyboardButton(text="🆘 SOS")],
    ],
    resize_keyboard=True,
)


def get_admin_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌐 Web Panel", web_app=WebAppInfo(url=WEB_APP_URL))],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Foydalanuvchilar")],
            [KeyboardButton(text="🎬 Kinolar"), KeyboardButton(text="📌 Postlar")],
            [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="🎯 Reklama")],
            [KeyboardButton(text="💳 To'lov tizimlari"), KeyboardButton(text="💎 Premium xarid qilish")],
            [KeyboardButton(text="🔗 Referal"), KeyboardButton(text="⬅️ Chiqish")],
        ],
        resize_keyboard=True,
    )


ADMIN_BUTTON_TEXTS = {
    "🌐 Web Panel",
    "📊 Statistika",
    "👥 Foydalanuvchilar",
    "🎬 Kinolar",
    "📌 Postlar",
    "➕ Kino qo'shish",
    "🎯 Reklama",
    "💳 To'lov tizimlari",
    "💎 Premium xarid qilish",
    "🔗 Referal",
    "🆘 SOS",
    "⬅️ Chiqish",
}


async def setup_bot_commands():
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="🏠 Botni ishga tushirish"),
        ],
        scope=BotCommandScopeDefault(),
    )
    try:
        await bot.set_my_commands(
            commands=[
                BotCommand(command="admin", description="🛠 Admin va Web Panel"),
                BotCommand(command="start", description="🏠 Bosh menyu"),
            ],
            scope=BotCommandScopeChat(chat_id=ADMIN_ID),
        )
        await bot.set_chat_menu_button(
            chat_id=ADMIN_ID,
            menu_button=MenuButtonCommands(),
        )
    except Exception as e:
        add_log(f"Admin menyu sozlash xatosi: {e}")


async def check_sub_channels(user_id: int) -> list:
    if user_id == ADMIN_ID:
        return []
    not_subbed = []
    for ch in DB["settings"]["channels"]:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in {"member", "administrator", "creator"}:
                not_subbed.append(ch)
        except Exception as e:
            add_log(f"Kanal tekshirish xatosi ({ch}): {e}")
    return not_subbed


def get_sub_keyboard(channels: list):
    rows = []
    for ch in channels:
        clean = ch.replace("@", "")
        url = ch if ch.startswith("http") else f"https://t.me/{clean}"
        rows.append([InlineKeyboardButton(text=f"📢 Obuna bo'lish ({ch})", url=url)])
    rows.append([InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_welcome(message: types.Message):
    text = DB["settings"]["welcome_text"]
    photo = DB["settings"].get("welcome_photo", "").strip()
    kb = get_admin_menu_kb() if message.from_user.id == ADMIN_ID else main_menu_kb
    if photo:
        try:
            await message.answer_photo(photo=photo, caption=text, reply_markup=kb, parse_mode="HTML")
            return
        except Exception as e:
            add_log(f"Welcome rasm xatosi: {e}")
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# === HANDLERLAR ===
@dp.my_chat_member()
async def on_my_chat_member(update: types.ChatMemberUpdated):
    if update.chat.type == "private":
        new_status = update.new_chat_member.status
        uid = update.from_user.id
        if new_status in {"kicked", "left"}:
            mark_user_left(uid, "blocked" if new_status == "kicked" else "left")
        elif new_status == "member":
            register_user(update.from_user)


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user)
    user_id = message.from_user.id

    args = (message.text or "").split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = str(int(args[1].split("_", 1)[1]))
            if ref_id != str(user_id) and ref_id in DB["users"]:
                DB["users"][ref_id]["referrals"] = DB["users"][ref_id].get("referrals", 0) + 1
                save_data()
        except ValueError:
            pass

    missing = await check_sub_channels(user_id)
    if missing:
        await message.answer(
            "❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=get_sub_keyboard(missing),
        )
        return

    await send_welcome(message)


@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    register_user(callback.from_user)
    missing = await check_sub_channels(callback.from_user.id)
    if not missing:
        try:
            await callback.message.delete()
        except Exception:
            pass
        kb = get_admin_menu_kb() if callback.from_user.id == ADMIN_ID else main_menu_kb
        await callback.message.answer(DB["settings"]["welcome_text"], reply_markup=kb, parse_mode="HTML")
    else:
        await callback.answer("❌ Siz hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Bu buyruq faqat bot admini uchun.")
        return

    total_views = sum(m.get("views", 0) for m in DB["movies"].values())
    active_users = sum(1 for u in DB["users"].values() if u.get("status") == "active")
    panel_text = (
        "🎬 <b>HUFilmBot 💎</b>\n"
        "<i>Admin boshqaruv paneli</i>\n\n"
        f"🎬 <b>{len(DB['movies'])}</b> kino  •  👥 <b>{active_users}</b> faol obunachi  •  👁 <b>{total_views}</b> ko'rish"
    )
    inline_web = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Web Panelni ochish", web_app=WebAppInfo(url=WEB_APP_URL))]
        ]
    )
    await message.answer(panel_text, reply_markup=get_admin_menu_kb(), parse_mode="HTML")
    await message.answer("📲 Quyidagi tugma orqali Web Panelga kiring:", reply_markup=inline_web)


@dp.message(F.text == "⬅️ Chiqish")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Bosh menyu", reply_markup=main_menu_kb)


@dp.message(F.text == "🆘 SOS")
async def sos_handler(message: types.Message):
    register_user(message.from_user)
    missing = await check_sub_channels(message.from_user.id)
    if missing:
        await message.answer("❌ Avval kanallarga obuna bo'ling!", reply_markup=get_sub_keyboard(missing))
        return
    admin_user = DB["settings"]["admin_username"].replace("@", "")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="👨‍💻 Adminga yozish", url=f"https://t.me/{admin_user}")]]
    )
    await message.answer("🆘 Savol, taklif yoki muammolar bo'yicha adminga murojaat qiling:", reply_markup=kb)


@dp.message(F.text == "💳 To'lov tizimlari")
async def payment_handler(message: types.Message):
    register_user(message.from_user)
    card = DB["settings"]["payment_card"]
    admin_user = DB["settings"]["admin_username"].replace("@", "")
    await message.answer(
        f"💳 <b>To'lov tizimlari</b>\n\n"
        f"Karta raqami: <code>{card}</code>\n"
        f"To'lov chekini yuboring: @{admin_user}",
        parse_mode="HTML",
    )


@dp.message(F.text == "💎 Premium xarid qilish")
async def premium_handler(message: types.Message):
    register_user(message.from_user)
    price = DB["settings"]["vip_price"]
    card = DB["settings"]["payment_card"]
    admin_user = DB["settings"]["admin_username"].replace("@", "")
    await message.answer(
        f"💎 <b>Premium obuna xarid qilish</b>\n\n"
        f"💰 Narxi: <b>{price}</b>\n"
        f"💳 Karta: <code>{card}</code>\n\n"
        f"To'lov qilib chekni @{admin_user} ga yuboring.",
        parse_mode="HTML",
    )


@dp.message(F.text == "🔗 Referal")
async def referral_handler(message: types.Message):
    register_user(message.from_user)
    uid = str(message.from_user.id)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{uid}"
    count = DB["users"].get(uid, {}).get("referrals", 0)
    await message.answer(
        f"🔗 <b>Sizning referal havolangiz:</b>\n{ref_link}\n\n"
        f"👥 Taklif qilgan do'stlaringiz: <b>{count} ta</b>",
        parse_mode="HTML",
    )


# === ADMIN TELEGRAM BUYRUQLARI ===
@dp.message(F.text == "📊 Statistika")
async def admin_stat(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total_views = sum(m.get("views", 0) for m in DB["movies"].values())
    active = sum(1 for u in DB["users"].values() if u.get("status") == "active")
    left = len(DB["users"]) - active
    await message.answer(
        f"📊 <b>Bot Statistikasi:</b>\n\n"
        f"👥 Jami obunachilar: <b>{len(DB['users'])}</b>\n"
        f"✅ Faol: <b>{active}</b> | ❌ Tark etgan: <b>{left}</b>\n"
        f"🎬 Kinolar soni: <b>{len(DB['movies'])}</b>\n"
        f"👁 Jami ko'rishlar: <b>{total_views}</b>",
        parse_mode="HTML",
    )


@dp.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    active = sum(1 for u in DB["users"].values() if u.get("status") == "active")
    await message.answer(
        f"👥 Jami: <b>{len(DB['users'])}</b> | Faol: <b>{active}</b>\n"
        f"To'liq ro'yxatni 🌐 <b>Web Panel</b>ning 2-bo'limida ko'rishingiz mumkin.",
        parse_mode="HTML",
    )


@dp.message(F.text == "🎬 Kinolar")
async def admin_movies_list(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not DB["movies"]:
        await message.answer("🎬 Hozircha kinolar qo'shilmagan.")
        return
    lines = [
        f"🔹 Kod: <code>{code}</code> | {m['title']} | 👁 {m.get('views', 0)}"
        for code, m in DB["movies"].items()
    ]
    await message.answer("🎬 <b>Kinolar:</b>\n\n" + "\n".join(lines[:30]), parse_mode="HTML")


@dp.message(F.text == "📌 Postlar")
async def admin_posts(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    chs = ", ".join(DB["settings"]["channels"]) or "Yo'q"
    await message.answer(f"📌 Majburiy obuna kanallari: <b>{chs}</b>", parse_mode="HTML")


@dp.message(F.text == "🎯 Reklama")
async def admin_ads_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📢 Barcha obunachilarga yuboriladigan xabar, rasm yoki videoni yuboring:")
    await state.set_state(BroadcastState.waiting_for_ad_content)


@dp.message(BroadcastState.waiting_for_ad_content)
async def process_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    sent, blocked = 0, 0
    status = await message.answer("⏳ Reklama tarqatilmoqda...")
    for uid_str in list(DB["users"].keys()):
        uid = int(uid_str)
        try:
            await message.send_copy(chat_id=uid)
            sent += 1
            await asyncio.sleep(0.04)
        except TelegramForbiddenError:
            blocked += 1
            mark_user_left(uid, "blocked")
        except Exception as e:
            blocked += 1
            add_log(f"Reklama xatosi ({uid}): {e}")
    await status.edit_text(f"✅ Yuborildi: {sent} ta\n❌ Bloklagan: {blocked} ta")


# === TELEGRAMDAN KINO QO'SHISH ===
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
    code = str(101 + len(DB["movies"]))
    while code in DB["movies"]:
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
    admin_user = DB["settings"]["admin_username"].replace("@", "")
    caption = (
        f"🎬 <b>{data['title']}</b>\n"
        f"🔢 Kod: <code>{code}</code>\n"
        f"🌐 Til: {data['language']} | 🎭 Janr: {data['genre']}\n"
        f"📄 {data['description']}\n"
        f"👨‍💻 Admin: @{admin_user}"
    )
    DB["movies"][code] = {
        "code": code,
        "type": data["file_type"],
        "file_id": data["file_id"],
        "title": data["title"],
        "description": data["description"],
        "language": data["language"],
        "genre": data["genre"],
        "access": data["access"],
        "caption": caption,
        "views": 0,
        "added_date": today_str(),
    }
    save_data()
    await callback.message.edit_text(
        f"🎉 <b>{data['title']}</b> qo'shildi! Kodi: <code>{code}</code>",
        parse_mode="HTML",
    )
else:
    await callback.message.edit_text("🔄 Bekor qilindi.")
await state.clear()
await callback.answer()


# === KINO QIDIRISH ===
@dp.message(F.text)
async def search_movie_by_code(message: types.Message):
text = (message.text or "").strip()
if text in ADMIN_BUTTON_TEXTS or text.startswith("/"):
    return

register_user(message.from_user)
user_id = message.from_user.id

missing = await check_sub_channels(user_id)
if missing:
    await message.answer("❌ Avval kanallarga obuna bo'ling!", reply_markup=get_sub_keyboard(missing))
    return

if text in DB["movies"]:
    movie = DB["movies"][text]
    if movie.get("access") == "Faqat VIP" and user_id != ADMIN_ID:
        if not DB["users"].get(str(user_id), {}).get("is_vip", False):
            await message.answer("💎 Bu kino faqat VIP obunachilar uchun! <b>💎 Premium xarid qilish</b> tugmasini bosing.", parse_mode="HTML")
            return

    movie["views"] = movie.get("views", 0) + 1
    uid_str = str(user_id)
    if uid_str in DB["users"]:
        DB["users"][uid_str]["watched_count"] = DB["users"][uid_str].get("watched_count", 0) + 1
        watched_list = DB["users"][uid_str].setdefault("watched_movies", [])
        watched_list.append(f"{text} - {movie['title']}")
        if len(watched_list) > 50:
            DB["users"][uid_str]["watched_movies"] = watched_list[-50:]
    save_data()

    try:
        if movie.get("type") == "document" and movie.get("file_id"):
            await message.answer_document(document=movie["file_id"], caption=movie["caption"], parse_mode="HTML")
        elif movie.get("file_id"):
            await message.answer_video(video=movie["file_id"], caption=movie["caption"], parse_mode="HTML")
        else:
            await message.answer(movie["caption"], parse_mode="HTML")
    except Exception as e:
        add_log(f"Kino yuborish xatosi ({text}): {e}")
        await message.answer("❌ Kinoni yuborishda xatolik yuz berdi.")
elif text.isdigit():
    admin_user = DB["settings"]["admin_username"].replace("@", "")
    await message.answer(f"❌ Bunday kodli kino topilmadi. Admin: @{admin_user}")


# === FLASK 4-BO'LIMLI WEB PANEL ===
app = Flask(__name__)

WEB_TEMPLATE = """
<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HUFilmBot — Admin Web Panel</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b1120; color: #f1f5f9; margin: 0; padding: 12px; padding-bottom: 40px; }
    .header { text-align: center; padding: 12px; background: linear-gradient(135deg, #1e293b, #0f172a); border-radius: 14px; border: 1px solid #334155; margin-bottom: 14px; }
    .header h1 { margin: 0; font-size: 20px; color: #38bdf8; }
    .header p { margin: 4px 0 0; font-size: 12px; color: #94a3b8; }

    .tabs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 14px; }
    .tab-btn { background: #1e293b; color: #cbd5e1; border: 1px solid #334155; padding: 10px 4px; border-radius: 10px; font-size: 12px; font-weight: 600; cursor: pointer; text-align: center; }
    .tab-btn.active { background: #0284c7; color: #fff; border-color: #38bdf8; }

    .section { display: none; background: #1e293b; padding: 14px; border-radius: 14px; border: 1px solid #334155; }
    .section.active { display: block; }
    h2 { margin: 0 0 12px; font-size: 16px; color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 8px; }

    label { display: block; font-size: 12px; color: #94a3b8; margin: 10px 0 4px; }
    input, textarea, select { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 14px; }
    .btn { display: inline-block; background: #0284c7; color: #fff; border: none; padding: 10px 14px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 10px; width: 100%; }
    .btn-danger { background: #e11d48; width: auto; padding: 6px 10px; font-size: 12px; margin: 0; }
    .btn-green { background: #16a34a; }
    .btn-gray { background: #475569; }

    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
    .card { background: #0f172a; padding: 10px; border-radius: 10px; border: 1px solid #334155; text-align: center; }
    .card span { display: block; font-size: 11px; color: #94a3b8; }
    .card b { font-size: 18px; color: #38bdf8; }
    .card b.red { color: #f43f5e; }
    .card b.green { color: #4ade80; }

    .user-item, .movie-item { background: #0f172a; padding: 10px; border-radius: 10px; border: 1px solid
    
