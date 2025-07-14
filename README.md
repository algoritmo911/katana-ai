# Katana

This project contains a Telegram bot and a React-based UI.

## Dev Setup

### Prerequisites

-   [Python 3.11+](https://www.python.org/downloads/)
-   [Node.js 20+](https://nodejs.org/en/download/package-manager) (LTS recommended)
-   `pip`
-   `npm`

### Backend (Bot)

The bot is built with Python and the `pyTelegramBotAPI` library.

**1. Set up a virtual environment**

From the project root:

```sh
python -m venv .venv
source .venv/bin/activate
```

**2. Install dependencies**

```sh
pip install -r bot/requirements.txt
```

**3. Set up environment variables**

The bot requires a Telegram token. You can get one by talking to the [@BotFather](https://t.me/BotFather).

Create a `.env` file in the `bot/` directory with the following content:

```env
KATANA_TELEGRAM_TOKEN="<your-token>"
```

**4. Run the bot**

```sh
python bot/katana_bot.py
```

### Frontend (UI)

The UI is a standard [Vite](https://vitejs.dev/) + [React](https://react.dev/) project.

There are two UI projects:

-   `ui/`: The main project
-   `legacy_ui/`: A legacy project

The setup is the same for both. From the project root:

**1. Go to the UI directory**

```sh
cd ui/ # or legacy_ui/
```

**2. Install dependencies**

```sh
npm install
```

**3. Run the dev server**

```sh
npm run dev
```

This will start the UI at [http://localhost:5173](http://localhost:5173).

### Running Tests

**Bot**

From the project root:

```sh
pytest bot/
```

**UI**

The UI projects do not have tests set up yet.

### Code Style

**Bot**

We use [Ruff](https://docs.astral.sh/ruff/) to format and lint the Python code.

From the project root:

```sh
# Format
ruff format bot/

# Lint
ruff check bot/
```

**UI**

We use [Prettier](https://prettier.io/) to format and [ESLint](https://eslint.org/) to lint the code.

From `ui/` or `legacy_ui/`:

```sh
# Format
npm run format

# Lint
npm run lint
```

## Project Structure

-   `.github/`: CI/CD workflows
-   `bot/`: Python bot
-   `ui/`: Main UI
-   `legacy_ui/`: Legacy UI

## Docker (Optional)

You can also run the bot and the UI in Docker.

### Prerequisites

-   [Docker](https://docs.docker.com/get-docker/)
-   [Docker Compose](https://docs.docker.com/compose/install/)

### Build and run the containers

From the project root:

```sh
docker-compose up --build
```

This will start:

-   The bot
-   The main UI at [http://localhost:5173](http://localhost:5173)
-   The legacy UI at [http://localhost:5174](http://localhost:5174)

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
