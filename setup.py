import subprocess
import sys

def install(package):
    """Install a package using pip."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def install_dependencies():
    """Install dependencies from the requirements.txt file."""
    try:
        # Attempt to open and read the requirements.txt file
        with open('requirements.txt') as f:
            for line in f:
                # Install each dependency listed in requirements.txt
                install(line.strip())
        print("Setup has successfully completed.")
    except FileNotFoundError:
        print("Error: 'requirements.txt' file not found. Make sure it is in the same directory as setup.py.")
    except Exception as e:
        print(f"An unexpected error occurred during installation: {e}")

if __name__ == "__main__":
    # Check if pip is available
    try:
        import pip
    except ImportError:
        print("pip is not installed. Please install pip to continue.")
        sys.exit(1)

    # Execute dependency installation
    install_dependencies()
