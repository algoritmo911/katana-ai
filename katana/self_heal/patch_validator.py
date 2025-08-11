import os
import shutil
import subprocess

class PatchValidator:
    """
    Validates a code patch by running tests.
    """

    def validate_patch(self, file_path: str, original_snippet: str, patched_snippet: str) -> bool:
        """
        Validates a patch by applying it and running the test suite.

        Args:
            file_path: The path to the file to patch.
            original_snippet: The original code snippet to be replaced.
            patched_snippet: The new code snippet to apply.

        Returns:
            True if the patch is valid (tests pass), False otherwise.
        """
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            return False

        backup_path = f"{file_path}.bak"

        try:
            # 1. Read the original file content
            with open(file_path, 'r') as f:
                original_content = f.read()

            # 2. Create the patched content
            if original_snippet not in original_content:
                print("Error: Original snippet not found in the file.")
                return False
            patched_content = original_content.replace(original_snippet, patched_snippet)

            # 3. Backup the original file and write the patched version
            shutil.copy(file_path, backup_path)
            with open(file_path, 'w') as f:
                f.write(patched_content)

            # 4. Run the test suite
            print("Running test suite...")
            result = subprocess.run(["pytest"], capture_output=True, text=True)

            if result.returncode == 0:
                print("Tests passed successfully.")
                return True
            else:
                print("Tests failed after applying the patch.")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False

        except Exception as e:
            print(f"An error occurred during patch validation: {e}")
            return False
        finally:
            # 5. Restore the original file from backup
            if os.path.exists(backup_path):
                shutil.move(backup_path, file_path)
                print(f"Restored original file: {file_path}")
