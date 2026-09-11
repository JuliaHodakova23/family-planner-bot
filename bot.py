import asyncio
import sqlite3
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

TOKEN = os.environ.get("TELEGRAM_TOKEN", "8952306568:AAG-rKOmdm91XcbAmlhFIKAuoH4EIwfXbxg")

FAMILY_IDS = [5017615927, 909536228]
FAMILY_COMMON_ID = 999999999

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('family_planner.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            due_date TEXT,
            done INTEGER DEFAULT 0,
            reminded INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_task(user_id, text, due_date):
    if user_id in FAMILY_IDS:
        user_id = FAMILY_COMMON_ID
    conn = sqlite3.connect('family_planner.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO tasks (user_id, text, due_date) VALUES (?, ?, ?)',
                (user_id, text, due_date))
    conn.commit()
    conn.close()

def get_tasks(user_id):
    if user_id in FAMILY_IDS:
        user_id = FAMILY_COMMON_ID
    conn = sqlite3.connect('family_planner.db')
    cur = conn.cursor()
    cur.execute('SELECT id, text, due_date FROM tasks WHERE user_id=? AND done=0 ORDER BY due_date', (user_id,))
    tasks = cur.fetchall()
    conn.close()
    return tasks

def delete_task(task_id, user_id):
    if user_id in FAMILY_IDS:
        user_id = FAMILY_COMMON_ID
    conn = sqlite3.connect('family_planner.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM tasks WHERE id=? AND user_id=?', (task_id, user_id))
    conn.commit()
    conn.close()

def mark_done(task_id, user_id):
    if user_id in FAMILY_IDS:
        user_id = FAMILY_COMMON_ID
    conn = sqlite3.connect('family_planner.db')
    cur = conn.cursor()
    cur.execute('UPDATE tasks SET done=1 WHERE id=? AND user_id=?', (task_id, user_id))
    conn.commit()
    conn.close()

def update_task(task_id, user_id, new_text):
    if user_id in FAMILY_IDS:
        user_id = FAMILY_COMMON_ID
    conn = sqlite3.connect('family_planner.db')
    cur = conn.cursor()
    cur.execute('UPDATE tasks SET text=? WHERE id=? AND user_id=?', (new_text, task_id, user_id))
    conn.commit()
    conn.close()

init_db()

# ===== КЛАВИАТУРЫ =====
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить задачу")],
        [KeyboardButton(text="📋 Мои задачи")]
    ],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

user_data = {}

# ===== КАЛЕНДАРЬ =====
def generate_calendar(year, month):
    first_day = datetime(year, month, 1)
    start_weekday = first_day.weekday()
    days_in_month = (first_day.replace(month=month+1, day=1) - timedelta(days=1)).day
    keyboard = []
    month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    keyboard.append([
        InlineKeyboardButton(text="◀️", callback_data=f"cal_prev_{year}_{month}"),
        InlineKeyboardButton(text=f"{month_names[month-1]} {year}", callback_data="ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal_next_{year}_{month}")
    ])
    keyboard.append([InlineKeyboardButton(text=d, callback_data="ignore") for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]])
    row = []
    for _ in range(start_weekday):
        row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
    for day in range(1, days_in_month + 1):
        is_past = datetime(year, month, day) < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if is_past:
            row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
        else:
            row.append(InlineKeyboardButton(text=str(day), callback_data=f"day_{year}_{month}_{day}"))
        if len(row) == 7:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_date")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def generate_hours_kb(date_str):
    keyboard = []
    row = []
    now = datetime.now()
    if date_str == now.strftime('%Y-%m-%d'):
        current_hour = now.hour
        for h in range(current_hour, 24):
            row.append(InlineKeyboardButton(text=f"{h:02d}", callback_data=f"hour_{h:02d}"))
            if len(row) == 6:
                keyboard.append(row)
                row = []
    else:
        for h in range(24):
            row.append(InlineKeyboardButton(text=f"{h:02d}", callback_data=f"hour_{h:02d}"))
            if len(row) == 6:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_time")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def generate_minutes_kb(date_str, hour_str):
    keyboard = []
    row = []
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute

    if date_str == now.strftime('%Y-%m-%d') and int(hour_str) == current_hour:
        start_minute = (current_minute // 10) * 10 + 10
        for m in range(start_minute, 60, 10):
            row.append(InlineKeyboardButton(text=f"{m:02d}", callback_data=f"min_{m:02d}"))
            if len(row) == 6:
                keyboard.append(row)
                row = []
    else:
        for m in range(0, 60, 10):
            row.append(InlineKeyboardButton(text=f"{m:02d}", callback_data=f"min_{m:02d}"))
            if len(row) == 6:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_time")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ===== ГЛАВНОЕ МЕНЮ =====
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👨‍👩‍👦 Семейный планер!\n\nВыбери действие на кнопках ниже:",
        reply_markup=main_kb
    )

@dp.message(lambda m: m.text == "➕ Добавить задачу")
async def add_task_button(message: types.Message):
    user_data[message.from_user.id] = {"state": "awaiting_text"}
    await message.answer("Введите текст задачи:", reply_markup=cancel_kb)

@dp.message(lambda m: m.text == "📋 Мои задачи")
async def my_tasks_button(message: types.Message):
    tasks = get_tasks(message.from_user.id)
    if not tasks:
        await message.answer("У вас пока нет задач.", reply_markup=main_kb)
        return
    await message.answer("📋 Ваши задачи:", reply_markup=main_kb)
    for task_id, text, due in tasks:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{task_id}"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit_{task_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{task_id}")
            ]
        ])
        await message.answer(f"📝 {text}\n🕒 {due}", reply_markup=keyboard)

# ===== ОБРАБОТКА ТЕКСТА =====
@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Выбери действие на кнопках ниже:", reply_markup=main_kb)
        return
    data = user_data[user_id]
    state = data.get("state")

    if state == "awaiting_text":
        if message.text == "❌ Отмена":
            del user_data[user_id]
            await message.answer("Отменено.", reply_markup=main_kb)
            return
        data["text"] = message.text
        data["state"] = "awaiting_date"
        now = datetime.now()
        await message.answer("Выберите дату:", reply_markup=generate_calendar(now.year, now.month))

    elif state == "editing_text":
        task_id = data["task_id"]
        if message.text == "❌ Отмена":
            del user_data[user_id]
            await message.answer("Отменено.", reply_markup=main_kb)
            return
        update_task(task_id, user_id, message.text)
        await message.answer("✅ Текст задачи обновлён.", reply_markup=main_kb)
        del user_data[user_id]

# ===== ОБРАБОТЧИКИ КНОПОК =====
@dp.callback_query(lambda c: c.data.startswith("done_"))
async def done_task(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    mark_done(task_id, callback.from_user.id)
    await callback.message.edit_text("✅ Задача выполнена!")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def delete_task_callback(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    delete_task(task_id, callback.from_user.id)
    await callback.message.edit_text("🗑️ Задача удалена.")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def edit_task_callback(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    user_data[callback.from_user.id] = {"state": "editing_text", "task_id": task_id}
    await callback.message.answer("Введите новый текст задачи:", reply_markup=cancel_kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "ignore" or c.data == "cancel_date" or c.data == "cancel_time")
async def handle_cancel(callback: types.CallbackQuery):
    if callback.data.startswith("cancel"):
        if callback.from_user.id in user_data:
            del user_data[callback.from_user.id]
        await callback.message.edit_text("❌ Отменено.")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("cal_prev_") or c.data.startswith("cal_next_"))
async def change_month(callback: types.CallbackQuery):
    _, direction, year_str, month_str = callback.data.split("_")
    year, month = int(year_str), int(month_str)
    if direction == "prev":
        month -= 1
        if month == 0: month = 12; year -= 1
    else:
        month += 1
        if month == 13: month = 1; year += 1
    await callback.message.edit_reply_markup(reply_markup=generate_calendar(year, month))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("day_"))
async def select_day(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_data or user_data[user_id].get("state") != "awaiting_date":
        await callback.answer("Ошибка")
        return
    _, year, month, day = callback.data.split("_")
    date_str = f"{year}-{int(month):02d}-{int(day):02d}"
    user_data[user_id]["date"] = date_str
    user_data[user_id]["state"] = "awaiting_time"
    await callback.message.edit_text("Выберите час:", reply_markup=generate_hours_kb(date_str))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("hour_"))
async def select_hour(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_data or user_data[user_id].get("state") != "awaiting_time":
        await callback.answer("Ошибка")
        return
    hour = callback.data.split("_")[1]
    user_data[user_id]["hour"] = hour
    date_str = user_data[user_id]["date"]
    await callback.message.edit_text(f"Вы выбрали {hour} часов. Теперь выберите минуты:", reply_markup=generate_minutes_kb(date_str, hour))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("min_"))
async def select_minute(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_data or user_data[user_id].get("state") != "awaiting_time":
        await callback.answer("Ошибка")
        return
    minute = callback.data.split("_")[1]
    data = user_data[user_id]
    full_datetime = f"{data['date']} {data['hour']}:{minute}:00"
    add_task(user_id, data["text"], full_datetime)

    # ===== ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ ВТОРОМУ ЧЕЛОВЕКУ =====
    if user_id == FAMILY_IDS[0]:
        partner_id = FAMILY_IDS[1]
    else:
        partner_id = FAMILY_IDS[0]

    try:
        await bot.send_message(
            partner_id,
            f"🔔 Добавлена новая задача!\n\n"
            f"📝 {data['text']}\n"
            f"🕒 {full_datetime}\n\n"
            f"Проверь в /start → «Мои задачи»."
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление партнёру: {e}")

    await callback.message.edit_text(f"✅ Задача добавлена:\n📝 {data['text']}\n🕒 {full_datetime}")
    del user_data[user_id]
    await callback.answer()

# ===== НАПОМИНАНИЯ =====
async def check_reminders():
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = sqlite3.connect('family_planner.db')
        cur = conn.cursor()
        cur.execute('SELECT id, user_id, text, due_date FROM tasks WHERE due_date <= ? AND done=0 AND reminded=0', (now,))
        tasks = cur.fetchall()
        for task_id, user_id, text, due in tasks:
            await bot.send_message(user_id, f"🔔 Напоминание: {text} (до {due})")
            cur.execute('UPDATE tasks SET reminded=1 WHERE id=?', (task_id,))
        conn.commit()
        conn.close()
        await asyncio.sleep(60)

# ===== ЗАПУСК =====
async def main():
    await asyncio.gather(
        dp.start_polling(bot),
        check_reminders()
    )

# Запуск бота теперь через app.py