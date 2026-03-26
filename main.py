import sqlite3
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

# ----- Конфигурация -----
RATE = 10000  # 10000 очков = 1 OSC
CONVERT_ENABLED = False  # временно отключено
CONVERT_MESSAGE = "Скоро"

# ----- База данных -----
def get_db():
    conn = sqlite3.connect('olympus_tap.db')
    conn.row_factory = sqlite3.Row
    return conn

def update_energy(cursor, user_id):
    cursor.execute("SELECT energy, max_energy, energy_regen_rate, last_energy_update FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return
    energy, max_energy, regen_rate, last_update = row
    now = time.time()
    if last_update == 0:
        cursor.execute("UPDATE users SET last_energy_update=? WHERE id=?", (now, user_id))
        return
    elapsed = now - last_update
    regen = int(elapsed / 60 * regen_rate)
    if regen > 0:
        new_energy = min(max_energy, energy + regen)
        cursor.execute("UPDATE users SET energy=?, last_energy_update=? WHERE id=?", (new_energy, now, user_id))

def get_user_data(user_id):
    conn = get_db()
    cursor = conn.cursor()
    update_energy(cursor, user_id)
    cursor.execute("SELECT id, username, points, energy, max_energy, tap_power, energy_regen_rate, osc_balance FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (id, username, last_energy_update) VALUES (?, ?, ?)", (user_id, "anon", time.time()))
        conn.commit()
        cursor.execute("SELECT id, username, points, energy, max_energy, tap_power, energy_regen_rate, osc_balance FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
    data = dict(row)
    conn.close()
    return data

def update_user_data(user_id, updates):
    conn = get_db()
    cursor = conn.cursor()
    update_energy(cursor, user_id)
    set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
    values = list(updates.values()) + [user_id]
    cursor.execute(f"UPDATE users SET {set_clause} WHERE id=?", values)
    conn.commit()
    conn.close()

def add_points_and_use_energy(user_id, points, energy_used):
    conn = get_db()
    cursor = conn.cursor()
    update_energy(cursor, user_id)
    cursor.execute("SELECT points, energy, tap_power, max_energy FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    new_points = row[0] + points
    new_energy = row[1] - energy_used
    if new_energy < 0:
        conn.close()
        return False
    cursor.execute("UPDATE users SET points=?, energy=?, last_tap_time=? WHERE id=?", (new_points, new_energy, time.time(), user_id))
    conn.commit()
    conn.close()
    return True

# ----- Эндпоинты -----
@app.get("/api/user")
async def get_user(user_id: int):
    return get_user_data(user_id)

@app.post("/api/tap")
async def tap(user_id: int):
    user = get_user_data(user_id)
    if user['energy'] < 1:
        return {"success": False, "error": "Недостаточно энергии"}
    success = add_points_and_use_energy(user_id, user['tap_power'], 1)
    if success:
        updated = get_user_data(user_id)
        return {"success": True, "user": updated}
    return {"success": False, "error": "Ошибка"}

@app.post("/api/buy")
async def buy(user_id: int, upgrade_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT cost, effect_type, effect_value FROM upgrades WHERE id=?", (upgrade_id,))
    up = cursor.fetchone()
    if not up:
        conn.close()
        return {"success": False, "error": "Улучшение не найдено"}
    cost, effect_type, effect_value = up
    user = get_user_data(user_id)
    if user['points'] < cost:
        conn.close()
        return {"success": False, "error": "Недостаточно очков"}
    cursor.execute("UPDATE users SET points = points - ? WHERE id=?", (cost, user_id))
    if effect_type == 'tap_power':
        cursor.execute("UPDATE users SET tap_power = tap_power + ? WHERE id=?", (effect_value, user_id))
    elif effect_type == 'max_energy':
        cursor.execute("UPDATE users SET max_energy = max_energy + ? WHERE id=?", (effect_value, user_id))
    elif effect_type == 'regen_rate':
        cursor.execute("UPDATE users SET energy_regen_rate = energy_regen_rate + ? WHERE id=?", (effect_value, user_id))
    cursor.execute("INSERT INTO user_upgrades (user_id, upgrade_id, level) VALUES (?,?,1) ON CONFLICT(user_id, upgrade_id) DO UPDATE SET level = level + 1", (user_id, upgrade_id))
    conn.commit()
    conn.close()
    updated_user = get_user_data(user_id)
    return {"success": True, "user": updated_user}

@app.get("/api/upgrades")
async def get_upgrades(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, cost FROM upgrades")
    upgrades = cursor.fetchall()
    conn.close()
    return [dict(u) for u in upgrades]

@app.get("/api/leaderboard")
async def leaderboard(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return [{"username": r[0], "points": r[1]} for r in rows]

@app.post("/api/convert")
async def convert(user_id: int, amount: int):
    # Временно отключено
    return {"success": False, "error": CONVERT_MESSAGE}

# ----- Статика -----
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index(request: Request):
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)