# katana-ai

## Purpose

`katana-ai` is a Python application that demonstrates how to manage secrets and environment variables using a `.env` file. This project provides a basic framework for building a Python application with a focus on configuration management and testing.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/algoritmo911/katana-ai.git
   cd katana-ai
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running Tests

To run the tests, use the following command:

```bash
pytest
```

## Using .env

The `.env` file is used to store environment variables. You can copy the `.env.example` file to `.env` and modify it to your needs. The following variables are available:

- `SECRET_KEY`: A secret key for your application.
- `KATANA_ENV`: The environment for the application (e.g., `development`, `production`).
- `LOG_LEVEL`: The logging level for the application (e.g., `INFO`, `DEBUG`).