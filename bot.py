import asyncio
import sqlite3
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# ----- База данных (та же, что и в API) -----
def get_db():
    conn = sqlite3.connect('olympus_tap.db')
    return conn

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (id, username, last_energy_update) VALUES (?,?,?)", (user_id, username, time.time()))
        conn.commit()
    conn.close()

    webapp_url = f"https://olympus-tap.onrender.com/?user_id={user_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Открыть игру", web_app=types.WebAppInfo(url=webapp_url))]
    ])
    await message.answer(
        "🏛️ *Olympus Tap*\n\nТапай по Олимпусу, копи очки, улучшай героя!",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
