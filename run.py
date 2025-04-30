import os
import subprocess
import sys
import platform  # Import platform

# --- Configuration ---
host = "0.0.0.0"
port = "12345"
app_module = "app:app"
VENV_DIR = "venv"
ENV_FILE = ".env"
SETUP_COMMAND = "python setup.py setup_dev_env"
if platform.system() != "Windows":
    SETUP_COMMAND = "python3 setup.py setup_dev_env"  # Suggest python3 for non-Windows

# --- Environment Setup Check ---
venv_exists = os.path.isdir(VENV_DIR)
env_file_exists = os.path.isfile(ENV_FILE)

if venv_exists and env_file_exists:
    print("Virtual environment and .env file found. Proceeding to start server...")
    # Refined check for running inside the virtual environment
    is_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if not is_venv:
        print("\n" + "=" * 50)
        print("WARNING: You don't seem to be running inside the virtual environment!")
        print("Please activate it first:")
        if platform.system() == "Windows":
            print(f"  .\\{VENV_DIR}\\Scripts\\activate")
        else:
            print(f"  source {VENV_DIR}/bin/activate")
        print("Then run 'python run.py' again.")
        print("=" * 50 + "\n")
        # Optionally exit here, or let it potentially fail later
        # sys.exit(1)

elif not venv_exists:
    print("\n" + "=" * 50)
    print(f"ERROR: Virtual environment directory '{VENV_DIR}' not found.")
    print("Please run the setup command first:")
    print(f"  {SETUP_COMMAND}")
    print("=" * 50 + "\n")
    sys.exit(1)
elif not env_file_exists:
    print("\n" + "=" * 50)
    print(f"ERROR: Configuration file '{ENV_FILE}' not found.")
    print("Please run the setup command first to create it:")
    print(f"  {SETUP_COMMAND}")
    print("=" * 50 + "\n")
    sys.exit(1)
# --- End Environment Setup Check ---

# Determine the operating system
if os.name == 'nt':  # Windows
    print(f"Detected Windows. Starting Waitress server on {host}:{port}...")
    command = [
        sys.executable,  # Use the same python interpreter that's running this script
        "-m",
        "waitress",
        f"--host={host}",
        f"--port={port}",
        app_module
    ]
elif os.name == 'posix':  # Linux, macOS, etc.
    print(f"Detected POSIX system. Starting Gunicorn server on {host}:{port}...")
    command = [
        "gunicorn",
        "-w", "4",
        "-b", f"{host}:{port}",
        app_module
    ]
else:
    print(f"Unsupported operating system: {os.name}")
    sys.exit(1)

# Run the command simply, assuming run.py is executed from the project root
try:
    print(f"Executing command: {' '.join(command)}")
    subprocess.run(command, check=True)  # Removed env=env, cwd=project_root
except FileNotFoundError:
    server_name = "Waitress" if os.name == 'nt' else "Gunicorn"
    print(f"Error: {server_name} not found. Make sure it's installed.")
    print("You might need to run:")
    if os.name == 'nt':
        print(f"  pip install waitress")
    else:
        print(f"  pip install gunicorn")
    print("\nMake sure the virtual environment is activated before running.")
    sys.exit(1)
except subprocess.CalledProcessError as e:
    print(f"Error running the server: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("\nServer stopped.")
    sys.exit(0)
