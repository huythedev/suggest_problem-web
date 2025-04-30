import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env file first
load_dotenv()

# --- Flask Configuration ---
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-replace-me-in-config')

# --- Application Constants ---
ALLOWED_OJS = sorted(['Codeforces', 'SPOJ', 'AtCoder', 'UVA', 'VNOJ', 'Other'])

# --- Load Admin Credentials ---
ADMINS = []
try:
    # Use the absolute path to .env relative to this config file if needed
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        print(f"Warning: .env file not found at {env_path}. Cannot load admin credentials.")
    else:
        with open(env_path, 'r') as f:
            lines = f.readlines()
            current_admin = {}
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line.startswith('ADMIN_USERNAME='):
                    if 'username' in current_admin:
                        print(f"Warning: Found new ADMIN_USERNAME before ADMIN_PASSWORD for {current_admin.get('username')}. Ignoring previous entry.")
                    username = line.split('=', 1)[1].strip("'\"")
                    current_admin = {'username': username}

                elif line.startswith('ADMIN_PASSWORD=') and 'username' in current_admin:
                    password = line.split('=', 1)[1].strip("'\"")
                    current_admin['password'] = password
                    ADMINS.append(current_admin)
                    current_admin = {}

            if 'username' in current_admin and 'password' not in current_admin:
                print(f"Warning: Incomplete admin entry found at end of file for username {current_admin.get('username')}.")

except Exception as e:
    print(f"Error parsing .env file for admin credentials: {e}")

if not ADMINS:
    print("Warning: No admin credentials loaded. Login will not be possible unless defaults are added.")
    # Optionally add a default admin here if needed as a fallback
    # ADMINS.append({'username': 'admin', 'password': 'password'})


# --- MongoDB Connection ---
MONGO_URI = os.environ.get(
    'MONGO_URI',
    'mongodb://localhost:27017/web_task_manager' # Default fallback URI
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000, connectTimeoutMS=20000, socketTimeoutMS=20000)
    # Test connection
    client.admin.command('ping')
    print("MongoDB connection: SUCCESS")
    db = client['web_task_manager'] # Use the correct database name
    problems_collection = db['problems']
    logs_collection = db['logs']
except Exception as e:
    print(f"MongoDB connection: FAILED - {e}")
    # Depending on the severity, you might want to exit or handle this differently
    db = None
    problems_collection = None
    logs_collection = None
    # sys.exit(1) # Uncomment to exit if DB connection is critical at startup
