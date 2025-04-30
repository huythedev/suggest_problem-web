from flask import Blueprint, jsonify, request, render_template, session
# Use absolute imports with modules. prefix
from modules.config import ALLOWED_OJS, db
# Import model functions with modules. prefix
from modules.models import (
    add_log,
    get_all_problems,
    find_problem_by_oj_code,
    check_problem_exists,
    add_new_problem,
    delete_problem_by_oj_code,
    update_problem_document
)
from modules.auth import login_required
import requests
from bs4 import BeautifulSoup
import json
import time
import re

problem_bp = Blueprint('problem', __name__)

# --- Luogu Fetching Logic ---

def _fetch_with_retries(url, headers, retries=2, timeout=10):
    """Helper to fetch URL with basic retry logic."""
    for i in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            # Basic check for login pages (can be expanded)
            if "login" in response.text.lower() and "logout" not in response.text.lower():
                 print(f"Warning: Possible login page detected at {url}")
            return response
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error fetching {url} (Attempt {i+1}/{retries+1}): {e}")
            if e.response.status_code in [404, 403]: # Don't retry on 404/403
                return None
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching {url} (Attempt {i+1}/{retries+1}): {e}")
        except Exception as e:
             print(f"Unexpected error fetching {url} (Attempt {i+1}/{retries+1}): {e}")
        if i < retries:
            time.sleep(1) # Wait a bit before retrying
    return None

# Helper function to make the actual request and parse data from embedded JSON
def _fetch_luogu_json(luogu_pid):
    """Fetches Luogu HTML page, parses embedded JSON, and extracts difficulty and title."""
    url = f"https://www.luogu.com.cn/problem/{luogu_pid}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    details = {"rating": None, "title": None} # Initialize details dict

    try:
        print(f"Fetching Luogu HTML URL: {url}")
        # Use the retry helper
        response = _fetch_with_retries(url, headers)
        if response is None:
             print(f"Failed to fetch Luogu URL {url} after retries.")
             return details # Return default details

        content_type = response.headers.get('Content-Type', '')
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Content-Type: {content_type}")

        # Check if response is HTML before parsing with BeautifulSoup
        if 'text/html' in content_type:
            soup = BeautifulSoup(response.content, 'html.parser')
            script_tag = soup.find('script', id='lentille-context')

            if script_tag:
                try:
                    # Parse the JSON content of the script tag
                    script_data = json.loads(script_tag.string)
                    problem_data = script_data.get('data', {}).get('problem', {})

                    if problem_data:
                        # Extract difficulty
                        difficulty = problem_data.get('difficulty')
                        if difficulty is not None:
                            details["rating"] = int(difficulty)
                            print(f"Found Luogu difficulty via embedded JSON ({luogu_pid}): {details['rating']}")
                        elif 'pid' in problem_data: # Check if problem exists but difficulty is missing
                            details["rating"] = 0 # Treat missing difficulty for existing problem as 0
                            print(f"Found Luogu problem ({luogu_pid}) in embedded JSON, but difficulty is missing or null. Setting rating to 0.")
                        else:
                             print(f"Difficulty key not found or problem data incomplete for {luogu_pid}.")

                        # Extract title
                        title = problem_data.get('title')
                        if title:
                            details["title"] = title.strip()
                            print(f"Found Luogu title via embedded JSON ({luogu_pid}): {details['title']}")
                        else:
                            print(f"Title key not found within embedded JSON structure for {luogu_pid}.")

                    else:
                         print(f"Problem data block not found within embedded JSON structure for {luogu_pid}.")

                except json.JSONDecodeError as e:
                    print(f"Error decoding embedded JSON from script tag for {luogu_pid}: {e}")
                except (AttributeError, KeyError, TypeError, ValueError) as e:
                    print(f"Error processing embedded JSON data for {luogu_pid}: {e}")
            else:
                print(f"Script tag with id='lentille-context' not found in HTML for {luogu_pid}.")
        else:
            print(f"Response was not HTML (Content-Type: {content_type}). Cannot parse for embedded JSON.")

    # Catch errors specifically from _fetch_with_retries if needed, or general exceptions
    except Exception as e:
        print(f"An unexpected error occurred while fetching/processing HTML for {luogu_pid}: {e}")

    return details

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

        results_div = soup.find('div', class_='lg-container') # Adjust if class changes
        if results_div:
             sp_links = results_div.find_all('a', href=lambda href: href and href.startswith('/problem/SP'))
             for link in sp_links:
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


def fetch_luogu_details(oj, code):
    """
    Fetches difficulty rating AND title from Luogu.cn based on OJ and code.
    Prioritizes using Luogu's embedded JSON.
    Returns a dictionary {"rating": value, "title": value}.
    """
    luogu_pid = None
    details = {"rating": None, "title": None} # Default return value
    pids_tried = [] # Keep track of PIDs tried for logging

    print(f"\nAttempting to fetch Luogu details for OJ: {oj}, Code: {code}")

    raw_code_ojs = ["Codeforces", "AtCoder", "UVA"]
    if oj in raw_code_ojs:
        print(f"Attempt 1: Trying raw code '{code}' directly on Luogu.")
        pids_tried.append(code)
        details = _fetch_luogu_json(code)
        if details["rating"] is not None or details["title"] is not None:
            print(f"Successfully fetched details using raw code '{code}'. Rating: {details['rating']}, Title: {details['title']}")
            return details
        else:
            print(f"Raw code '{code}' fetch failed or returned no details.")

    print("Proceeding with OJ-specific PID construction for Luogu.")

    if oj == "Codeforces":
        if not code.upper().startswith("CF"):
            luogu_pid = f"CF{code}"
            print(f"Attempt 2: Trying constructed PID '{luogu_pid}'.")
            pids_tried.append(luogu_pid)
            details = _fetch_luogu_json(luogu_pid)
        else:
            print("Raw code already started with CF and failed, skipping second attempt.")
            luogu_pid = code

    elif oj == "SPOJ":
        luogu_sp_code = _find_spoj_luogu_code(code)
        if luogu_sp_code:
            luogu_pid = luogu_sp_code
            pids_tried.append(luogu_pid)
            details = _fetch_luogu_json(luogu_pid)
        else:
            print(f"Could not find Luogu mapping for SPOJ code {code}.")

    elif oj == "AtCoder":
        parts = code.split('_')
        contest_part = parts[0].lower()
        task_part = parts[1] if len(parts) > 1 else ''
        pid1 = f"AT{contest_part}{task_part}"
        pid2 = f"AT_{contest_part}_{task_part}" if '_' in code and task_part else None

        if pid1.lower() != code.lower():
            print(f"Attempt 2: Trying constructed PID '{pid1}'.")
            pids_tried.append(pid1)
            details = _fetch_luogu_json(pid1)
        else:
            print(f"Constructed PID '{pid1}' is same as raw code, skipping.")

        if (details["rating"] is None and details["title"] is None) and pid2 and pid2.lower() != code.lower():
             print(f"Attempt 3: Trying constructed PID '{pid2}'.")
             pids_tried.append(pid2)
             details = _fetch_luogu_json(pid2)
             if details["rating"] is None and details["title"] is None:
                  print(f"Second constructed AtCoder format ({pid2}) also failed.")
        elif pid2 and pid2.lower() == code.lower():
             print(f"Constructed PID '{pid2}' is same as raw code, skipping.")
        elif not pid2:
             print("Original AtCoder code did not contain '_' or task part, skipping second format.")

        if details["rating"] is not None or details["title"] is not None:
             if pid2 in pids_tried:
                 temp_details = _fetch_luogu_json(pid2)
                 if temp_details["rating"] is not None or temp_details["title"] is not None:
                     luogu_pid = pid2
                 elif pid1 in pids_tried:
                      luogu_pid = pid1
             elif pid1 in pids_tried:
                  luogu_pid = pid1
        elif pid2 in pids_tried: luogu_pid = pid2
        elif pid1 in pids_tried: luogu_pid = pid1
        else: luogu_pid = code

    elif oj == "UVA":
        if not code.upper().startswith("UVA"):
            luogu_pid = f"UVA{code}"
            print(f"Attempt 2: Trying constructed PID '{luogu_pid}'.")
            pids_tried.append(luogu_pid)
            details = _fetch_luogu_json(luogu_pid)
        else:
            print("Raw code already started with UVA and failed, skipping second attempt.")
            luogu_pid = code

    else:
        print(f"OJ '{oj}' not currently supported for Luogu detail fetching.")
        return details

    if details["rating"] is not None or details["title"] is not None:
        print(f"Successfully fetched details for {oj} {code} (Luogu PID: {luogu_pid}): Rating={details['rating']}, Title='{details['title']}'")
    else:
        unique_pids = sorted(list(set(pids_tried)))
        print(f"Failed to fetch details for {oj} {code} (Tried Luogu PID(s): {', '.join(unique_pids)})")

    return details


@problem_bp.route('/fetch-luogu-details', methods=['GET'])
@login_required
def fetch_luogu_details_route():
    oj = request.args.get('oj')
    code = request.args.get('code')

    if not oj or not code:
        return jsonify({"error": "Missing 'oj' or 'code' parameter"}), 400

    details = fetch_luogu_details(oj, code)

    return jsonify(details)


# --- UVA ID Fetching Logic ---
@problem_bp.route('/fetch-uva-id', methods=['GET'])
@login_required
def fetch_uva_id_route():
    uva_url = request.args.get('url')
    if not uva_url or 'onlinejudge.org' not in uva_url:
        return jsonify({"error": "Missing or invalid UVA URL parameter", "uva_id": None, "title": None}), 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    extracted_id = None
    extracted_title = None
    try:
        print(f"Fetching UVA page for ID & Title extraction: {uva_url}")
        response = _fetch_with_retries(uva_url, headers)
        if response is None:
             print(f"Failed to fetch UVA URL {uva_url} after retries.")
             return jsonify({"error": "Failed to fetch UVA URL", "uva_id": None, "title": None}), 502

        content_type = response.headers.get('Content-Type', '')
        page_content = response.text

        title_tag = BeautifulSoup(page_content, 'html.parser').find('title')
        title_text = title_tag.get_text().lower() if title_tag else ""
        if "login" in title_text or "you need to login" in page_content.lower() or "you are not authorised" in page_content.lower():
             print(f"UVA page requires login or is login page: {uva_url}")
             return jsonify({"error": "UVA page requires login to view", "uva_id": None, "title": None}), 403

        if 'text/html' in content_type:
            soup = BeautifulSoup(response.content, 'html.parser')
            h3_tags = soup.find_all('h3')
            found_problem_h3 = False
            for h3_tag in h3_tags:
                h3_text = h3_tag.get_text().strip()
                if "login" in h3_text.lower():
                    print(f"Skipping h3 tag containing 'login': {h3_text}")
                    continue

                match = re.match(r'\s*(\d+)\s*-\s*(.*)', h3_text)
                if match:
                    extracted_id = match.group(1)
                    extracted_title = match.group(2).strip()
                    print(f"Extracted UVA ID: {extracted_id}, Title: {extracted_title}")
                    found_problem_h3 = True
                    break
                else:
                    print(f"H3 tag found but did not match ID-Title pattern: {h3_text}")

            if not found_problem_h3:
                print("Could not find a suitable H3 tag containing the problem ID and Title.")
        else:
            print(f"Response from UVA URL was not HTML: {content_type}")

    except requests.exceptions.HTTPError as e:
         print(f"HTTP error fetching UVA URL {uva_url}: {e}")
         status_code = e.response.status_code
         error_message = f"Failed to fetch UVA URL (HTTP {status_code})"
         if status_code == 404: error_message = "UVA problem not found (404)"
         elif status_code == 403: error_message = "Access forbidden to UVA URL (403)"
         return jsonify({"error": error_message, "uva_id": None, "title": None}), status_code if status_code in [403, 404] else 502
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching UVA URL {uva_url}: {e}")
        return jsonify({"error": f"Network error fetching UVA URL: {e}", "uva_id": None, "title": None}), 502
    except Exception as e:
        print(f"Error parsing UVA page {uva_url}: {e}")
        return jsonify({"error": f"Failed to parse UVA page: {e}", "uva_id": None, "title": None}), 500

    return jsonify({"uva_id": extracted_id, "title": extracted_title})


# --- Existing Routes ---
@problem_bp.route('/')
def index():
    return render_template('index.html', is_public=True, allowed_ojs=ALLOWED_OJS)

@problem_bp.route('/admin')
@login_required
def admin_dashboard():
    return render_template('admin.html', allowed_ojs=ALLOWED_OJS)

# --- API Endpoints ---

@problem_bp.route('/problems', methods=['GET'])
def get_problems():
    problems_data = get_all_problems()
    if problems_data is None:
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

    if check_problem_exists(data['oj'], data['code']):
        return jsonify({'error': 'Problem with this OJ and Code already exists'}), 409

    inserted_id = add_new_problem(data)

    if inserted_id:
        add_log(
            action='add',
            username=session.get('username', 'unknown'),
            problem_oj=data.get('oj'),
            problem_code=data.get('code'),
            details={'added_data': data}
        )
        new_problem = find_problem_by_oj_code(data['oj'], data['code'])
        if new_problem:
             new_problem.pop('_id', None)
             return jsonify(new_problem), 201
        else:
             data.pop('_id', None)
             return jsonify(data), 201
    else:
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
    else:
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

    current_doc = find_problem_by_oj_code(original_oj, original_code)
    if not current_doc:
         if db is None: return jsonify({"error": "Database connection not available"}), 503
         return jsonify({'error': 'Problem to update not found'}), 404

    if (data['oj'] != original_oj or data['code'] != original_code):
        if check_problem_exists(data['oj'], data['code'], exclude_id=current_doc.get('_id')):
            return jsonify({'error': 'Another problem with the new OJ and Code already exists'}), 409

    update_data = {
        'oj': data['oj'],
        'code': data['code'],
        'title': data['title'],
        'rating': data['rating'],
        'contest': data['contest'],
        'tags': data.get('tags'),
        'custom': data.get('custom')
    }

    matched_count, modified_count = update_problem_document(original_oj, original_code, update_data)

    if matched_count is None:
         if db is None: return jsonify({"error": "Database connection not available"}), 503
         return jsonify({'error': 'An error occurred during update'}), 500
    elif matched_count == 1:
        add_log(
            action='update',
            username=session.get('username', 'unknown'),
            problem_oj=original_oj,
            problem_code=original_code,
            details={'updated_to': data}
        )
        updated_doc_data = find_problem_by_oj_code(data['oj'], data['code'])
        if updated_doc_data:
            updated_doc_data.pop('_id', None)
            return jsonify(updated_doc_data), 200
        else:
             return jsonify({'message': 'Update successful, but could not retrieve updated document'}), 200
    else:
        return jsonify({'error': 'Problem not found during update operation (unexpected)'}), 404

