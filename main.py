import asyncio
import logging
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, render_template_string, request

# === SOZLAMALAR ===
BOT_TOKEN = "9217478644:AAHN4xdotZXbpVq2ZrqwF4f3UtOYxxoOYlY"

settings = {
    "channel": "@HUFilmlar",      # Majburiy obuna kanali
    "db_channel": "@kwliskbw"     # Kino bazasi joylashgan kanal/guruh
}

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ASOSIY MENYU TUGMALARI ---
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📢 Kanallar"), KeyboardButton(text="📋 So'rovlar")],
        [KeyboardButton(text="💳 To'lov tizimlari"), KeyboardButton(text="💎 Premium")],
        [KeyboardButton(text="📄 Matnlar"), KeyboardButton(text="🔗 Referal")],
        [KeyboardButton(text="👮‍♂️ Adminlar"), KeyboardButton(text="↗️ Ulanish")],
        [KeyboardButton(text="🌐 Web Panel"), KeyboardButton(text="📖 Qo'llanma")],
        [KeyboardButton(text="🚪 Chiqish"), KeyboardButton(text="🎨 Dizayn")]
    ],
    resize_keyboard=True
)

# --- FLASK VEB-PANEL QISMI ---
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>HUFilmBot Panel</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f9; margin: 0; padding: 20px; }
        .container { max-width: 400px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h2 { color: #333; text-align: center; }
        label { font-weight: bold; display: block; margin-top: 15px; }
        input[type="text"] { width: 100%; padding: 10px; margin-top: 5px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #ffc107; border: none; padding: 12px; width: 100%; margin-top: 20px; font-weight: bold; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #e0a800; }
        .status { text-align: center; color: green; margin-bottom: 15px; font-weight: bold; }
        .saved { text-align: center; color: blue; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🎬 HUFilmBot Boshqaruvi</h2>
        <div class="status">🟢 Panel ishlamoqda</div>
        <form method="POST">
            <label>📢 Majburiy Obuna Kanali:</label>
            <input type="text" name="channel" value="{{ settings.channel }}">
            
            <label>🗄 Kinolar Bazasi:</label>
            <input type="text" name="db_channel" value="{{ settings.db_channel }}">
            
            <button type="submit">Saqlash</button>
        </form>
        {% if saved %}
        <div class="saved">Muvaffaqiyatli saqlandi! ✅</div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global settings
    saved = False
    if request.method == "POST":
        settings["channel"] = request.form.get("channel").strip()
        settings["db_channel"] = request.form.get("db_channel").strip()
        saved = True
    return render_template_string(HTML_TEMPLATE, settings=settings, saved=saved)

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


# --- AIOGRAM BOT QISMI ---
async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=settings["channel"], user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        pass
    return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{settings['channel'][1:]}")],
            [InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")]
        ])
        await message.answer(
            "❌ Botdan foydalanish uchun quyidagi kanalimizga obuna bo'ling va "
            "so'ng 'Tekshirish' tugmasini bosing:",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            "💎 **HUFilmBot**\n"
            "Kino boshqaruv paneli.\n\n"
            "🎬 Hammasini shu yerdan boshqarasiz. Menga kino kodini yuboring yoki quyidagi menyudan foydalaning:",
            reply_markup=main_menu_kb
        )

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    try:
        await callback.answer()
    except Exception:
        pass

    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        try:
            await callback.message.delete()
        except Exception:
            pass
            
        await callback.message.answer(
            "Rahmat! Obuna tasdiqlandi ✅\nAsosiy menyu ochildi:",
            reply_markup=main_menu_kb
        )
    else:
        try:
            await callback.message.answer("❌ Siz hali kanalga obuna bo'lmadingiz! Iltimos, avval obuna bo'ling.")
        except Exception:
            pass

# Menyudagi tugmalar bosilganda javob berish
@dp.message(F.text.in_([
    "📢 Kanallar", "📋 So'rovlar", "💳 To'lov tizimlari", "💎 Premium", 
    "📄 Matnlar", "🔗 Referal", "👮
            
