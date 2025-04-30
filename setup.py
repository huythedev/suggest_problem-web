import os
import sys
import subprocess
import venv
import platform
import secrets
from setuptools import setup, find_packages, Command

# --- Constants ---
VENV_DIR = "venv"
REQUIREMENTS_FILE = "requirements.txt"
ENV_FILE = ".env"
ENV_EXAMPLE_FILE = ".env_example"

# --- Helper Functions ---
def _find_python_executable():
    """Tries to find a suitable python3 or python executable."""
    try:
        subprocess.run([sys.executable, "--version"], check=True, capture_output=True)
        print(f"Using Python executable: {sys.executable}")
        return sys.executable
    except Exception as e:
        print(f"Current sys.executable ({sys.executable}) failed: {e}")
    for cmd in ["python3", "python"]:
        try:
            subprocess.run([cmd, "--version"], check=True, capture_output=True)
            print(f"Found Python executable: {cmd}")
            try:
                path_result = subprocess.run(['where' if platform.system() == "Windows" else 'which', cmd], check=True, capture_output=True, text=True)
                full_path = path_result.stdout.splitlines()[0].strip()
                print(f"Full path: {full_path}")
                return full_path
            except Exception:
                print(f"Could not determine full path for {cmd}, using command name.")
                return cmd
        except FileNotFoundError: continue
        except Exception as e: print(f"Error checking {cmd}: {e}"); continue
    return None

def _get_venv_pip_executable(venv_dir):
    """Gets the path to the pip executable inside the virtual environment."""
    if platform.system() == "Windows":
        pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        pip_path = os.path.join(venv_dir, "bin", "pip")
    if not os.path.exists(pip_path):
         if platform.system() != "Windows":
             pip3_path = os.path.join(venv_dir, "bin", "pip3")
             if os.path.exists(pip3_path): return pip3_path
         print(f"Error: Could not find pip executable at {pip_path}")
         return None
    print(f"Using pip executable: {pip_path}")
    return pip_path

def _run_command(command, description):
    """Runs a command and prints output/errors."""
    print(f"\n--- {description} ---")
    print(f"Running: {' '.join(command)}")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        for line in process.stdout: print(line, end='')
        process.wait()
        if process.returncode != 0: print(f"\nError: Command failed with exit code {process.returncode}"); return False
        print(f"--- {description} completed successfully ---")
        return True
    except FileNotFoundError: print(f"Error: Command not found: {command[0]}"); return False
    except Exception as e: print(f"An unexpected error occurred: {e}"); return False

def _create_env_file():
    """Prompts user for essential config and creates the .env file."""
    print(f"\n--- Creating Configuration File ({ENV_FILE}) ---")
    if os.path.exists(ENV_FILE):
        print(f"'{ENV_FILE}' already exists. Skipping creation.")
        print(f"Please ensure it contains the necessary variables (MONGO_URI, FLASK_SECRET_KEY, ADMIN_USERNAME_1, ADMIN_PASSWORD_1).")
        return True
    print("The application needs some configuration. Please provide the following details:")
    mongo_uri = ""
    while not mongo_uri:
        mongo_uri = input("Enter your MongoDB Connection URI: ").strip()
        if not mongo_uri.startswith("mongodb+srv://") and not mongo_uri.startswith("mongodb://"):
            print("Warning: MongoDB URI usually starts with 'mongodb+srv://' or 'mongodb://'. Please double-check.")
            confirm = input("Use this URI anyway? (yes/no): ").lower().strip()
            if confirm != 'yes': mongo_uri = ""
    admin_user_1 = ""; admin_pass_1 = ""
    while not admin_user_1: admin_user_1 = input("Enter the desired username for the first admin: ").strip()
    while not admin_pass_1: admin_pass_1 = input("Enter the desired password for the first admin: ").strip()
    flask_secret_key = secrets.token_hex(24)
    print(f"Generated a default FLASK_SECRET_KEY.")
    try:
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.write(f"MONGO_URI='{mongo_uri}'\n"); f.write(f"FLASK_SECRET_KEY='{flask_secret_key}'\n"); f.write("\n# Admin Credentials - Use numbered format starting from 1\n")
            f.write(f"ADMIN_USERNAME_1='{admin_user_1}'\n"); f.write(f"ADMIN_PASSWORD_1='{admin_pass_1}'\n"); f.write("\n# Add more admins by incrementing the number (e.g., ADMIN_USERNAME_2, ADMIN_PASSWORD_2)\n")
        print(f"\nSuccessfully created '{ENV_FILE}' with your settings.")
        print(f"You can edit this file later to change the secret key or add more admin users.")
        return True
    except IOError as e:
        print(f"\nError: Could not write to '{ENV_FILE}': {e}"); print("Please create the '.env' file manually.")
        if os.path.exists(ENV_EXAMPLE_FILE): print(f"You can use '{ENV_EXAMPLE_FILE}' as a template.")
        return False

# --- Custom Setup Command ---
class SetupDevEnvironment(Command):
    """Custom command to set up the development environment (venv, deps, .env)."""
    description = 'Set up the development environment: create venv, install dependencies, create .env file.'
    user_options = [] # No options for this command

    def initialize_options(self):
        """Set default values for options."""
        pass

    def finalize_options(self):
        """Post-process options."""
        pass

    def run(self):
        """Execute the command."""
        print("Starting development environment setup...")

        # 1. Find Python
        python_exe = _find_python_executable()
        if not python_exe:
            print("Error: Could not find a suitable Python 3 executable ('python3' or 'python').")
            print("Please ensure Python 3.8+ is installed and in your PATH.")
            sys.exit(1)

        # 2. Create venv if it doesn't exist
        if os.path.exists(VENV_DIR):
            print(f"\nVirtual environment '{VENV_DIR}' already exists.")
        else:
            print(f"\nCreating virtual environment '{VENV_DIR}'...")
            try:
                builder = venv.EnvBuilder(with_pip=True)
                builder.create(VENV_DIR)
                print("Virtual environment created successfully.")
            except Exception as e:
                 print(f"Direct venv creation failed ({e}), attempting with subprocess...")
                 if not _run_command([python_exe, "-m", "venv", VENV_DIR], "Create Virtual Environment (Subprocess)"):
                     print("Error: Failed to create virtual environment.")
                     sys.exit(1)

        # 3. Find pip within venv
        pip_exe = _get_venv_pip_executable(VENV_DIR)
        if not pip_exe:
            print("Error: Failed to locate pip inside the virtual environment.")
            sys.exit(1)

        # 4. Install requirements
        if not os.path.exists(REQUIREMENTS_FILE):
            print(f"Error: '{REQUIREMENTS_FILE}' not found.")
            sys.exit(1)
        if not _run_command([pip_exe, "install", "-r", REQUIREMENTS_FILE], f"Install Dependencies from {REQUIREMENTS_FILE}"):
            print("Error: Failed to install dependencies.")
            sys.exit(1)

        # 5. Create .env file
        if not _create_env_file():
            pass

        # 6. Print activation instructions
        print("\n--- Setup Complete! ---")
        print("To activate the virtual environment, run:")
        if platform.system() == "Windows": print(f"  .\\{VENV_DIR}\\Scripts\\activate")
        else: print(f"  source {VENV_DIR}/bin/activate")
        print("After activation, you can run the application using:")
        print("  python run.py")
        print("-" * 25)


# --- Standard Setup Configuration ---
try:
    with open(REQUIREMENTS_FILE) as f:
        required = f.read().splitlines()
except FileNotFoundError:
    print(f"Warning: '{REQUIREMENTS_FILE}' not found. Dependencies might not be installed correctly by standard setup methods.")
    required = []

try:
    long_description = open('README.md').read()
except FileNotFoundError:
    long_description = 'Web Task Manager for Competitive Programming Problems'


setup(
    name='suggest-problem-web',
    version='1.0.0',
    description='Web Task Manager for Competitive Programming Problems',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Name / Organization',
    author_email='your.email@example.com',
    url='https://github.com/huythedev/suggest_problem-web',
    packages=find_packages(exclude=['venv']),
    include_package_data=True,
    install_requires=required,
    entry_points={
        'console_scripts': [],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: Flask',
        'Private :: Do Not Upload',
    ],
    python_requires='>=3.8',
    cmdclass={
        'setup_dev_env': SetupDevEnvironment,
    },
)
