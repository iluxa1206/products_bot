import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, ReplyKeyboardRemove

# --- Конфигурация ---
BOT_TOKEN = "6668788537:AAFmwHuuJkn9g_DUQeIZ-dXZYN-hfkPL_IQ"
PDF_FOLDER_PATH = Path('product_files/')
DB_NAME = 'db.db'

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
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
    """Создает необходимые таблицы при запуске"""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute('''CREATE TABLE IF NOT EXISTS users
                        (user_name TEXT PRIMARY KEY, is_admin INTEGER)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS download_logs
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_name TEXT,
                         file_name TEXT,
                         timestamp DATETIME)''')
        conn.commit()
        logger.info("База данных инициализирована")
    except sqlite3.Error as e:
        logger.error(f"Ошибка инициализации БД: {e}")
    finally:
        conn.close()

def is_admin(user_id_or_name):
    if not user_id_or_name: 
        return False
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE user_name = ?", (str(user_id_or_name).replace("@", ""),))
        result = cursor.fetchone()
        return result and result[0] == 1
    except sqlite3.Error as e:
        logger.error(f"Ошибка проверки админа: {e}")
        return False
    finally:
        if conn:
            conn.close()

def is_registered(user_id_or_name):
    if not user_id_or_name: 
        return False
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_name FROM users WHERE user_name = ?", (str(user_id_or_name).replace("@", ""),))
        result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        logger.error(f"Ошибка проверки регистрации: {e}")
        return False
    finally:
        if conn:
            conn.close()

def log_event(user_name, file_name):
    """Записывает действие в базу логов"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT INTO download_logs (user_name, file_name, timestamp) VALUES (?, ?, ?)",
                     (user_name, file_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        logger.info(f"Пользователь {user_name} скачал файл: {file_name}")
    except sqlite3.Error as e:
        logger.error(f"Ошибка логирования: {e}")
    finally:
        if conn:
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
    
    logger.info(f"Пользователь {user_name} запустил бота")

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
    try:
        data = await state.get_data()
        u_name = data['new_user_name']
        u_role = int(message.text)
       
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT OR REPLACE INTO users (user_name, is_admin) VALUES (?, ?)", (u_name, u_role))
        conn.commit()
        conn.close()
       
        await message.answer(f"Пользователь {u_name} сохранен.", reply_markup=get_admin_menu())
        await state.clear()
        logger.info(f"Админ добавил пользователя {u_name} с ролью {'админ' if u_role else 'пользователь'}")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        await message.answer("Произошла ошибка при добавлении пользователя.")
        await state.clear()

@dp.message(F.text == "Выгрузить отчет (Excel)")
async def export_report(message: types.Message):
    try:
        if is_admin(message.from_user.username):
            conn = sqlite3.connect(DB_NAME)
            df = pd.read_sql_query("SELECT * FROM download_logs", conn)
            conn.close()
           
            file_path = "report.xlsx"
            df.to_excel(file_path, index=False)
            await message.answer_document(FSInputFile(file_path), caption="Отчет об активности")
            os.remove(file_path)
            logger.info(f"Админ {message.from_user.username} выгрузил отчет")
    except Exception as e:
        logger.error(f"Ошибка при выгрузке отчета: {e}")
        await message.answer("Произошла ошибка при формировании отчета.")

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
        logger.info(f"Пользователь {user_id} открыл меню презентаций")

@dp.message(F.text == "Назад")
async def go_back(message: types.Message):
    user = message.from_user.username
    markup = get_admin_menu() if is_admin(user) else get_main_menu()
    await message.answer("Главное меню", reply_markup=markup)

@dp.message(F.text.in_(all_products))
async def send_pdf(message: types.Message):
    try:
        if message.text == "Назад": 
            return
       
        user_name = message.from_user.username or "Unknown"
        product = message.text
        found = False

        if PDF_FOLDER_PATH.exists():
            for file in os.listdir(PDF_FOLDER_PATH):
                if file.endswith(".pdf") and product.lower() in file.lower():
                    file_path = PDF_FOLDER_PATH / file
                    await message.answer_document(FSInputFile(file_path))
                    log_event(user_name, file)
                    found = True
                    break
       
        if not found:
            await message.answer("К сожалению, файлы по этой стратегии еще не загружены.")
            logger.warning(f"Файл для '{product}' не найден (пользователь: {user_name})")
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        await message.answer("Произошла ошибка при загрузке файла.")

async def main():
    init_db()
    logger.info("Бот запускается...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка polling: {e}")
    finally:
        await bot.session.close()
        logger.info("Бот остановлен, сессия закрыта")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Необработанная ошибка: {e}")
