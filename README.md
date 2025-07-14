# Katana AI

## 🚀 Run project locally

```bash
npm install
npm run dev
```

## 🧪 Run tests

```bash
npm test
```

## Project Structure

-   `/bot`: Python bot
-   `/ui`: Main UI
-   `/legacy_ui`: Legacy UI

## Environment Variables

Create a `.env` file in the `bot/` directory with the following content:

```env
# .env
PORT=3000
SECRET_KEY=my_super_secret
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## 🧪 Testing & Debugging

To run tests:

```bash
npm test
```

If you face issues with specific mocks (like `socket.io-client`, or `@mui/icons-material`), check `setupTests.js`.

Some tests may require isolated mocking or patching due to runtime env (CI / local).
