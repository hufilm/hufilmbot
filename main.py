
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

# === SOZLAMALAR ===
BOT_TOKEN = "9217478644:AAG4feyRXGijMM4mAMPI-NosT-dbwaCbtl0"
CHANNEL_ID = "@HUFilmlar"  # Majburiy obuna kanali

# Kino bazasi (Vaqtinchalik xotira)
MOVIES = {
    "5": "🎬 **5-kino nomi:** Forsaj 9\n📄 **Janr:** Jangari\n🔗 Kinoni ko'rish uchun bazadagi manzilga o'ting.",
    "6": "🎬 **6-kino nomi:** Qasoskorlar\n📄 **Janr:** Fantastika."
}

# Admin kino qo'shish holatlari (FSM)
class AddMovieState(StatesGroup):
    waiting_for_code_choice = State()
    waiting_for_custom_code = State()
    waiting_for_genre = State()
    waiting_for_cover_choice = State()
    waiting_for_custom_cover = State()
    waiting_for_confirmation = State()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === ASOSIY MENYU TUGMALARI ===
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💳 To'lov tizimlari"), KeyboardButton(text="💎 Premium")],
        [KeyboardButton(text="🔗 Referal"), KeyboardButton(text="👨‍💻 Adminlar")]
    ],
    resize_keyboard=True
)

# Admin uchun maxsus tugmalar
admin_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="🔙 Asosiy menyuga qaytish")]
    ],
    resize_keyboard=True
)

# Obunani tekshiruvchi funksiya
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
    
    if not await check_sub_channel(user_id):
        await message.answer(
            "❌ **Avval kanalimizga obuna bo'ling!**\n\nBotdan foydalanish uchun quyidagi kanalga obuna bo'lishingiz kerak:",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    welcome_text = (
        "<b>Salom! 👋</b>\n\n"
        "Men <b>HUFilmBot</b>man — siz sevikli kinolar va seriallarni osongina topib, tomosha qilishingiz uchun yaratilgan yordamchingirman.\n\n"
        "🤖 <b>Men nima qila olaman?</b>\n"
        "• 🔍 <b>Kino qidirish:</b> Menga kinoning maxsus raqamli kodini yuboring (masalan: <code>5</code>, <code>6</code>), men darhol siz istagan kinoni topib beraman.\n\n"
        "Kerakli bo'limni tanlash uchun pastdagi tugmalardan birini bosing yoki kino kodini yuboring! 👇"
    )
    await message.answer(welcome_text, reply_markup=main_menu_kb, parse_mode="HTML")

@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await check_sub_channel(user_id):
        await callback.message.delete()
        await callback.message.answer(
            "✅ **Obuna tasdiqlandi!** Endi botdan bemalol foydalanishingiz mumkin.",
            reply_markup=main_menu_kb,
            parse_mode="Markdown"
        )
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

@dp.message(Command("admin"))
@dp.message(F.text == "👨‍💻 Adminlar")
async def cmd_admin(message: types.Message):
    await message.answer("👨‍💻 **Admin panelga xush kelibsiz!** Kerakli amalni tanlang:", reply_markup=admin_menu_kb, parse_mode="Markdown")

@dp.message(F.text == "🔙 Asosiy menyuga qaytish")
async def back_to_main(message: types.Message):
    await message.answer("Asosiy menyuga qaytdingiz:", reply_markup=main_menu_kb)

@dp.message(F.text.in_({"💳 To'lov tizimlari", "💎 Premium", "🔗 Referal", "📊 Statistika"}))
async def menu_handler(message: types.Message):
    user_id = message.from_user.id
    if not await check_sub_channel(user_id):
        await message.answer("❌ **Avval kanalimizga obuna bo'ling!**", reply_markup=get_sub_keyboard(), parse_mode="Markdown")
        return
    await message.answer(f"Siz '{message.text}' bo'limini tanladingiz.")

# === ADMIN KINO QO'SHISH KONSTRUKTORI (FSM) ===
@dp.message(F.text == "➕ Kino qo'shish")
async def start_add_movie(message: types.Message, state: FSMContext):
    await message.answer("🎬 Iltimos, kanalga tashlangan kinoni (video yoki faylni) botga yuboring:")
    await state.set_state(AddMovieState.waiting_for_code_choice)

@dp.message(AddMovieState.waiting_for_code_choice)
async def process_movie_file(message: types.Message, state: FSMContext):
    auto_code = str(len(MOVIES) + 1)
    await state.update_data(movie_file=message.text, auto_code=auto_code)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ha", callback_data="code_yes"), InlineKeyboardButton(text="Yo'q", callback_data="code_no")]
    ])
    await message.answer(f"✅ Kino joylandi. Kod masalan: <b>{auto_code}</b>. O'zingiz kod qo'yasizmi yoki shu kod bo'laveradimi?", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.in_({"code_yes", "code_no"}))
async def process_code_choice(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if callback.data == "code_yes":
        await state.update_data(final_code=data['auto_code'])
        await callback.message.answer("✍️ Endi kino **janrini** kiriting (masalan: Jangari, Komediya):")
        await state.set_state(AddMovieState.waiting_for_genre)
    else:
        await callback.message.answer("✍️ O'zingiz qo'ymoqchi bo'lgan raqamli kodni kiriting (masalan: 88):")
        await state.set_state(AddMovieState.waiting_for_custom_code)
    await callback.answer()

@dp.message(AddMovieState.waiting_for_custom_code)
async def process_custom_code(message: types.Message, state: FSMContext):
    await state.update_data(final_code=message.text)
    await message.answer("✍️ Endi kino **janrini** kiriting (masalan: Jangari, Komediya):")
    await state.set_state(AddMovieState.waiting_for_genre)

@dp.message(AddMovieState.waiting_for_genre)
async def process_genre(message: types.Message, state: FSMContext):
    await state.update_data(genre=message.text)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ha", callback_data="cover_yes"), InlineKeyboardButton(text="Yo'q", callback_data="cover_no")]
    ])
    await message.answer("🖼️ O'zining coveri (rasmi) bo'ladimi yoki o'zingiz qo'yasizmi?", reply_markup=kb)
    await state.set_state(AddMovieState.waiting_for_cover_choice)

@dp.callback_query(F.data.in_({"cover_yes", "cover_no"}))
async def process_cover_choice(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cover_yes":
        await state.update_data(cover="default")
        await show_preview(callback.message, state)
    else:
        await callback.message.answer("📸 Iltimos, yangi cover rasmini yuboring:")
        await state.set_state(AddMovieState.waiting_for_custom_cover)
    await callback.answer()

@dp.message(AddMovieState.waiting_for_custom_cover)
async def process_custom_cover(message: types.Message, state: FSMContext):
    await state.update_data(cover=message.photo[-1].file_id if message.photo else "custom")
    await show_preview(message, state)

async def show_preview(message: types.Message, state: FSMContext):
    data = await state.get_data()
    preview_text = (
        f"📋 **Kino ma'lumotlari to'liq:**\n"
        f"🔢 Kod: <code>{data['final_code']}</code>\n"
        f"📄 Janr: {data['genre']}\n\n"
        f"🎬 Kino qo'yilsinmi?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha", callback_data="publish_yes"), InlineKeyboardButton(text="✏️ Edit", callback_data="publish_edit")]
    ])
    await message.answer(preview_text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(AddMovieState.waiting_for_confirmation)

@dp.callback_query(F.data.in_({"publish_yes", "publish_edit"}))
async def process_final_publish(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "publish_yes":
        data = await state.get_data()
        MOVIES[data['final_code']] = f"🎬 **Kino kodi:** {data['final_code']}\n📄 **Janr:** {data['genre']}\n🔗 Kinoni ko'rish uchun bazaga o'ting."
        await callback.message.answer("🎉 **Kino muvaffaqiyatli bazaga qo'shildi!** Endi foydalanuvchilar shu kodni yozib kinoni olishlari mumkin.", reply_markup=admin_menu_kb)
    else:
        await callback.message.answer("🔄 Tahrirlash bekor qilindi. Boshidan boshlash uchun '➕ Kino qo'shish' tugmasini bosing.", reply_markup=admin_menu_kb)
    await state.clear()
    await callback.answer()

# Kino kodlari bo'yicha qidirish (Foydalanuvchilar uchun)
@dp.message(F.text.regexp(r'^\d+$'))
async def search_movie(message: types.Message):
    user_id = message.from_user.id
    if not await check_sub_channel(user_id):
        await message.answer("❌ **Avval kanalimizga obuna bo'ling!**", reply_markup=get_sub_keyboard(), parse_mode="Markdown")
        return

    code = message.text
    if code in MOVIES:
        await message.answer(MOVIES[code], parse_mode="Markdown")
    else:
        await message.answer("❌ Kechirasiz, bunday kodli kino topilmadi.")

# === FLASH VEBSERVER (Render 24/7 ushlab turish uchun) ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti va 24/7 faol!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

def start_web_server():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

async def main():
    start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
