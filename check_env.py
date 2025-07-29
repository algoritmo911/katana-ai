import sys
import subprocess

def check_python_version():
    """Checks if the Python version is 3.8 or higher."""
    print("Checking Python version...")
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        return False
    print("Python version check passed.")
    return True

def check_pip_dependencies():
    """Checks if all pip dependencies are installed."""
    print("Checking pip dependencies...")
    try:
        subprocess.run(["pip", "check"], check=True)
        print("Pip dependencies check passed.")
        return True
    except subprocess.CalledProcessError:
        print("Error: Pip dependencies are not satisfied. Please run 'pip install -r requirements.txt'")
        return False

def check_docker():
    """Checks if Docker is running."""
    print("Checking Docker...")
    try:
        subprocess.run(["docker", "ps"], check=True, capture_output=True)
        print("Docker check passed.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Docker is not running or not installed.")
        return False

def check_docker_compose():
    """Checks if docker-compose is installed."""
    print("Checking docker-compose...")
    try:
        subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
        print("docker-compose check passed.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: docker-compose is not installed.")
        return False

def main():
    """Runs all environment checks."""
    checks = [
        check_python_version,
        check_pip_dependencies,
        check_docker,
        check_docker_compose,
    ]

    all_passed = True
    for check in checks:
        if not check():
            all_passed = False

    if all_passed:
        print("\nAll environment checks passed successfully!")
    else:
        print("\nSome environment checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
