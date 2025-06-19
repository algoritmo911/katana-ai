
import asyncio
import aiohttp # pip install aiohttp
import os # For API Key from environment variable
import json # For printing dict results
from datetime import datetime, timezone # For logging timestamp
from pathlib import Path # Not directly used in this version of class, but good for future
import traceback # For logging full tracebacks

# --- Configuration ---
DEFAULT_STEAM_API_KEY = "YOUR_STEAM_API_KEY_PLEASE_REPLACE"

# --- Logging Helper (Simple) ---
def log_event_ga(level, message):
    """Basic logging to stdout for Game Agent operations."""
    timestamp = datetime.now(timezone.utc).isoformat() # Use timezone.utc explicitly
    print(f"[{timestamp}] [KatanaGameAgent:{level.upper()}] {message}")

class KatanaGameAgent:
    def __init__(self, steam_api_key: str):
        if not steam_api_key or steam_api_key == DEFAULT_STEAM_API_KEY:
            log_event_ga("warning", "Steam API key is missing or is the default placeholder. Real API calls will likely fail.")
        self.steam_api_key = steam_api_key
        self.base_steam_url = "https://api.steampowered.com"
        log_event_ga("info", f"KatanaGameAgent initialized. Steam API Key ends with: ...{steam_api_key[-4:] if steam_api_key and len(steam_api_key) > 4 else 'N/A'}")

    async def get_player_summary(self, steam_id: str):
        """
        Asynchronously fetches player summary from the Steam API.
        Returns player data dictionary or None on error.
        """
        if not self.steam_api_key or self.steam_api_key == DEFAULT_STEAM_API_KEY:
            log_event_ga("error", f"Cannot get player summary for {steam_id}: Steam API key not configured.")
            return None

        url = f"{self.base_steam_url}/ISteamUser/GetPlayerSummaries/v2/"
        params = {
            'key': self.steam_api_key,
            'steamids': steam_id
        }
        timeout = aiohttp.ClientTimeout(total=10)

        log_event_ga("debug", f"Requesting player summary for Steam ID: {steam_id} from {url}")

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    response_text = await resp.text()
                    try:
                        data = json.loads(response_text)
                    except json.JSONDecodeError as e_json_inner:
                        log_event_ga("error", f"JSON decode error fetching player summary for {steam_id}: {e_json_inner}. Response text snippet: {response_text[:200]}")
                        return None

                    players = data.get('response', {}).get('players', [])
                    if players:
                        log_event_ga("info", f"Successfully fetched player summary for {steam_id}: {players[0].get('personaname', 'N/A')}")
                        return players[0]
                    else:
                        log_event_ga("warning", f"No player data found in response for {steam_id}. Response: {data}")
                        return None
        except aiohttp.ClientResponseError as e_http:
            log_event_ga("error", f"HTTP error fetching player summary for {steam_id}: {e_http.status} {e_http.message} (URL: {e_http.request_info.url if e_http.request_info else url})")
            return None
        except aiohttp.ClientError as e_client:
            log_event_ga("error", f"Client error (e.g., timeout, connection) fetching player summary for {steam_id}: {e_client}")
            return None
        except asyncio.TimeoutError:
             log_event_ga("error", f"Request timed out fetching player summary for {steam_id} (URL: {url})")
             return None
        except Exception as e:
            log_event_ga("error", f"Unexpected error fetching player summary for {steam_id}: {e.__class__.__name__} - {e}")
            log_event_ga("debug", f"Traceback for get_player_summary error: {traceback.format_exc()}")
            return None

    async def send_chat_message(self, steam_id: str, message: str):
        """
        Asynchronously simulates sending a chat message.
        """
        log_event_ga("info", f"Attempting to send chat message to {steam_id}: '{message}'")
        await asyncio.sleep(0.1)
        log_event_ga("info", f"Successfully sent (simulated) chat message to {steam_id}: '{message}'")
        return {"status": "success", "steam_id": steam_id, "message_sent": message}

async def main():
    """Main function to demonstrate concurrent agent operations."""
    log_event_ga("info", "Starting KatanaGameAgent demo...")

    steam_api_key_env = os.getenv('STEAM_API_KEY', DEFAULT_STEAM_API_KEY)
    if steam_api_key_env == DEFAULT_STEAM_API_KEY or not steam_api_key_env:
        log_event_ga("critical", "STEAM_API_KEY environment variable not set or using default placeholder. Real API calls will fail.")
        log_event_ga("critical", "Please set STEAM_API_KEY in your environment. Exiting demo.")
        return

    agent = KatanaGameAgent(steam_api_key=steam_api_key_env)

    steam_ids_to_test = [
        "76561197960435530",
        "76561198000000001",
        "76561197960265728"
    ]

    tasks = []
    for sid in steam_ids_to_test:
        tasks.append(agent.get_player_summary(sid))
        tasks.append(agent.send_chat_message(sid, "Катана приветствует тебя. Вектор выравнивания задан."))

    log_event_ga("info", f"Gathering {len(tasks)} tasks to run concurrently...")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    log_event_ga("info", "All tasks completed. Processing results...")

    for i, res in enumerate(results):
        original_task_description = "Unknown task"
        task_type_index = i % 2
        steam_id_for_task = steam_ids_to_test[i // 2]

        if task_type_index == 0:
            original_task_description = f"get_player_summary for {steam_id_for_task}"
        else:
            original_task_description = f"send_chat_message to {steam_id_for_task}"

        if isinstance(res, Exception):
            log_event_ga("error", f"Task '{original_task_description}' resulted in an exception: {res}")
        elif res is None and task_type_index == 0 :
            log_event_ga("warning", f"Task '{original_task_description}' returned None (likely an error during API call).")
        elif isinstance(res, dict):
            log_event_ga("info", f"Result for '{original_task_description}':")
            try:
                print(json.dumps(res, indent=2, ensure_ascii=False))
            except TypeError:
                 print(str(res))
        else:
             log_event_ga("info", f"Task '{original_task_description}' completed with a non-dictionary, non-None result: {res}")

    log_event_ga("info", "KatanaGameAgent demo finished.")

if __name__ == "__main__":
    asyncio.run(main())
