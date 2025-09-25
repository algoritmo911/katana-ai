# Katana AI

## 📜 Содержание

*   [📝 Обзор](#-обзор)
*   [🚀 Как начать](#-как-начать)
    *   [Установка](#1-установка)
    *   [Запуск](#2-запуск)
*   [🧪 Тестирование](#-тестирование)
    *   [Python-бот](#python-бот)
    *   [UI](#ui)
*   [🐛 Отладка](#-отладка)
*   [⚙️ Переменные окружения](#️-переменные-окружения)
*   [🤝 Управление зависимостями](#-управление-зависимостями)
    *   [Python](#python)
    *   [UI](#ui-1)
*   [🚀 Локальный запуск](#-локальный-запуск)

## 📝 Обзор

Этот проект состоит из двух основных частей:

*   **`/bot`**: Python-бот, который является ядром проекта.
*   **`/ui`**: Основной пользовательский интерфейс для взаимодействия с ботом.
*   **`/legacy_ui`**: Устаревший пользовательский интерфейс.

## 🚀 Как начать

### 1. Установка

**Клонируйте репозиторий:**

```bash
git clone https://github.com/algoritmo911/katana-ai.git
cd katana-ai
```

**Настройте Python-бота:**

```bash
cd bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Настройте UI:**

```bash
cd ../ui
npm install
```

### 2. Запуск

**Запустите бота:**

Для удобства вы можете использовать скрипт `start.sh`:

```bash
./start.sh
```

Или вручную:

```bash
cd bot
source venv/bin/activate
python katana_bot.py
```

**Запустите UI:**

```bash
cd ../ui
npm run dev
```

## 🧪 Тестирование

### Python-бот

Чтобы запустить тесты для бота:

```bash
cd bot
python -m unittest discover
```

### UI

Чтобы запустить тесты для UI:

```bash
cd ../ui
npm test
```

## 🐛 Отладка

*   **Ошибка `ModuleNotFoundError` в Python:** Убедитесь, что вы активировали виртуальное окружение (`source venv/bin/activate`).
*   **Проблемы с `npm`:** Попробуйте удалить `node_modules` и `package-lock.json`, а затем снова запустить `npm install`.

## ⚙️ Переменные окружения

Создайте файл `.env` в директории `bot/` по примеру `.env.example`:

```env
# .env.example

# Telegram
KATANA_TELEGRAM_TOKEN=123456:ABCDEF

# OpenAI
OPENAI_API_KEY=sk-...

# Supabase
SUPABASE_URL=https://....supabase.co
SUPABASE_KEY=...
```

> **Опционально: Doppler**
>
> Если вы используете Doppler для управления секретами, убедитесь, что он настроен правильно.

## 🤝 Управление зависимостями

### Python

Мы используем `pip-tools` для управления Python-зависимостями.

*   `requirements.in`: здесь вы указываете необходимые пакеты.
*   `requirements.txt`: этот файл генерируется автоматически.

**Установка и обновление зависимостей:**

```bash
# Установка pip-tools
pip install pip-tools

# Компиляция requirements.in в requirements.txt
pip-compile bot/requirements.in

# Установка зависимостей из requirements.txt
pip install -r bot/requirements.txt
```

### UI

Зависимости для UI управляются через `package.json`.

## 🚀 Локальный запуск

**Запустите бота в режиме разработки:**

```bash
./start.sh --dev
```

**Запустите тесты:**

```bash
./start.sh --test
```
