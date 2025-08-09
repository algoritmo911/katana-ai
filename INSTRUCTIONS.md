# Инструкция по настройке и запуску workflow "Telegram to Google Sheets"

Этот документ поможет вам настроить и запустить workflow, который при получении команды `/start` в Telegram боте сохраняет информацию о пользователе в Google Sheets и отправляет ответное сообщение с кнопкой.

## 1. Предварительные требования

Перед началом убедитесь, что у вас есть:
- **Токен Telegram бота:** Вы можете получить его у [@BotFather](https://t.me/BotFather) в Telegram.
- **Проект в Google Cloud Platform:** С активированным **Google Sheets API**.
- **OAuth Client ID и Client Secret:** Созданные в вашем проекте Google Cloud Platform. Убедитесь, что в настройках OAuth-клиента добавлен `https://<your-n8n-domain>/rest/oauth2-credential/callback` в качестве разрешенного URI перенаправления.

## 2. Создание Credentials (учетных данных) в n8n

Вам нужно создать два набора учетных данных в вашем n8n (как на удаленном "Корвин", так и на локальном).

### а) Telegram Credentials
1. В интерфейсе n8n перейдите в **Credentials** -> **Add Credential**.
2. В поиске найдите и выберите **Telegram**.
3. В поле **Credential Name** введите `MyTelegramCreds` (или любое другое имя).
4. В поле **Access Token** вставьте токен вашего Telegram бота.
5. Нажмите **Save**.

### б) Google Sheets Credentials
1. В интерфейсе n8n перейдите в **Credentials** -> **Add Credential**.
2. Найдите и выберите **Google Sheets**.
3. В поле **Credential Name** введите `MyGoogleSheetsCreds` (или любое другое имя).
4. Вставьте ваш **Client ID** и **Client Secret** из Google Cloud Console.
5. Нажмите на кнопку **"Sign in with Google"** и пройдите аутентификацию, предоставив необходимые разрешения.
6. Нажмите **Save**.

## 3. Импорт и настройка Workflow

1.  **Импортируйте** файл `telegram_start_corwin.json` в ваш n8n.
2.  Откройте импортированный workflow. Вы увидите три узла: `Telegram Trigger`, `Google Sheets`, `Telegram Sender`.
3.  **Настройте Telegram Trigger:**
    *   Кликните на узел `Telegram Trigger`.
    *   В поле **Credential** выберите созданные вами учетные данные Telegram (`MyTelegramCreds`).
4.  **Настройте Google Sheets:**
    *   Кликните на узел `Google Sheets`.
    *   В поле **Credential** выберите созданные вами учетные данные Google Sheets (`MyGoogleSheetsCreds`).
    *   В поле **Spreadsheet ID** вставьте ID вашей Google таблицы. Его можно найти в URL таблицы (`.../spreadsheets/d/SPREADSHEET_ID/...`).
    *   В поле **Sheet Name** укажите имя листа, в который будут записываться данные (например, `Sheet1`).
    *   Убедитесь, что на этом листе есть как минимум три колонки для `user_id`, `username`, и `timestamp`.
5.  **Настройте Telegram Sender:**
    *   Кликните на узел `Telegram Sender`.
    *   В поле **Credential** выберите те же учетные данные Telegram, что и в триггере.

## 4. Активация и тестирование

1.  Сохраните workflow, нажав кнопку **Save**.
2.  Активируйте workflow, переключив его в режим **Active** в правом верхнем углу.
3.  Откройте чат с вашим Telegram ботом и отправьте команду `/start`.
4.  **Проверка:**
    *   Вы должны получить в ответ сообщение "Данные сохранены. Что дальше?" с кнопкой "Дальше".
    *   В вашей Google таблице должна появиться новая строка с вашим user_id, username и временем.

Этот workflow готов к переносу на любой n8n instance. Просто повторите шаги 2, 3 и 4 на локальном сервере.
