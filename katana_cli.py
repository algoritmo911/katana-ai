import argparse
import json
from user_profile import get_user_profile

def view_user_prefs(args):
    """Prints the user's preferences."""
    user_profile = get_user_profile(args.user_id)
    if not user_profile.profile_path.exists():
        print(f"No profile found for user ID: {args.user_id}")
        return
    print(json.dumps(user_profile.data.get('preferences', {}), indent=4))

def get_user_recs(args):
    """Prints command recommendations for the user."""
    user_profile = get_user_profile(args.user_id)
    if not user_profile.profile_path.exists():
        print(f"No profile found for user ID: {args.user_id}")
        return

    recommendations = user_profile.get_command_recommendations(top_n=args.top_n)

    if not recommendations:
        print("No recommendations available for this user.")
        return

    print("Command Recommendations:")
    for i, command in enumerate(recommendations, 1):
        print(f"{i}. {command}")

def main():
    """Main function for the Katana CLI."""
    parser = argparse.ArgumentParser(description="Katana AI CLI")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # User preferences command
    parser_prefs = subparsers.add_parser('user-prefs', help='View user preferences')
    parser_prefs.add_argument('user_id', type=int, help='The ID of the user')
    parser_prefs.set_defaults(func=view_user_prefs)

    # User recommendations command
    parser_recs = subparsers.add_parser('user-recs', help='Get command recommendations for a user')
    parser_recs.add_argument('user_id', type=int, help='The ID of the user')
    parser_recs.add_argument('--top-n', type=int, default=5, help='Number of recommendations to show')
    parser_recs.set_defaults(func=get_user_recs)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
