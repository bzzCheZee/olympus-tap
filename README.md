# Olympus Tap

## Деплой

### 1. GitHub
- Создайте репозиторий и загрузите все файлы.

### 2. Render (API)
- Зайдите на render.com, создайте Web Service.
- Подключите GitHub репозиторий.
- В Environment Variables добавьте `BOT_TOKEN` и `ADMIN_ID` (значения из .env.example).
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Нажмите Create. Через минуту получите URL типа `https://olympus-tap.onrender.com`.

### 3. Cloudflare Pages (фронтенд)
- Зайдите на pages.cloudflare.com, создайте проект.
- Подключите тот же GitHub репозиторий.
- Build command оставьте пустым, Output directory укажите `.`
- Нажмите Deploy. Получите URL типа `https://olympus-tap.pages.dev`.

### 4. Обновление бота
- В файле `bot.py` убедитесь, что `webapp_url` указывает на ваш Cloudflare Pages URL.
- Если вы использовали другой URL, измените его в коде и залейте изменения в GitHub.
- Render автоматически перезапустит бота.

Готово! Теперь в Telegram бот открывает мини-приложение, а API работает на Render.