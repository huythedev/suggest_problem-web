from flask import Blueprint, jsonify, request, render_template, session
# Use absolute imports
from config import ALLOWED_OJS, db # Keep ALLOWED_OJS, remove problems_collection
# Import model functions instead of collection directly
from models import (
    add_log,
    get_all_problems,
    find_problem_by_oj_code,
    check_problem_exists,
    add_new_problem,
    delete_problem_by_oj_code,
    update_problem_document
)
from auth import login_required
import requests # For fetching external URL
from bs4 import BeautifulSoup # For parsing HTML (needed for SPOJ search)
import json # For parsing JSON response
import time # For potential delays if needed

problem_bp = Blueprint('problem', __name__)

# --- Luogu Fetching Logic ---

# Helper function to make the actual request and parse difficulty from embedded JSON
def _fetch_luogu_json(luogu_pid):
    """Fetches Luogu HTML page, parses embedded JSON, and extracts difficulty."""
    url = f"https://www.luogu.com.cn/problem/{luogu_pid}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    try:
        print(f"Fetching Luogu HTML URL: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Response Status Code: {response.status_code}")
        content_type = response.headers.get('Content-Type', '')
        print(f"Response Content-Type: {content_type}")

        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Check if response is HTML before parsing with BeautifulSoup
        if 'text/html' in content_type:
            soup = BeautifulSoup(response.content, 'html.parser')
            script_tag = soup.find('script', id='lentille-context')

            if script_tag:
                try:
                    # Parse the JSON content of the script tag
                    script_data = json.loads(script_tag.string)
                    # Extract the difficulty from the correct path in this JSON structure
                    difficulty = script_data.get('data', {}).get('problem', {}).get('difficulty')

                    if difficulty is not None:
                        print(f"Found Luogu difficulty via embedded JSON ({luogu_pid}): {difficulty}")
                        return int(difficulty)
                    else:
                        # Check if problem exists but difficulty is missing/null in embedded JSON
                        problem_data = script_data.get('data', {}).get('problem')
                        if problem_data and 'pid' in problem_data:
                             print(f"Found Luogu problem ({luogu_pid}) in embedded JSON, but difficulty is missing or null.")
                             return 0 # Treat missing difficulty for existing problem as 0 (unrated)
                        else:
                             print(f"Difficulty key not found within embedded JSON structure for {luogu_pid}.")
                             return None # Structure unexpected

                except json.JSONDecodeError as e:
                    print(f"Error decoding embedded JSON from script tag for {luogu_pid}: {e}")
                    return None
                except (AttributeError, KeyError, TypeError, ValueError) as e:
                    print(f"Error processing embedded JSON data for {luogu_pid}: {e}")
                    return None
            else:
                print(f"Script tag with id='lentille-context' not found in HTML for {luogu_pid}.")
                return None
        else:
            # If not HTML, log it - shouldn't happen for the base URL usually
            print(f"Response was not HTML (Content-Type: {content_type}). Cannot parse for embedded JSON.")
            return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Luogu problem {luogu_pid} not found (404).")
        elif e.response.status_code in [403, 503]:
             print(f"HTTP error {e.response.status_code} fetching Luogu HTML for {luogu_pid}. Possible Cloudflare block/issue.")
        else:
            print(f"HTTP error {e.response.status_code} fetching Luogu HTML for {luogu_pid}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching Luogu HTML for {luogu_pid}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while fetching/processing HTML for {luogu_pid}: {e}")

    return None

# Helper function specifically for SPOJ search
def _find_spoj_luogu_code(spoj_code):
    """Searches Luogu for an SPOJ code and returns the corresponding SPxxx code."""
    search_url = f"https://www.luogu.com.cn/problem/list?keyword={spoj_code}&page=1"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        print(f"Searching Luogu for SPOJ code: {spoj_code} at {search_url}")
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the first link in the results list that points to an SP problem
        # This relies on Luogu's search result structure
        results_div = soup.find('div', class_='lg-container') # Adjust if class changes
        if results_div:
             # Look for links like <a href="/problem/SP...">...</a>
             sp_links = results_div.find_all('a', href=lambda href: href and href.startswith('/problem/SP'))
             for link in sp_links:
                 # Maybe check if the link text or surrounding text matches spoj_code?
                 # For now, let's take the first one found.
                 luogu_sp_code = link['href'].split('/')[-1]
                 if luogu_sp_code.startswith('SP'):
                     print(f"Found potential Luogu SP code: {luogu_sp_code}")
                     return luogu_sp_code
        print(f"No matching SPxxx link found in search results for {spoj_code}.")

    except requests.exceptions.RequestException as e:
        print(f"Error searching Luogu for SPOJ code {spoj_code}: {e}")
    except Exception as e:
        print(f"Error parsing SPOJ search results for {spoj_code}: {e}")

    return None


def fetch_luogu_difficulty(oj, code):
    """
    Fetches difficulty rating from Luogu.cn based on OJ and code.
    Tries fetching with raw code first for CF/AT/UVA, then with prefixed PID.
    Handles different OJ code formats and uses embedded JSON from HTML.
    """
    luogu_pid = None
    difficulty = None
    pids_tried = [] # Keep track of PIDs tried for logging

    print(f"\nAttempting to fetch Luogu difficulty for OJ: {oj}, Code: {code}")

    # --- Try raw code first for applicable OJs ---
    raw_code_ojs = ["Codeforces", "AtCoder", "UVA"]
    if oj in raw_code_ojs:
        print(f"Attempt 1: Trying raw code '{code}' directly.")
        pids_tried.append(code) # Log the raw code attempt
        difficulty = _fetch_luogu_json(code)
        if difficulty is not None:
            print(f"Successfully fetched difficulty using raw code '{code}'.")
            return difficulty
        else:
            print(f"Raw code '{code}' fetch failed or returned no difficulty.")

    # --- If raw code failed or OJ is SPOJ, proceed with specific logic ---
    print("Proceeding with OJ-specific PID construction.")

    if oj == "Codeforces":
        # Raw code failed, now try constructing CF{code}
        if not code.upper().startswith("CF"): # Avoid double prefix if raw code already had it
            luogu_pid = f"CF{code}"
            print(f"Attempt 2: Trying constructed PID '{luogu_pid}'.")
            pids_tried.append(luogu_pid)
            difficulty = _fetch_luogu_json(luogu_pid)
        else:
            # If raw code started with CF and failed, no need to try again
            print("Raw code already started with CF and failed, skipping second attempt.")
            luogu_pid = code # Keep for logging

    elif oj == "SPOJ":
        # SPOJ always requires search first
        luogu_sp_code = _find_spoj_luogu_code(code)
        if luogu_sp_code:
            luogu_pid = luogu_sp_code
            pids_tried.append(luogu_pid) # Log the found SP code
            difficulty = _fetch_luogu_json(luogu_pid)
        else:
            print(f"Could not find Luogu mapping for SPOJ code {code}.")

    elif oj == "AtCoder":
        # Raw code failed, now try constructing AT... PIDs
        parts = code.split('_')
        contest_part = parts[0].lower()
        task_part = parts[1] if len(parts) > 1 else ''

        # Format 1: AT<lowercase_contest><task>
        pid1 = f"AT{contest_part}{task_part}"
        # Avoid retrying if pid1 is same as raw code and already failed
        if pid1.lower() != code.lower():
            print(f"Attempt 2: Trying constructed PID '{pid1}'.")
            pids_tried.append(pid1)
            difficulty = _fetch_luogu_json(pid1)
        else:
            print(f"Constructed PID '{pid1}' is same as raw code, skipping.")

        if difficulty is None: # If first constructed format failed or was skipped
            print(f"Constructed AtCoder format ({pid1}) failed or was skipped, trying second format.")
            # Format 2: AT_<lowercase_contest>_<task>
            if '_' in code and task_part:
                 pid2 = f"AT_{contest_part}_{task_part}"
                 # Avoid retrying if pid2 is same as raw code and already failed
                 if pid2.lower() != code.lower():
                     print(f"Attempt 3: Trying constructed PID '{pid2}'.")
                     pids_tried.append(pid2)
                     difficulty = _fetch_luogu_json(pid2)
                     if difficulty is None:
                          print(f"Second constructed AtCoder format ({pid2}) also failed.")
                 else:
                     print(f"Constructed PID '{pid2}' is same as raw code, skipping.")
            else:
                 print("Original AtCoder code did not contain '_' or task part, skipping second format.")

        # Determine final luogu_pid for logging
        if difficulty is not None:
             luogu_pid = pid2 if pid2 in pids_tried and _fetch_luogu_json(pid2) is not None else pid1 # Prefer last successful one tried
        elif pid2 in pids_tried:
             luogu_pid = pid2 # Log last attempted if both failed
        elif pid1 in pids_tried:
             luogu_pid = pid1
        else:
             luogu_pid = code # Fallback to raw code if no constructed PIDs were tried

    elif oj == "UVA":
        # Raw code failed, now try constructing UVA{code}
        if not code.upper().startswith("UVA"): # Avoid double prefix
            luogu_pid = f"UVA{code}"
            print(f"Attempt 2: Trying constructed PID '{luogu_pid}'.")
            pids_tried.append(luogu_pid)
            difficulty = _fetch_luogu_json(luogu_pid)
        else:
            print("Raw code already started with UVA and failed, skipping second attempt.")
            luogu_pid = code # Keep for logging

    else:
        # This case should only be hit if OJ was not in raw_code_ojs initially
        print(f"OJ '{oj}' not currently supported for Luogu difficulty fetching.")
        return None

    # --- Final Logging ---
    if difficulty is not None:
        print(f"Successfully fetched difficulty for {oj} {code} (Luogu PID: {luogu_pid}): {difficulty}")
    else:
        # Log all unique PIDs that were tried
        unique_pids = sorted(list(set(pids_tried)))
        print(f"Failed to fetch difficulty for {oj} {code} (Tried Luogu PID(s): {', '.join(unique_pids)})")

    return difficulty


@problem_bp.route('/fetch-luogu-details', methods=['GET'])
@login_required # Or remove if public fetching is desired
def fetch_luogu_details_route():
    oj = request.args.get('oj')
    code = request.args.get('code')

    if not oj or not code:
        return jsonify({"error": "Missing 'oj' or 'code' parameter"}), 400

    difficulty = fetch_luogu_difficulty(oj, code)

    if difficulty is not None:
        return jsonify({"rating": difficulty})
    else:
        return jsonify({"rating": None})


# --- Existing Routes ---
@problem_bp.route('/')
def index():
    # Pass the OJ list and a flag to the template
    return render_template('index.html', is_public=True, allowed_ojs=ALLOWED_OJS)

@problem_bp.route('/admin')
@login_required
def admin_dashboard():
    # Pass the OJ list to the admin template
    return render_template('admin.html', allowed_ojs=ALLOWED_OJS)

# --- API Endpoints ---

@problem_bp.route('/problems', methods=['GET'])
def get_problems():
    problems_data = get_all_problems()
    if problems_data is None:
        # Handle cases where DB connection failed or query error occurred
        return jsonify({"error": "Failed to retrieve problems from database."}), 500
    return jsonify(problems_data)


@problem_bp.route('/problems', methods=['POST'])
@login_required
def add_problem():
    data = request.json
    required = ['oj', 'code', 'title', 'rating']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields (oj, code, title, rating)'}), 400

    if data.get('oj') not in ALLOWED_OJS:
        return jsonify({'error': f"Invalid OJ specified. Allowed: {', '.join(ALLOWED_OJS)}"}), 400

    data.setdefault('contest', 'No')

    # Use model function to check existence
    if check_problem_exists(data['oj'], data['code']):
        return jsonify({'error': 'Problem with this OJ and Code already exists'}), 409

    # Use model function to add
    inserted_id = add_new_problem(data)

    if inserted_id:
        add_log(
            action='add',
            username=session.get('username', 'unknown'),
            problem_oj=data.get('oj'),
            problem_code=data.get('code'),
            details={'added_data': data} # Log original data before popping _id
        )
        # Find the newly added problem to return it (optional, but good practice)
        # Or just return the input data minus _id if find isn't needed
        new_problem = find_problem_by_oj_code(data['oj'], data['code'])
        if new_problem:
             new_problem.pop('_id', None) # Remove internal ID before returning
             return jsonify(new_problem), 201
        else:
             # Fallback if find fails immediately after insert (unlikely)
             data.pop('_id', None) # Ensure _id from insert_one isn't returned
             return jsonify(data), 201 # Return input data as fallback
    else:
        # Check if db connection was the issue or insert failed
        if db is None:
             return jsonify({"error": "Database connection not available"}), 503
        return jsonify({'error': 'Failed to add problem to database'}), 500


@problem_bp.route('/problems', methods=['DELETE'])
@login_required
def delete_problem():
    code = request.args.get('code')
    oj = request.args.get('oj')
    if not code or not oj:
        return jsonify({'error': 'Missing code or oj'}), 400

    # Optional: Check if problem exists before attempting delete using find_problem_by_oj_code
    # problem_to_delete = find_problem_by_oj_code(oj, code)
    # if not problem_to_delete:
    #     return jsonify({'error': 'Problem not found'}), 404

    # Use model function to delete
    deleted_count = delete_problem_by_oj_code(oj, code)

    if deleted_count is None:
        if db is None:
             return jsonify({"error": "Database connection not available"}), 503
        return jsonify({'error': 'An error occurred during deletion'}), 500
    elif deleted_count == 1:
        add_log(
            action='delete',
            username=session.get('username', 'unknown'),
            problem_oj=oj,
            problem_code=code
        )
        return jsonify({'message': 'Problem deleted'}), 200
    else: # deleted_count == 0
        return jsonify({'error': 'Problem not found or already deleted'}), 404


@problem_bp.route('/problems', methods=['PUT'])
@login_required
def update_problem():
    original_oj = request.args.get('oj')
    original_code = request.args.get('code')
    if not original_oj or not original_code:
        return jsonify({'error': 'Missing original oj or code in query parameters'}), 400

    data = request.json
    required_core = ['oj', 'code', 'title', 'rating']
    if not all(k in data for k in required_core):
         return jsonify({'error': 'Missing core fields (oj, code, title, rating) in update data'}), 400

    if data.get('oj') not in ALLOWED_OJS:
        return jsonify({'error': f"Invalid OJ specified. Allowed: {', '.join(ALLOWED_OJS)}"}), 400

    data.setdefault('contest', 'No')

    # Use model function to find the original document to check existence and get _id
    current_doc = find_problem_by_oj_code(original_oj, original_code)
    if not current_doc:
         # Check if DB connection failed or just not found
         if db is None: return jsonify({"error": "Database connection not available"}), 503
         return jsonify({'error': 'Problem to update not found'}), 404

    # Use model function to check for conflicts if identifiers changed
    if (data['oj'] != original_oj or data['code'] != original_code):
        if check_problem_exists(data['oj'], data['code'], exclude_id=current_doc.get('_id')):
            return jsonify({'error': 'Another problem with the new OJ and Code already exists'}), 409

    # Prepare update data (can stay here or move to model if complex)
    update_data = {
        'oj': data['oj'],
        'code': data['code'],
        'title': data['title'],
        'rating': data['rating'],
        'contest': data['contest'],
        'tags': data.get('tags'),
        'custom': data.get('custom')
    }

    # Use model function to update
    matched_count, modified_count = update_problem_document(original_oj, original_code, update_data)

    if matched_count is None: # Indicates DB error from model function
         if db is None: return jsonify({"error": "Database connection not available"}), 503
         return jsonify({'error': 'An error occurred during update'}), 500
    elif matched_count == 1:
        add_log(
            action='update',
            username=session.get('username', 'unknown'),
            problem_oj=original_oj, # Log original identifiers
            problem_code=original_code,
            details={'updated_to': data} # Log the intended new data
        )
        # Fetch the updated document using potentially new identifiers
        updated_doc_data = find_problem_by_oj_code(data['oj'], data['code'])
        if updated_doc_data:
            updated_doc_data.pop('_id', None)
            return jsonify(updated_doc_data), 200
        else:
             # Should be rare if update succeeded
             return jsonify({'message': 'Update successful, but could not retrieve updated document'}), 200
    else: # matched_count == 0
        # This case should have been caught by the initial find_problem_by_oj_code
        return jsonify({'error': 'Problem not found during update operation (unexpected)'}), 404

