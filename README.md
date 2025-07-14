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

## 🧪 Testing & Mocking Strategy

We use `jest` with `jsdom` environment.

### 📁 setupTests.js

This file includes global mocks and setup for testing libraries.

### 📁 __mocks__/

Custom mocks live in the `/__mocks__/` directory and are auto-loaded via `jest.config.js`.

> If you're mocking:
- `socket.io-client`: use `__mocks__/socket-io-client-mock.js`
- `@mui/icons-material/*`: use `__mocks__/mui-icon-mock.js`

### 🛠️ Example configuration

```js
// jest.config.js
module.exports = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/setupTests.js"],
  moduleNameMapper: {
    "\\.(css|less|scss)$": "identity-obj-proxy",
    "^@mui/icons-material/(.*)$": "<rootDir>/__mocks__/mui-icon-mock.js",
    "^socket.io-client$": "<rootDir>/__mocks__/socket-io-client-mock.js"
  }
};
```
