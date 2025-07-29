import argparse
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.user_profile import get_user_profile
from core.sync_engine import push_profile_to_cloud, pull_profile_from_cloud, get_sync_status

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

def show_profile(args):
    """Shows the user's full profile."""
    user_profile = get_user_profile(args.user_id)
    if not user_profile.profile_path.exists():
        print(f"No profile found for user ID: {args.user_id}")
        return
    if args.json:
        print(json.dumps(user_profile.data, indent=4))
    else:
        print(user_profile.data)

def sync_push(args):
    """Pushes the user profile to the cloud."""
    try:
        push_profile_to_cloud(args.user_id)
        print(f"Profile for user {args.user_id} pushed successfully.")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")

def sync_pull(args):
    """Pulls the user profile from the cloud."""
    try:
        pull_profile_from_cloud(args.user_id)
        print(f"Profile for user {args.user_id} pulled successfully.")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")

def sync_status(args):
    """Checks the sync status of the user profile."""
    status = get_sync_status(args.user_id)
    print(f"Sync status for user {args.user_id}: {status}")

def main():
    """Main function for the Katana CLI."""
    parser = argparse.ArgumentParser(description="Katana AI CLI")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Profile commands
    parser_profile = subparsers.add_parser('profile', help='Manage user profiles')
    profile_subparsers = parser_profile.add_subparsers(dest='profile_command', required=True)
    parser_profile_show = profile_subparsers.add_parser('show', help='Show user profile')
    parser_profile_show.add_argument('user_id', type=int, help='The ID of the user')
    parser_profile_show.add_argument('--json', action='store_true', help='Output in JSON format')
    parser_profile_show.set_defaults(func=show_profile)

    # Sync commands
    parser_sync = subparsers.add_parser('sync', help='Sync user profiles')
    sync_subparsers = parser_sync.add_subparsers(dest='sync_command', required=True)

    parser_sync_push = sync_subparsers.add_parser('push', help='Push profile to cloud')
    parser_sync_push.add_argument('user_id', type=int, help='The ID of the user')
    parser_sync_push.set_defaults(func=sync_push)

    parser_sync_pull = sync_subparsers.add_parser('pull', help='Pull profile from cloud')
    parser_sync_pull.add_argument('user_id', type=int, help='The ID of the user')
    parser_sync_pull.set_defaults(func=sync_pull)

    parser_sync_status = sync_subparsers.add_parser('status', help='Check sync status')
    parser_sync_status.add_argument('user_id', type=int, help='The ID of the user')
    parser_sync_status.set_defaults(func=sync_status)

    # Legacy commands
    parser_prefs = subparsers.add_parser('user-prefs', help='View user preferences (legacy)')
    parser_prefs.add_argument('user_id', type=int, help='The ID of the user')
    parser_prefs.set_defaults(func=view_user_prefs)

    parser_recs = subparsers.add_parser('user-recs', help='Get command recommendations for a user (legacy)')
    parser_recs.add_argument('user_id', type=int, help='The ID of the user')
    parser_recs.add_argument('--top-n', type=int, default=5, help='Number of recommendations to show')
    parser_recs.set_defaults(func=get_user_recs)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
