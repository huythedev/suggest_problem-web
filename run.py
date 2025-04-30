import os
import subprocess
import sys

# Define the host and port
host = "0.0.0.0"
port = "12345"
# Use the package name (assuming the folder is the package) and the app object
# If your folder name has hyphens, Python might not treat it as a package directly.
# Let's stick with 'app:app' for now and ensure the path is correct.
app_module = "app:app"

# Get the absolute path to the directory containing this script (project root)
project_root = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory of the project root
parent_dir = os.path.dirname(project_root)

# Prepare environment variables for the subprocess
# Add the *parent* directory to PYTHONPATH so Python can find the 'suggest_problem-web' package
# Or add the project_root itself if 'app.py' is directly importable from there. Let's try project_root first.
env = os.environ.copy()
# Prepend project_root to PYTHONPATH, creating it if it doesn't exist
env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
print(f"Setting PYTHONPATH for subprocess: {env['PYTHONPATH']}")

# Determine the operating system
if os.name == 'nt':  # Windows
    print(f"Detected Windows. Starting Waitress server on {host}:{port}...")
    command = [
        sys.executable,
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
        # Gunicorn might need --chdir project_root depending on setup
        # "--chdir", project_root,
    ]
else:
    print(f"Unsupported operating system: {os.name}")
    sys.exit(1)

# Run the command with the modified environment
try:
    print(f"Executing command: {' '.join(command)}")
    # Pass the modified environment to the subprocess
    subprocess.run(command, check=True, env=env)
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
