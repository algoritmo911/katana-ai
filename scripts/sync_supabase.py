import sys
import os

# Add project root to Python path to allow importing katana modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from katana.knowledge_base import synchronize_all_data
from katana.reporter import generate_weekly_report
from datetime import datetime

def main():
    """
    Main function to trigger Supabase data synchronization
    and weekly report generation if it's Sunday.
    """
    print("Starting Supabase synchronization script...")
    try:
        synchronize_all_data()
        print("Supabase synchronization script completed successfully.")
    except Exception as e:
        print(f"Error during Supabase synchronization: {e}")
        # Decide if script should exit or continue to report generation
        # For now, let's allow report generation even if sync fails,
        # as it might operate on previously synced data.
        # sys.exit(1)

    # Check if today is Sunday (weekday() returns 0 for Monday, 6 for Sunday)
    today = datetime.utcnow().weekday()
    # For testing, you can force report generation:
    # force_report = True
    # if today == 6 or force_report:
    if today == 6: # 6 is Sunday
        print("It's Sunday. Generating weekly report...")
        try:
            generate_weekly_report()
            print("Weekly report generation completed successfully.")
        except Exception as e:
            print(f"Error during weekly report generation: {e}")
            sys.exit(1) # Exit with error if report generation fails
    else:
        print(f"Today is not Sunday (it's {datetime.utcnow().strftime('%A')}). Skipping weekly report generation.")

if __name__ == "__main__":
    main()
