
import asyncio
import logging
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask

# === SOZLAMALAR ===
BOT_TOKEN = "9217478644:AAHN4xdotZXbpVq2ZrqWF4f3Ut0Yxxo0Y1Y"
settings = {
    "channel": "@HUFilmlar",      # Majburiy obuna kanalingiz
    "db_channel": "@kwliskbw"     # Kino bazasi joylashgan kanal
}

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === ASOSIY MENYU TUGMALARI ===
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📢 Kanallar"), KeyboardButton(text="📁 So'rovlar")],
        [KeyboardButton(text="💳 To'lov tizimlari"), KeyboardButton(text="💎 Premium")],
        [KeyboardButton(text="📝 Matnlar"), KeyboardButton(text="🔗 Referal")],
        [KeyboardButton(text="👨‍💻 Adminlar")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Assalomu alaykum! HUFilmBot ga xush kelibsiz. Kerakli bo'limni tanlang:",
        reply_markup=main_menu_kb
    )

@dp.message(F.text.in_({
    "📢 Kanallar", "📁 So'rovlar", "💳 To'lov tizimlari", "💎 Premium",
    "📝 Matnlar", "🔗 Referal", "👨‍💻 Adminlar"
}))
async def menu_handler(message: types.Message):
    await message.answer(f"Siz '{message.text}' bo'limini tanladingiz.")

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

# === ASOSIY FUNKSIYA ===
async def main():
    start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
