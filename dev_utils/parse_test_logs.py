import json
from pathlib import Path
from collections import Counter

LOG_FILE = Path("katana_events.log") # Assuming it's in the project root

def parse_and_analyze_logs():
    if not LOG_FILE.exists():
        print(f"Log file not found: {LOG_FILE.resolve()}")
        return

    print(f"--- Analyzing log file: {LOG_FILE.resolve()} ---")

    parsed_logs = []
    line_count = 0
    parse_errors = 0

    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line_count += 1
            line = line.strip()
            if not line:
                continue
            try:
                log_entry = json.loads(line)
                parsed_logs.append(log_entry)
            except json.JSONDecodeError:
                print(f"Error parsing JSON on line {line_num}: {line[:100]}...")
                parse_errors += 1

    print(f"\n--- Summary ---")
    print(f"Total lines read: {line_count}")
    print(f"Successfully parsed JSON entries: {len(parsed_logs)}")
    print(f"JSON parse errors: {parse_errors}")

    if not parsed_logs:
        print("No logs to analyze further.")
        return

    print(f"\n--- First few log entries (max 5) ---")
    for i, entry in enumerate(parsed_logs[:5]):
        print(f"Log #{i+1}:")
        print(f"  Timestamp: {entry.get('timestamp')}")
        print(f"  Level:     {entry.get('level')}")
        print(f"  Module:    {entry.get('module')}")
        print(f"  User ID:   {entry.get('user_id')}")
        print(f"  Chat ID:   {entry.get('chat_id')}")
        print(f"  MessageID: {entry.get('message_id')}")
        print(f"  Message:   {entry.get('message', '')[:150]}...") # Truncate long messages
        if 'exc_info' in entry and entry['exc_info']:
            print(f"  Exc_Info:  Present (not fully displayed here)")


    levels = [entry.get('level', 'UNKNOWN') for entry in parsed_logs]
    level_counts = Counter(levels)
    print("\n--- Log Counts by Level ---")
    for level, count in level_counts.items():
        print(f"  {level}: {count}")

    print("\n--- Distinct User IDs (sample) ---")
    user_ids = set(entry.get('user_id') for entry in parsed_logs if entry.get('user_id'))
    print(f"  Found {len(user_ids)} distinct user_ids: {list(user_ids)[:10]}") # Print up to 10

    print("\n--- Distinct Chat IDs (sample) ---")
    chat_ids = set(entry.get('chat_id') for entry in parsed_logs if entry.get('chat_id'))
    print(f"  Found {len(chat_ids)} distinct chat_ids: {list(chat_ids)[:10]}")

    print("\n--- Modules Generating Logs (sample) ---")
    modules = set(entry.get('module') for entry in parsed_logs if entry.get('module'))
    print(f"  Found {len(modules)} distinct modules: {list(modules)[:10]}")


if __name__ == "__main__":
    parse_and_analyze_logs()
