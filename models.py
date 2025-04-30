from datetime import datetime, timezone
# Use absolute import based on project root being in PYTHONPATH
from config import logs_collection, problems_collection # Import problems_collection

# --- Logging ---

def add_log(action, username, problem_oj, problem_code, details=None):
    """Adds an entry to the logs collection."""
    if logs_collection is None:
        print("Error: Cannot add log, database connection not established.")
        return

    log_entry = {
        'timestamp': datetime.now(timezone.utc),
        'action': action,
        'username': username,
        'problem_oj': problem_oj,
        'problem_code': problem_code,
        'details': details or {}
    }
    try:
        logs_collection.insert_one(log_entry)
        print(f"Log added: {action} by {username} for {problem_oj}/{problem_code}")
    except Exception as e:
        print(f"Error adding log: {e}")

# --- Problem Operations ---

def get_all_problems():
    """Fetches all problems from the database, excluding the _id field."""
    if problems_collection is None:
        print("Error: Cannot get problems, database connection not available.")
        return None # Indicate error or unavailable connection
    try:
        return list(problems_collection.find({}, {'_id': 0}))
    except Exception as e:
        print(f"Error fetching all problems from DB: {e}")
        return None # Indicate error

def find_problem_by_oj_code(oj, code):
    """Finds a single problem by OJ and code."""
    if problems_collection is None: return None
    try:
        return problems_collection.find_one({'oj': oj, 'code': code}) # Keep _id for internal use if needed
    except Exception as e:
        print(f"Error finding problem {oj}/{code}: {e}")
        return None

def check_problem_exists(oj, code, exclude_id=None):
    """Checks if a problem with the given OJ and code exists, optionally excluding one _id."""
    if problems_collection is None: return False # Assume doesn't exist if DB unavailable
    query = {'oj': oj, 'code': code}
    if exclude_id:
        query['_id'] = {'$ne': exclude_id}
    try:
        return problems_collection.count_documents(query) > 0
    except Exception as e:
        print(f"Error checking if problem {oj}/{code} exists: {e}")
        return False # Safer to assume false on error? Or raise?

def add_new_problem(problem_data):
    """Adds a new problem document to the collection."""
    if problems_collection is None: return None
    try:
        # Basic validation could happen here too, or be left to the route
        insert_result = problems_collection.insert_one(problem_data)
        return insert_result.inserted_id
    except Exception as e:
        print(f"Error inserting new problem: {e}")
        return None

def delete_problem_by_oj_code(oj, code):
    """Deletes a problem by OJ and code."""
    if problems_collection is None: return None
    try:
        result = problems_collection.delete_one({'oj': oj, 'code': code})
        return result.deleted_count
    except Exception as e:
        print(f"Error deleting problem {oj}/{code}: {e}")
        return None

def update_problem_document(original_oj, original_code, update_data):
    """Updates a problem document identified by original OJ and code."""
    if problems_collection is None: return None, None # Indicate error
    try:
        result = problems_collection.update_one(
            {'oj': original_oj, 'code': original_code},
            {'$set': update_data}
        )
        # Return matched_count and modified_count for the route to interpret
        return result.matched_count, result.modified_count
    except Exception as e:
        print(f"Error updating problem {original_oj}/{original_code}: {e}")
        return None, None # Indicate error
