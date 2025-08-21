import logging
import threading
import time

# Attempt to import the bot object for notifications
try:
    from bot.katana_bot import bot as telegram_bot
except (ImportError, ModuleNotFoundError):
    # This might happen if the orchestrator is run in a context where `bot` is not in sys.path.
    # We create a placeholder so the application can still load.
    telegram_bot = None
    logging.getLogger(__name__).warning(
        "Could not import telegram_bot. Notifications will only be logged."
    )


from katana.self_heal import diagnostics, patcher

logger = logging.getLogger(__name__)


class SelfHealingOrchestrator:
    """
    Automates the process of diagnosing and healing the system.
    """

    def __init__(self, config):
        """
        Initializes the orchestrator.

        :param config: A dictionary containing configuration.
                       Expected keys:
                       - log_file_path (str): Path to the log file to monitor.
                       - service_name (str): The systemd service name to manage.
                       - check_interval_seconds (int): How often to run diagnostics.
                       - error_threshold (int): Number of errors to trigger a restart.
                       - notification_chat_id (str): The Telegram chat ID for alert notifications.
        """
        self.config = config
        self.is_running = False
        self.thread = None

    def start(self):
        """Starts the orchestrator in a background thread."""
        if self.is_running:
            logger.info("Orchestrator is already running.")
            return

        logger.info("Starting Self-Healing Orchestrator...")
        self.is_running = True
        self.thread = threading.Thread(target=self._run_monitoring_loop, daemon=True)
        self.thread.start()
        logger.info("Self-Healing Orchestrator started.")

    def stop(self):
        """Stops the orchestrator."""
        if not self.is_running:
            logger.info("Orchestrator is not running.")
            return

        logger.info("Stopping Self-Healing Orchestrator...")
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
        logger.info("Self-Healing Orchestrator stopped.")

    def _run_monitoring_loop(self):
        """The main loop that periodically checks system health."""
        while self.is_running:
            try:
                self._perform_health_check()
            except Exception as e:
                logger.error(f"Error during health check: {e}", exc_info=True)

            # Wait for the next check
            time.sleep(self.config.get("check_interval_seconds", 60))

    def _perform_health_check(self):
        """
        Performs a single health check and triggers actions if needed.
        """
        logger.debug("Running a new health check cycle...")

        # 1. Analyze logs
        log_file = self.config.get("log_file_path")
        if not log_file:
            logger.warning("No log file path configured. Skipping log analysis.")
            return

        errors_found, message = diagnostics.analyze_logs(log_file)
        if errors_found is None:
            logger.warning(f"Could not analyze logs: {message}")
            return

        logger.info(message)

        # 2. Decide on action
        error_threshold = self.config.get("error_threshold", 5)
        if len(errors_found) > error_threshold:
            logger.warning(
                f"Error threshold ({error_threshold}) exceeded with {len(errors_found)} errors. "
                "Triggering corrective action."
            )
            self._trigger_corrective_action(errors_found)

    def _trigger_corrective_action(self, errors_found):
        """
        Triggers a corrective action, like restarting a service.
        """
        service_name = self.config.get("service_name")
        if not service_name:
            logger.error("No service name configured. Cannot perform corrective action.")
            return

        # For now, the only action is to restart the service.
        # This could be extended with more sophisticated rules.
        logger.info(f"Attempting to restart service: {service_name}")
        success, message = patcher.restart_service(service_name)

        if success:
            logger.info(f"Service restart successful: {message}")
            self._send_notification(
                f"✅ Service '{service_name}' restarted successfully after detecting {len(errors_found)} errors."
            )
        else:
            logger.error(f"Service restart failed: {message}")
            self._send_notification(
                f"❌ Failed to restart service '{service_name}' after detecting {len(errors_found)} errors. "
                f"Manual intervention may be required. Details: {message}"
            )

    def _send_notification(self, message):
        """
        Sends a notification to the operator via Telegram.
        """
        # Log the notification locally regardless of whether it's sent
        logger.info(f"NOTIFICATION: {message}")

        chat_id = self.config.get("notification_chat_id")
        if not telegram_bot:
            logger.warning("Telegram bot not available. Skipping notification.")
            return
        if not chat_id:
            logger.warning("Notification chat ID not configured. Skipping notification.")
            return

        try:
            telegram_bot.send_message(chat_id, message)
            logger.info(f"Successfully sent notification to chat_id {chat_id}.")
        except Exception as e:
            logger.error(
                f"Failed to send Telegram notification to chat_id {chat_id}: {e}",
                exc_info=True,
            )
