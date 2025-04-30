import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import warnings

# --- Load Environment Variables FIRST ---
# Explicitly specify the path to the .env file in the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Go up one level from modules/
dotenv_path = os.path.join(project_root, '.env')

# Check if the .env file exists before trying to load
if os.path.exists(dotenv_path):
    print(f"Loading .env file from: {dotenv_path}")
    # Load the specific .env file. override=True might be useful if variables could exist elsewhere.
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    # Use warnings.warn for non-fatal issues
    warnings.warn(f".env file not found at {dotenv_path}. Using environment variables or defaults if available.")
    # Still call load_dotenv without path to load from actual environment variables if set
    load_dotenv(override=True) # Attempt to load from OS environment

# --- Now access environment variables ---

# --- Flask Secret Key ---
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'default-secret-key-please-change') # Provide a default for safety
if SECRET_KEY == 'default-secret-key-please-change':
    warnings.warn("FLASK_SECRET_KEY not set in environment. Using insecure default.")

# --- Allowed OJs ---
ALLOWED_OJS = ["Codeforces", "AtCoder", "UVA", "SPOJ", "Luogu", "Other"] # Add more as needed

# --- Admin Credentials ---
ADMIN_CREDENTIALS = {}
i = 1
while True:
    username_key = f'ADMIN_USERNAME_{i}'
    password_key = f'ADMIN_PASSWORD_{i}'
    username = os.getenv(username_key)
    password = os.getenv(password_key)

    if username and password:
        if username in ADMIN_CREDENTIALS:
            print(f"Warning: Duplicate admin username '{username}' found for index {i}. Check .env file.")
        ADMIN_CREDENTIALS[username] = password
        print(f"Loaded admin user '{username}' from environment (index {i}).")
        i += 1
    elif username or password:
        print(f"Warning: Incomplete admin credentials found for index {i}. Both {username_key} and {password_key} must be set. Skipping.")
        i += 1 # Increment to avoid infinite loop if only one is set
    else:
        # Stop when both username and password for the current index are not found
        break

if not ADMIN_CREDENTIALS:
    warnings.warn("No admin credentials found in environment variables (e.g., ADMIN_USERNAME_1, ADMIN_PASSWORD_1). Admin login will not work.")
    # Optionally set a default admin if none are found, or rely on the empty dict
    # ADMIN_CREDENTIALS['default_admin'] = 'default_password'

# --- MongoDB Connection ---
MONGO_URI = os.getenv('MONGO_URI')
db = None
mongo_client = None

if not MONGO_URI:
    print("Error: MONGO_URI not set in environment variables.")
else:
    try:
        print(f"DEBUG: Attempting MongoDB connection with URI: {MONGO_URI}")
        mongo_client = MongoClient(MONGO_URI)
        # The ismaster command is cheap and does not require auth.
        mongo_client.admin.command('ismaster')
        print("MongoDB server connection: SUCCESS")
        # Try accessing the default database specified in the URI
        db = mongo_client.get_database() # Gets default DB from URI
        print(f"MongoDB default database connection: SUCCESS")

    except ConfigurationError as e:
        print(f"MongoDB Configuration Error: {e}")
        print("Please check the format of your MONGO_URI.")
        db = None
        if mongo_client: mongo_client.close()
    except ConnectionFailure as e:
        print(f"MongoDB Connection Failure: {e}")
        print("Please check your MONGO_URI, network connection, and firewall settings.")
        db = None
        if mongo_client: mongo_client.close()
    except Exception as e:
        print(f"An unexpected error occurred during MongoDB connection: {e}")
        db = None
        if mongo_client: mongo_client.close()
