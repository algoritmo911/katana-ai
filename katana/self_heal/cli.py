import argparse
from katana.self_heal import diagnostics, patcher

def main():
    """CLI for the self-healing module."""
    parser = argparse.ArgumentParser(description="Katana Self-Healing Module")
    subparsers = parser.add_subparsers(dest="command")

    # Diagnostics command
    diag_parser = subparsers.add_parser("diagnose", help="Run diagnostics")
    diag_parser.add_argument("--log-file", type=str, help="Path to the log file to analyze")
    diag_parser.add_argument("--module-path", type=str, help="Path to the module to check integrity")
    diag_parser.add_argument("--expected-hash", type=str, help="Expected hash of the module")

    # Patcher command
    patch_parser = subparsers.add_parser("patch", help="Run patcher")
    patch_parser.add_argument("--restart-service", type=str, help="Name of the service to restart")
    patch_parser.add_argument("--apply-patch", type=str, help="Path to the patch file to apply")
    patch_parser.add_argument("--rollback", action="store_true", help="Roll back the latest commit")
    patch_parser.add_argument("--fetch-patch", type=str, help="URL to fetch a patch from")


    args = parser.parse_args()

    if args.command == "diagnose":
        if args.log_file:
            anomalies, message = diagnostics.analyze_logs(args.log_file)
            print(message)
            if anomalies:
                print("Anomalies found:")
                for anomaly in anomalies:
                    print(anomaly)
        if args.module_path and args.expected_hash:
            success, message = diagnostics.check_module_integrity(args.module_path, args.expected_hash)
            print(message)

    elif args.command == "patch":
        if args.restart_service:
            success, message = patcher.restart_service(args.restart_service)
            print(message)
        if args.apply_patch:
            success, message = patcher.apply_patch(args.apply_patch)
            print(message)
        if args.rollback:
            success, message = patcher.rollback_changes()
            print(message)
        if args.fetch_patch:
            patch_content, message = patcher.fetch_patch(args.fetch_patch)
            if patch_content:
                # For demonstration, just printing the patch. In a real scenario, you'd save it and apply it.
                print("Fetched patch content:")
                print(patch_content)
            else:
                print(message)


if __name__ == "__main__":
    main()
