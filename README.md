# Инструкция по запуску Telegram-бота для презентаций

## 📋 Требования
- Python 3.8+
- Локальный ПК с постоянным подключением к интернету
- Токен бота от @BotFather

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Запуск бота
```bash
python main1.py
```

## 🔧 Для стабильной работы на Windows

### Вариант 1: Использование PM2 (рекомендуется)
1. Установите Node.js с https://nodejs.org/
2. Установите PM2:
   ```bash
   npm install -g pm2
   ```
3. Создайте файл `ecosystem.config.js`:
   ```javascript
   module.exports = {
     apps: [{
       name: "telegram-bot",
       script: "python",
       args: "main1.py",
       env: {
         PYTHONUNBUFFERED: "1"
       },
       restart_delay: 4000,
       max_restarts: 10,
       watch: false
     }]
   };
   ```
4. Запустите:
   ```bash
   pm2 start ecosystem.config.js
   pm2 save
   pm2 startup
   ```

### Вариант 2: Планировщик заданий Windows
1. Откройте "Планировщик заданий"
2. Создайте задачу:
   - Триггер: "При входе в систему"
   - Действие: `python.exe` с аргументом `C:\путь\к\main1.py`
   - Галочка "Запускать независимо от входа пользователя"

### Вариант 3: NSSM (Windows Service)
1. Скачайте NSSM с https://nssm.cc/
2. Создайте сервис:
   ```bash
   nssm install TelegramBot
   nssm set TelegramBot Application "C:\Python39\python.exe"
   nssm set TelegramBot AppParameters "C:\путь\к\main1.py"
   nssm set TelegramBot AppDirectory "C:\путь\к\проекту"
   nssm set TelegramBot DisplayName "Telegram Bot"
   nssm set TelegramBot StartService SERVICE_AUTO_START
   nssm start TelegramBot
   ```

### Вариант 4: Docker (если установлен Docker Desktop)
```bash
docker build -t telegram-bot .
docker run -d --restart always --name bot telegram-bot
```

## 🛡️ Чтобы бот не блокировался

### 1. Антивирус
Добавьте папку проекта в исключения антивируса:
- Папка с файлами `.py`
- Файл `db.db`
- Файл лога `bot.log`

### 2. Брандмауэр Windows
Разрешите Python доступ к сети:
```
Панель управления → Брандмауэр → Разрешить приложение → Python
```

### 3. Стабильное соединение
- Используйте проводное подключение вместо Wi-Fi
- Настройте статический IP или резервирование
- Рассмотрите UPS для защиты от отключений электричества

## 📊 Мониторинг

### Логи
Бот ведет логи в файле `bot.log`:
```bash
tail -f bot.log  # Linux/Mac
Get-Content bot.log -Wait  # PowerShell
```

### Проверка статуса
```bash
# Для PM2
pm2 status
pm2 logs telegram-bot

# Для Docker
docker ps
docker logs bot
```

## 👥 Управление пользователями

1. Запустите бота и напишите `/start`
2. Если нет доступа — получите ваш username/телефон
3. Администратор должен добавить вас через меню "Добавить пользователя"

## 📝 Примечания

- Храните токен бота в секрете!
- Регулярно делайте бэкап `db.db`
- Файлы презентаций должны быть в папке `product_files/`

## 🆘 Troubleshooting

**Бот не запускается:**
```bash
pip install --upgrade aiogram pandas openpyxl
```

**Ошибка доступа к БД:**
- Закройте все программы, которые могут использовать `db.db`
- Проверьте права доступа к папке

**Бот периодически отключается:**
- Проверьте стабильность интернета
- Увеличьте таймауты в настройках роутера
- Используйте PM2/NSSM для автоперезапуска
