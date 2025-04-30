import os
from pymongo import MongoClient
from dotenv import load_dotenv

def clear_logs_collection():
    """Connects to MongoDB and clears the 'logs' collection after confirmation."""
    load_dotenv() # Load environment variables from .env

    mongo_uri = os.environ.get('MONGO_URI')
    if not mongo_uri:
        print("Error: MONGO_URI not found in environment variables or .env file.")
        return

    try:
        print(f"Connecting to MongoDB at {mongo_uri.split('@')[-1]}...") # Hide credentials in print
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')
        print("MongoDB connection: SUCCESS")

        db = client['web_task_manager'] # Use the correct database name
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
    finally:
        if 'client' in locals() and client:
            client.close()
            print("MongoDB connection closed.")

if __name__ == "__main__":
    clear_logs_collection()
