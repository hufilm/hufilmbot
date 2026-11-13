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
from flask import Flask
from datetime import datetime, date

# === SOZLAMALAR ===
BOT_TOKEN = "9217478644:AAG4feyRXGijMM4mAMPI-NosT-dbwaCbtl0"
CHANNEL_ID = "@HUFilmlar"  # Majburiy obuna kanali
ADMIN_USERNAME = "@HuFilmAdmin"
PAYMENT_CARD = "8600 0000 0000 0000"  # <-- Shu yerga o'z karta raqamingizni yozing

# Xotira bazalari (Ma'lumotlar saqlanishi uchun)
MOVIES = {
    "5": {
        "type": "text",
        "caption": "🎬 Kino: Forsaj 9\n📄 Janr: Jangari",
        "views": 0
    }
}
USERS = set()  # Botdan foydalanuvchilar ID lari
STATS = {
    "joined_today": 0,
    "left_today": 0,
    "last_reset": str(date.today())
}
REFERRALS = {}  # user_id -> invited_count

# FSM holatlari (Kino qo'shish va Reklama yuborish uchun)
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
        [KeyboardButton(text="🔗 Referal"), KeyboardButton(text="👨‍💻 Adminlar")]
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
    except TelegramBadRequest:
        pass
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
    
    # Statistika va foydalanuvchini ro'yxatga olish
    if user_id not in USERS:
        USERS.add(user_id)
        STATS["joined_today"] += 1

    # Referal tizimini tekshirish (/start ref_12345)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].split("_")[1])
            if referrer_id != user_id and referrer_id not in REFERRALS:
                REFERRALS[referrer_id] = REFERRALS.get(referrer_id, 0) + 1
        except ValueError:
            pass

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

@dp.message(Command("admin"))
@dp.message(F.text == "👨‍💻 Adminlar")
async def cmd_admin(message: types.Message):
    total_views = sum(m.get("views", 0) for m in MOVIES.values())
    admin_panel_text = (
        "🎬 **HUFilmBot 💎**\n"
        "<i>Kino boshqaruv paneli</i>\n\n"
        f"🎬 <b>{len(MOVIES)}</b> kino  •  👥 <b>{len(USERS)}</b> obunachi  •  👁 <b>{total_views}</b> ko'rish\n\n"
        "Hammasini shu yerdan boshqarasiz."
    )
    await message.answer(admin_panel_text, reply_markup=admin_menu_kb, parse_mode="HTML")

@dp.message(F.text == "⬅️ Chiqish")
async def back_to_main(message: types.Message):
    await message.answer("🏠 Bosh menyu", reply_markup=main_menu_kb)

# === ADMIN BO'LIMLARI (STATISTIKA, REKLAMA VA BOSHQALAR) ===
@dp.message(F.text == "📊 Statistika")
async def admin_stat(message: types.Message):
    total_views = sum(m.get("views", 0) for m in MOVIES.values())
    stat_text = (
        "📊 **To'liq Bot Statistikasi:**\n\n"
        f"🟢 Bugun qo'shilganlar: +{STATS['joined_today']} ta\n"
        f"🔴 Bugun chiqib ketganlar (taxminiy): {STATS['left_today']} ta\n"
        f"👥 Jami obunachilar: {len(USERS)} ta\n"
        f"🎬 Jami kinolar: {len(MOVIES)} ta\n"
        f"👁 Jami kino ko'rishlar: {total_views} marta\n"
        f"👨‍💻 Admin: {ADMIN_USERNAME}"
    )
    await message.answer(stat_text, reply_markup=admin_menu_kb, parse_mode="Markdown")

@dp.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: types.Message):
    await message.answer(f"👥 **Foydalanuvchilar ma'lumotlari:**\n\nJami bazadagi faol foydalanuvchilar: {len(USERS)} ta.", reply_markup=admin_menu_kb, parse_mode="Markdown")

@dp.message(F.text == "🎬 Kinolar")
async def admin_movies_list(message: types.Message):
    if not MOVIES:
        movies_list = "Hozircha kinolar yo'q."
    else:
        movies_list = "\n".join([f"🔹 Kod: <code>{code}</code> | Ko'rishlar: {m.get('views', 0)} marta" for code, m in MOVIES.items()])
    await message.answer(f"🎬 **Bazadagi kinolar va ularning reytingi:**\n\n{movies_list}", reply_markup=admin_menu_kb, parse_mode="HTML")

@dp.message(F.text == "📌 Postlar")
async def admin_posts(message: types.Message):
    await message.answer("📌 Postlar bo'limi: Kanalga yuboriladigan avtomatlashgan postlar sozlamasi.", reply_markup=admin_menu_kb)

# --- REKLAMA TIZIMI (Rasm, video yoki matn tarqatish) ---
@dp.message(F.text == "🎯 Reklama")
async def admin_ads_start(message: types.Message, state: FSMContext):
    await message.answer("📢 Barcha obunachilarga yubormoqchi bo'lgan **xabaringizni, rasmingizni yoki videongizni** yuboring:")
    await state.set_state(BroadcastState.waiting_for_ad_content)

@dp.message(BroadcastState.waiting_for_ad_content)
async def process_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    sent_count = 0
    blocked_count = 0
    
    status_msg = await message.answer("⏳ Reklama tarqatilmoqda...")

    for user_id in USERS:
        try:
            await message.send_copy(chat_id=user_id)
            sent_count += 1
            await asyncio.sleep(0.05)  # Telegram limitiga tushmaslik uchun
        except Exception:
            blocked_count + 1

    await status_msg.edit_text(
        f"✅ **Reklama tarqatib bo'lindi!**\n\n"
        f"📤 Yuborildi: {sent_count} ta\n"
        f"❌ Bloklaganlar: {blocked_count} ta",
        reply_markup=admin_menu_kb
    )

# === FOYDALANUVCHI BO'LIMLARI (TO'LOV VA REFERAL) ===
@dp.message(F.text == "💳 To'lov tizimlari")
async def payment_handler(message: types.Message):
    pay_text = (
        "💳 **To'lov Tizimlari va Rekvizitlar:**\n\n"
        "Premium obuna yoki pullik xizmatlar uchun to'lovni quyidagi karta raqamiga o'tkazing:\n\n"
        f"💳 <code>{PAYMENT_CARD}</code>\n\n"
        f"To'lov qilgandan so'ng chekni adminga yuboring: {ADMIN_USERNAME}"
    )
    await message.answer(pay_text, reply_markup=main_menu_kb, parse_mode="HTML")

@dp.message(F.text == "💎 Premium")
async def premium_handler(message: types.Message):
    await message.answer(f"💎 **Premium Obuna**\n\nPremium imkoniyatlardan foydalanish va cheklovlaringizni olib tashlash uchun {ADMIN_USERNAME} bilan bog'laning.")

@dp.message(F.text == "🔗 Referal")
async def referral_handler(message: types.Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    invited_count = REFERRALS.get(user_id, 0)
    
    ref_text = (
        "🔗 **Referal Tizimi (Do'stlarni taklif qilish)**\n\n"
        "Do'stlaringizni botga taklif qiling va ballar/obunalar yig'ing!\n\n"
        f"📎 **Sizning havolangiz:**\n{ref_link}\n\n"
        f"👥 Taklif qilgan do'stlaringiz: <b>{invited_count} ta</b>"
    )
    await message.answer(ref_text, reply_markup=main_menu_kb, parse_mode="HTML")

# === ADMIN KINO QO'SHISH KONSTRUKTORI (FSM) ===
@dp.message(F.text == "➕ Kino qo'shish")
async def start_add_movie(message: types.Message, state: FSMContext):
    await message.answer("🎬 Kinoni (video yoki fayl ko'rinishida) yuboring:")
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
    await message.answer(f"✅ Kino qabul qilindi. Kod: <b>{auto_code}</b>. Shu kod qolsinmi?", reply_markup=kb, parse_mode="HTML")
    await state.set_state(AddMovieState.waiting_for_code_choice)

@dp.callback_query(AddMovieState.waiting_for_code_choice, F.data.in_({"code_yes", "code_no"}))
async def process_code_choice(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if callback.data == "code_yes":
        await state.update_data(final_code=data['auto_code'])
        await callback.message.answer("✍️ Kino janrini kiriting (masalan: Jangari):")
        await state.set_state(AddMovieState.waiting_for_genre)
    else:
        await callback.message.answer("✍️ O'zingizning raqamli kodingizni yuboring (masalan: 88):")
        await state.set_state(AddMovieState.waiting_for_custom_code)
    await callback.answer()

@dp.message(AddMovieState.waiting_for_custom_code)
async def process_custom_code(message: types.Message, state: FSMContext):
    await state.update_data(final_code=message.text)
    await message.answer("✍️ Kino janrini kiriting (masalan: Jangari):")
    await state.set_state(AddMovieState.waiting_for_genre)

@dp.message(AddMovieState.waiting_for_genre)
async def process_genre(message: types.Message, state: FSMContext):
    await state.update_data(genre=message.text)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ha", callback_data="cover_yes"), InlineKeyboardButton(text="Yo'q", callback_data="cover_no")]
    ])
    await message.answer("🖼️ O'zining rasmi (cover) bo'ladimi?", reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_cover_choice)

@dp.callback_query(AddMovieState.waiting_for_cover_choice, F.data.in_({"cover_yes", "cover_no"}))
async def process_cover_choice(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cover_yes":
        await state.update_data(cover="default")
        await show_preview(callback.message, state)
    else:
        await callback.message.answer("📸 Yangi rasm yuboring:")
        await state.set_state(AddMovieState.waiting_for_custom_cover)
    await callback.answer()

@dp.message(AddMovieState.waiting_for_custom_cover, F.photo)
async def process_custom_cover(message: types.Message, state: FSMContext):
    await state.update_data(cover=message.photo[-1].file_id)
    await show_preview(message, state)

async def show_preview(message: types.Message, state: FSMContext):
    data = await state.get_data()
    preview_text = f"🔢 Kod: {data['final_code']}\n📄 Janr: {data['genre']}\n\nKino qo'yilsinmi?"
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
            "caption": f"🎬 Kino kodi: {data['final_code']}\n📄 Janr: {data['genre']}\n👨‍💻 Admin: {ADMIN_USERNAME}",
            "views": 0
        }
        await callback.message.answer("🎉 Kino bazaga qo'shildi!", reply_markup=admin_menu_kb)
    else:
        await callback.message.answer("🔄 Bekor qilindi.", reply_markup=admin_menu_kb)
    await state.clear()
    await callback.answer()

# === KINO QIDIRISH VA STATISTIKANI YANGILASH ===
@dp.message(F.text.regexp(r'^\d+$'))
async def search_movie(message: types.Message):
    user_id = message.from_user.id
    if not await check_sub_channel(user_id):
        await message.answer("❌ Avval kanalga obuna bo'ling!", reply_markup=get_sub_keyboard(), parse_mode="Markdown")
        return

    code = message.text
    if code in MOVIES:
        movie = MOVIES[code]
        movie["views"] += 1  # Kino ko'rishlar sonini bittaga oshirish
        
        if "file_id" in movie:
            if movie["type"] == "video":
                await message.answer_video(video=movie["file_id"], caption=movie["caption"])
            else:
                await message.answer_document(document=movie["file_id"], caption=movie["caption"])
        else:
            await message.answer(movie["caption"])
    else:
        await message.answer(f"❌ Bunday kodli kino topilmadi.\n👨‍💻 Admin: {ADMIN_USERNAME}")

# === FLASK SERVER (24/7) ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                            
