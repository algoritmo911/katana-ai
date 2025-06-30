import os

def check_file_existence(filenames):
    """
    Checks for the existence of a list of files and prints their status.

    Args:
        filenames (list): A list of filenames to check.
    """
    for filename in filenames:
        if os.path.exists(filename):
            print(f"File '{filename}' exists.")
        else:
            print(f"File '{filename}' is missing.")

if __name__ == "__main__":
    files_to_check = ["katana.commands.json", "katana.history.json"]
    check_file_existence(files_to_check)
