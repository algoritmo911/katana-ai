import os
import time
import requests
import schedule
import telebot
from supabase import create_client, Client
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- Constants ---
HEARTBEAT_FILE_PATH = "/tmp/katana_heartbeat.txt"
HEARTBEAT_MAX_AGE_SECONDS = 600  # 10 minutes

class PraetorAgent:
    """
    An autonomous agent for monitoring the health of the Katana AI ecosystem.
    """

    def __init__(self):
        """
        Initializes the PraetorAgent, setting up connections to external services.
        """
        # Service URLs and credentials from environment variables
        self.katana_api_url = os.environ.get("KATANA_API_URL", "http://localhost:8080/healthcheck")
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        self.telegram_token = os.environ.get("PRAETOR_TELEGRAM_TOKEN")
        self.admin_chat_id = os.environ.get("PRAETOR_ADMIN_CHAT_ID")

        # Validate that essential configuration is present
        if not all([self.supabase_url, self.supabase_key, self.telegram_token, self.admin_chat_id]):
            raise ValueError("One or more required environment variables are missing.")

        # Initialize clients
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.telegram_bot = telebot.TeleBot(self.telegram_token)
        self.session = requests.Session()

        print("PraetorAgent initialized successfully.")

    def send_telegram_alert(self, message: str):
        """
        Sends an alert message to the configured admin Telegram channel.
        """
        try:
            print(f"Sending alert: {message}")
            self.telegram_bot.send_message(self.admin_chat_id, f"🚨 **Praetor Alert** 🚨\n\n{message}", parse_mode="Markdown")
        except Exception as e:
            print(f"Error sending Telegram alert: {e}")

    def log_status(self, service_name: str, status: str, latency_ms: int, details: str = ""):
        """
        Logs the status of a monitored service to the Supabase table.
        """
        try:
            record = {
                "service_name": service_name,
                "status": status,
                "latency_ms": latency_ms,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.supabase.table("praetor_logs").insert(record).execute()
        except Exception as e:
            error_message = f"Failed to log status for {service_name} to Supabase: {e}"
            print(error_message)
            # Send a critical alert if logging fails, as it's a meta-problem
            self.send_telegram_alert(f"**Critical Logging Failure!**\n{error_message}")

    def check_api_gateway(self):
        """
        Checks the health of the main Katana API gateway.
        """
        service_name = "Katana API Gateway"
        start_time = time.time()
        try:
            response = self.session.get(self.katana_api_url, timeout=10)
            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200 and response.json().get("status") == "ok":
                self.log_status(service_name, "online", latency_ms)
                print(f"{service_name} is online (latency: {latency_ms}ms).")
            else:
                details = f"Status Code: {response.status_code}, Response: {response.text}"
                self.log_status(service_name, "offline", latency_ms, details)
                self.send_telegram_alert(f"**{service_name} is OFFLINE.**\nDetails: {details}")
                print(f"{service_name} is offline. {details}")

        except requests.exceptions.RequestException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            details = f"Request failed: {e}"
            self.log_status(service_name, "offline", latency_ms, details)
            self.send_telegram_alert(f"**{service_name} is OFFLINE.**\nDetails: {details}")
            print(f"{service_name} is offline. {details}")

    def check_database(self):
        """
        Checks the health of the Supabase database connection.
        """
        service_name = "Memory Vault (Supabase)"
        start_time = time.time()
        try:
            # Perform a simple, fast, read-only query
            self.supabase.table("praetor_logs").select("id").limit(1).execute()
            latency_ms = int((time.time() - start_time) * 1000)
            self.log_status(service_name, "online", latency_ms)
            print(f"{service_name} is online (latency: {latency_ms}ms).")

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            details = f"Database query failed: {e}"
            self.log_status(service_name, "offline", latency_ms, details)
            self.send_telegram_alert(f"**{service_name} is OFFLINE.**\nDetails: {details}")
            print(f"{service_name} is offline. {details}")

    def check_heartbeat_file(self):
        """
        Checks for a recent heartbeat file from other services.
        """
        service_name = "System Heartbeat"
        latency_ms = 0 # Not applicable for file check
        try:
            if not os.path.exists(HEARTBEAT_FILE_PATH):
                details = f"Heartbeat file not found at {HEARTBEAT_FILE_PATH}"
                self.log_status(service_name, "offline", latency_ms, details)
                self.send_telegram_alert(f"**{service_name} is MISSING.**\nDetails: {details}")
                print(f"{service_name} is missing. {details}")
                return

            last_modified_timestamp = os.path.getmtime(HEARTBEAT_FILE_PATH)
            age_seconds = time.time() - last_modified_timestamp

            if age_seconds > HEARTBEAT_MAX_AGE_SECONDS:
                details = f"Heartbeat file is stale. Last updated {int(age_seconds)} seconds ago."
                self.log_status(service_name, "offline", latency_ms, details)
                self.send_telegram_alert(f"**{service_name} is STALE.**\nDetails: {details}")
                print(f"{service_name} is stale. {details}")
            else:
                self.log_status(service_name, "online", latency_ms, f"Last update {int(age_seconds)}s ago.")
                print(f"{service_name} is online (last update: {int(age_seconds)}s ago).")

        except Exception as e:
            details = f"Error checking heartbeat file: {e}"
            self.log_status(service_name, "offline", latency_ms, details)
            self.send_telegram_alert(f"**{service_name} check FAILED.**\nDetails: {details}")
            print(f"{service_name} check failed. {details}")

    def run_checks(self):
        """
        Runs all health checks sequentially.
        """
        print(f"\n--- Running health checks at {datetime.now()} ---")
        self.check_api_gateway()
        self.check_database()
        self.check_heartbeat_file()
        print("--- Health checks complete ---")

    def start(self):
        """
        Starts the monitoring loop.
        """
        print("PraetorAgent is starting its watch...")
        self.send_telegram_alert("PraetorAgent is online and starting its watch. ⚔️")

        # Schedule the checks to run every 5 minutes
        schedule.every(5).minutes.do(self.run_checks)

        # Run checks once immediately on startup
        self.run_checks()

        while True:
            schedule.run_pending()
            time.sleep(1)
