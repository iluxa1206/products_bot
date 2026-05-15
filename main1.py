import asyncio
import logging
import os
import sqlite3
from datetime import datetime

import pandas as pd
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile

# --- Конфигурация ---
BOT_TOKEN = "6668788537:AAFmwHuuJkn9g_DUQeIZ-dXZYN-hfkPL_IQ"
PDF_FOLDER_PATH = 'product_files/'
DB_NAME = 'db.db'

# Настройка логирования в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

all_products = [
    "Назад", "Общая презентация", "Российские акции", "Российские акции вне НРД",
    "Российские IPO SPO", "Российские акции 120_80", "Международные облигации", "Российские облигации",
    "Валютные облигации с выплатой дохода", "Хедж-фонд А+", "Хедж-фонд Р5", "Хедж-фонд Д5",
    "Хедж-фонд Ю5", "Хедж-фонд Д1", "Облигации Р1", "Хедж-фонд М3", "Мгновенная ликвидность",
    "Хедж фонды", "Результаты фондов", "Сравнение с индексами"
]

# --- Состояния (FSM) ---
class AddingUser(StatesGroup):
    name = State()
    admin = State()

class RequestPhoneNumber(StatesGroup):
    phone_number = State()

# --- Работа с базой данных ---

def init_db():
    """Создает необходимые таблицы при запуске [cite: 37, 38]"""
    conn = sqlite3.connect(DB_NAME)
    # Основная таблица пользователей (уже есть в вашем файле) [cite: 38]
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                    (user_name TEXT PRIMARY KEY, is_admin INTEGER)''')
    # Таблица логов скачивания
    conn.execute('''CREATE TABLE IF NOT EXISTS download_logs
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_name TEXT,
                     file_name TEXT,
                     timestamp DATETIME)''')
    conn.commit()
    conn.close()

def is_admin(user_id_or_name):
    if not user_id_or_name: return False
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE user_name = ?", (str(user_id_or_name).replace("@", ""),))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def is_registered(user_id_or_name):
    if not user_id_or_name: return False
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_name FROM users WHERE user_name = ?", (str(user_id_or_name).replace("@", ""),))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def log_event(user_name, file_name):
    """Записывает действие в базу логов"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO download_logs (user_name, file_name, timestamp) VALUES (?, ?, ?)",
                 (user_name, file_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# --- Клавиатуры ---

def get_main_menu():
    kb = [[types.KeyboardButton(text="Презентации")]]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_menu():
    kb = [
        [types.KeyboardButton(text="Добавить пользователя")],
        [types.KeyboardButton(text="Выгрузить отчет (Excel)")],
        [types.KeyboardButton(text="Презентации")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_unlogin_menu():
    kb = [[types.KeyboardButton(text="Ввести номер телефона")]]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- Обработчики команд ---

@dp.message(Command('start'))
async def send_welcome(message: types.Message, state: FSMContext):
    user_name = message.from_user.username
   
    # Если username нет, проверяем сохраненный в сессии телефон
    if not user_name:
        data = await state.get_data()
        user_name = data.get('my_phone')

    if not is_registered(user_name) and not is_admin(user_name):
        await message.answer(
            "Извините, у вас нет доступа к этому боту.\n"
            "Обратитесь к администратору для регистрации.",
            reply_markup=get_unlogin_menu()
        )
        await message.answer(f"Ваш ID/Username для регистрации: {user_name if user_name else 'не указан'}")
        return

    if is_admin(user_name):
        await message.answer("Привет, Админ! Доступ разрешен.", reply_markup=get_admin_menu())
    else:
        await message.answer("Привет! Выберите раздел:", reply_markup=get_main_menu())

# --- Логика Администратора ---

@dp.message(F.text == "Добавить пользователя")
async def admin_add_start(message: types.Message, state: FSMContext):
    if is_admin(message.from_user.username):
        await message.answer("Введите никнейм (без @) или телефон нового пользователя:")
        await state.set_state(AddingUser.name)

@dp.message(AddingUser.name)
async def admin_add_name(message: types.Message, state: FSMContext):
    await state.update_data(new_user_name=message.text.replace("@", "").strip())
    await message.answer("Выберите роль:\n1 - Администратор\n0 - Пользователь")
    await state.set_state(AddingUser.admin)

@dp.message(AddingUser.admin, F.text.in_(['0', '1']))
async def admin_add_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    u_name = data['new_user_name']
    u_role = int(message.text)
   
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR REPLACE INTO users (user_name, is_admin) VALUES (?, ?)", (u_name, u_role))
    conn.commit()
    conn.close()
   
    await message.answer(f"Пользователь {u_name} сохранен.", reply_markup=get_admin_menu())
    await state.clear()

@dp.message(F.text == "Выгрузить отчет (Excel)")
async def export_report(message: types.Message):
    if is_admin(message.from_user.username):
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM download_logs", conn)
        conn.close()
       
        file_path = "report.xlsx"
        df.to_excel(file_path, index=False)
        await message.answer_document(FSInputFile(file_path), caption="Отчет об активности")
        os.remove(file_path)

# --- Логика пользователя и файлов ---

@dp.message(F.text == "Ввести номер телефона")
async def user_phone_start(message: types.Message, state: FSMContext):
    await message.answer("Введите ваш номер телефона (89876543210):")
    await state.set_state(RequestPhoneNumber.phone_number)

@dp.message(RequestPhoneNumber.phone_number)
async def user_phone_finish(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(my_phone=phone)
    await message.answer(f"Номер {phone} временно привязан к сессии. Нажмите /start")
    await state.clear()

@dp.message(F.text == "Презентации")
async def show_strategies(message: types.Message):
    user_id = message.from_user.username
    if is_registered(user_id) or is_admin(user_id):
        kb = [[types.KeyboardButton(text=p)] for p in all_products]
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.answer("Выберите стратегию:", reply_markup=keyboard)

@dp.message(F.text == "Назад")
async def go_back(message: types.Message):
    user = message.from_user.username
    markup = get_admin_menu() if is_admin(user) else get_main_menu()
    await message.answer("Главное меню", reply_markup=markup)

@dp.message(F.text.in_(all_products))
async def send_pdf(message: types.Message):
    if message.text == "Назад": return
   
    user_name = message.from_user.username or "Unknown"
    product = message.text
    found = False

    if os.path.exists(PDF_FOLDER_PATH):
        for file in os.listdir(PDF_FOLDER_PATH):
            if file.endswith(".pdf") and product.lower() in file.lower():
                await message.answer_document(FSInputFile(os.path.join(PDF_FOLDER_PATH, file)))
                log_event(user_name, file)
                found = True
   
    if not found:
        await message.answer("К сожалению, файлы по этой стратегии еще не загружены.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
