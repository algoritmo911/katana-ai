import sys
import os

# Add project root to Python path to allow importing katana modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from katana.reporter import get_latest_report, generate_weekly_report, REPORT_FILE

def main():
    """
    CLI script to display the latest weekly report.
    If the report file doesn't exist, it offers to generate it.
    """
    print("Attempting to display the latest weekly report...")

    if not os.path.exists(REPORT_FILE):
        print(f"Report file not found at: {os.path.abspath(REPORT_FILE)}")
        user_input = input("Would you like to try generating a new report now? (yes/no): ").strip().lower()
        if user_input == 'yes':
            print("Generating a new report...")
            try:
                generate_weekly_report()
                print("Report generation complete.")
            except Exception as e:
                print(f"Error generating report: {e}")
                sys.exit(1)
        else:
            print("Exiting without displaying a report.")
            sys.exit(0)

    report_content = get_latest_report()

    if report_content:
        print("\n--- Latest Weekly Report ---")
        print(report_content)
        print("--- End of Report ---")
    else:
        # This case should ideally be handled by the generation step if the file existed but was empty.
        print("No report content found, even after attempting generation or if the file was empty.")
        print(f"Please check: {os.path.abspath(REPORT_FILE)}")

if __name__ == "__main__":
    main()
