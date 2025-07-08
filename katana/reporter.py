import json
import os
from datetime import datetime, timedelta, timezone

# Assuming knowledge_base.py defines these constants for file paths
from .knowledge_base import KNOWLEDGE_FILE, REFLECTIONS_FILE, DATA_DIR

REPORT_FILE = os.path.join(DATA_DIR, "weekly_report.md")
INSIGHTS_FILE = os.path.join(DATA_DIR, "insights_digest.json")


def _load_data(filepath: str) -> list:
    """Loads data from a JSON file."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {filepath}. Returning empty list.")
            return []

def generate_insights(knowledge_data: list, reflections_data: list) -> list:
    """
    Generates insights from knowledge and reflection data.
    This is a basic implementation. It can be expanded to perform more complex analysis.
    """
    insights = []

    # Example Insight: Count of new knowledge items
    insights.append({
        "type": "knowledge_count",
        "value": len(knowledge_data),
        "summary": f"Registered {len(knowledge_data)} new knowledge items this week."
    })

    # Example Insight: Count of new reflections
    insights.append({
        "type": "reflections_count",
        "value": len(reflections_data),
        "summary": f"Recorded {len(reflections_data)} new reflections this week."
    })

    # Example Insight: Key themes from reflections (simple keyword check)
    if reflections_data:
        themes = {}
        for item in reflections_data:
            # Assuming reflection items have a 'content' or 'text' field
            text_content = item.get('content', item.get('text', '')).lower()
            if "learning" in text_content:
                themes["learning"] = themes.get("learning", 0) + 1
            if "challenge" in text_content:
                themes["challenge"] = themes.get("challenge", 0) + 1
            if "success" in text_content:
                themes["success"] = themes.get("success", 0) + 1

        if themes:
            insights.append({
                "type": "reflection_themes",
                "value": themes,
                "summary": f"Key themes from reflections: {json.dumps(themes)}."
            })

    # Save insights to a file
    with open(INSIGHTS_FILE, 'w') as f:
        json.dump(insights, f, indent=4)

    return insights

def format_report_markdown(insights: list, knowledge_data: list, reflections_data: list) -> str:
    """
    Formats the generated insights and data into a Markdown report.
    """
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report_content = f"# Weekly Knowledge Digest - {report_date}\n\n"

    report_content += "## Summary Insights\n"
    if not insights:
        report_content += "- No specific insights generated this week.\n"
    else:
        for insight in insights:
            report_content += f"- {insight.get('summary', 'N/A')}\n"
    report_content += "\n"

    report_content += "## New Knowledge Items\n"
    if not knowledge_data:
        report_content += "- No new knowledge items recorded this week.\n"
    else:
        for i, item in enumerate(knowledge_data[:10]): # Displaying max 10 items for brevity
            # Assuming knowledge items have 'title' and 'summary' or 'content'
            title = item.get('title', f"Knowledge Item {item.get('id', i+1)}")
            summary = item.get('summary', item.get('content', 'No summary available.'))
            report_content += f"### {title}\n"
            report_content += f"{summary}\n\n"
        if len(knowledge_data) > 10:
            report_content += f"- ...and {len(knowledge_data) - 10} more items.\n"
    report_content += "\n"

    report_content += "## New Reflections\n"
    if not reflections_data:
        report_content += "- No new reflections recorded this week.\n"
    else:
        for i, item in enumerate(reflections_data[:10]): # Displaying max 10 items
            # Assuming reflections have a 'title' or 'theme' and 'content'
            title = item.get('title', item.get('theme', f"Reflection {item.get('id', i+1)}"))
            content = item.get('content', 'No content available.')
            report_content += f"### {title}\n"
            report_content += f"{content}\n\n"
        if len(reflections_data) > 10:
            report_content += f"- ...and {len(reflections_data) - 10} more items.\n"

    report_content += "\n---\nEnd of Report\n"
    return report_content

def generate_weekly_report(for_past_days: int = 7) -> str:
    """
    Generates a weekly report based on data fetched within the last `for_past_days`.
    This function loads all data and then filters it.
    A more optimized approach would be to fetch data for the specific period if
    the `knowledge_base` module supported it.
    """
    print(f"Generating weekly report for data from the past {for_past_days} days...")

    knowledge_all = _load_data(KNOWLEDGE_FILE)
    reflections_all = _load_data(REFLECTIONS_FILE)

    # Filter data for the last week
    # This assumes items have a 'created_at' or 'timestamp' field.
    # If not, all loaded data will be considered "this week's".
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=for_past_days)

    def filter_by_date(item):
        date_str = item.get('created_at', item.get('timestamp', item.get('updated_at')))
        if date_str:
            try:
                item_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if item_date.tzinfo is None: # If no timezone, assume UTC (common for DBs)
                    item_date = item_date.replace(tzinfo=timezone.utc)
                return item_date >= cutoff_date
            except ValueError:
                # If date format is unexpected, include it by default or log warning
                print(f"Warning: Could not parse date '{date_str}' for item {item.get('id')}. Including by default.")
                return True
        return True # Include if no date field is found

    knowledge_this_week = [k for k in knowledge_all if filter_by_date(k)]
    reflections_this_week = [r for r in reflections_all if filter_by_date(r)]

    print(f"Found {len(knowledge_this_week)} knowledge items and {len(reflections_this_week)} reflections for this week's report.")

    insights = generate_insights(knowledge_this_week, reflections_this_week)
    report_markdown = format_report_markdown(insights, knowledge_this_week, reflections_this_week)

    with open(REPORT_FILE, 'w') as f:
        f.write(report_markdown)

    print(f"Weekly report generated and saved to {REPORT_FILE}")
    print(f"Insights digest saved to {INSIGHTS_FILE}")

    return report_markdown

def get_latest_report() -> str | None:
    """Returns the content of the latest generated report file."""
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, 'r') as f:
            return f.read()
    return None

if __name__ == "__main__":
    print("Running weekly report generation test...")
    # Create dummy data files for testing if they don't exist
    if not os.path.exists(KNOWLEDGE_FILE):
        dummy_knowledge = [
            {"id": 1, "title": "Test Knowledge 1", "content": "Content for TK1", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": 2, "title": "Old Knowledge", "content": "This is old", "created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()}
        ]
        with open(KNOWLEDGE_FILE, 'w') as f: json.dump(dummy_knowledge, f, indent=4)
        print(f"Created dummy knowledge file: {KNOWLEDGE_FILE}")

    if not os.path.exists(REFLECTIONS_FILE):
        dummy_reflections = [
            {"id": 1, "theme": "Test Reflection 1", "content": "Reflection on learning something new.", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": 2, "theme": "Past Reflection", "content": "A thought from last month.", "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()}
        ]
        with open(REFLECTIONS_FILE, 'w') as f: json.dump(dummy_reflections, f, indent=4)
        print(f"Created dummy reflections file: {REFLECTIONS_FILE}")

    report = generate_weekly_report()
    if report:
        print("\n--- Generated Report (first 200 chars) ---")
        print(report[:200] + "...")
        print("--- End of Preview ---")

    latest_report_content = get_latest_report()
    if latest_report_content:
        print(f"\nSuccessfully retrieved latest report from {REPORT_FILE}")
    else:
        print(f"\nCould not retrieve latest report from {REPORT_FILE}")

    print(f"\nReport file location: {os.path.abspath(REPORT_FILE)}")
    print(f"Insights file location: {os.path.abspath(INSIGHTS_FILE)}")
