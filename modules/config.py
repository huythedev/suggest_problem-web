import os
from dotenv import load_dotenv
from pymongo import MongoClient
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
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'default-fallback-secret-key-if-not-set')
if SECRET_KEY == 'default-fallback-secret-key-if-not-set':
    warnings.warn("FLASK_SECRET_KEY not set in environment. Using insecure default.")

# --- Allowed OJs ---
ALLOWED_OJS = ["Codeforces", "AtCoder", "UVA", "SPOJ", "Other"] # Add more as needed

# --- Admin Credentials ---
# Initialize as an empty dictionary FIRST
ADMIN_CREDENTIALS = {}
# Load credentials from environment variables (handle multiple admins)
admin_user = os.getenv('ADMIN_USERNAME')
admin_pass = os.getenv('ADMIN_PASSWORD')

if admin_user and admin_pass:
    ADMIN_CREDENTIALS[admin_user] = admin_pass
    print(f"Loaded admin user '{admin_user}' from environment.") # Log only the last one found
else:
    warnings.warn("ADMIN_USERNAME or ADMIN_PASSWORD not found in environment. Login might not work.")

# Ensure ADMIN_CREDENTIALS is always defined (even if empty)
if not ADMIN_CREDENTIALS:
    warnings.warn("No admin credentials loaded. Login will not be possible.")

# --- MongoDB Connection ---
MONGO_URI = os.getenv('MONGO_URI')
db = None # Initialize db to None

# --- Debugging: Print the URI being used ---
print(f"DEBUG: Attempting MongoDB connection with URI: {MONGO_URI}")
# --- End Debugging ---

if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI)
        # Check server connection
        client.admin.command('ismaster')
        print("MongoDB server connection: SUCCESS")
        # Try to get the default database
        try:
            db = client.get_default_database() # Get the default DB from the URI
            print(f"MongoDB default database connection: SUCCESS")
        except Exception as db_err:
            # Make the error message even more explicit about checking the URI value
            print(f"MongoDB connection: FAILED - Error getting default database: {db_err}")
            print(">>> CRITICAL: Ensure your MONGO_URI in the .env file includes the database name <<<")
            print(">>> Example: mongodb+srv://...mongodb.net/YourActualDbName?... <<<")
            db = None # Ensure db is None if getting default DB fails
    except Exception as e:
        print(f"MongoDB server connection: FAILED - {e}")
        db = None # Ensure db is None if connection fails
else:
    print("MongoDB connection: SKIPPED - MONGO_URI not set in environment.")
