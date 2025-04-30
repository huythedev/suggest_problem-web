import os
import subprocess
import sys

# Define the host and port
host = "0.0.0.0"
port = "12345"
app_module = "app:app"

# Get the absolute path to the directory containing this script (project root)
# project_root = os.path.dirname(os.path.abspath(__file__)) # Not strictly needed now

# --- Remove environment preparation ---
# env = os.environ.copy()
# env['PYTHONPATH'] = project_root
# print(f"Setting PYTHONPATH for subprocess to: {env['PYTHONPATH']}")
# --- End removal ---

# Determine the operating system
if os.name == 'nt':  # Windows
    print(f"Detected Windows. Starting Waitress server on {host}:{port}...")
    command = [
        sys.executable, # Use the same python interpreter that's running this script
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
    subprocess.run(command, check=True) # Removed env=env, cwd=project_root
except FileNotFoundError:
    server_name = "Waitress" if os.name == 'nt' else "Gunicorn"
    print(f"Error: {server_name} not found. Make sure it's installed.")
    print("You might need to run:")
    if os.name == 'nt':
        print(f"  pip install waitress")
    else:
        print(f"  pip install gunicorn")
    sys.exit(1)
except subprocess.CalledProcessError as e:
    print(f"Error running the server: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("\nServer stopped.")
    sys.exit(0)
