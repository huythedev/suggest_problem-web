import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables first to potentially set MONGO_URI before config is imported
load_dotenv()

# Now import config which relies on MONGO_URI
from modules.config import db

def clear_logs_collection():
    """Connects to MongoDB and clears the 'logs' collection after confirmation."""
    # MONGO_URI is now handled within config.py, we just need the db object

    if db is None:
        print("Error: Database connection (db object) is None. Cannot clear logs.")
        return

    try:
        # db object is already connected via config.py
        print(f"Using database: {db.name}")
        logs_collection = db['logs']    # Access the logs collection

        count = logs_collection.count_documents({})
        if count == 0:
            print("Logs collection is already empty.")
            return

        print(f"\nWARNING: This script will permanently delete {count} log entries.")
        confirm = input("Are you sure you want to proceed? (yes/no): ").lower().strip()

        if confirm == 'yes':
            print("Deleting logs...")
            result = logs_collection.delete_many({})
            print(f"Successfully deleted {result.deleted_count} log entries.")
        else:
            print("Operation cancelled.")

    except Exception as e:
        print(f"An error occurred: {e}")
    # No need to manually close client here, as config.py handles the connection

if __name__ == "__main__":
    clear_logs_collection()
