from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ENV = os.getenv("KATANA_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
