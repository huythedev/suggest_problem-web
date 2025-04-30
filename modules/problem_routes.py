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
# Import the tag map from the new file
from modules.luogu_tag_map import LUOGU_TAG_MAP
import requests
from bs4 import BeautifulSoup
import json
import time
import re

problem_bp = Blueprint('problem', __name__)

def _map_luogu_tags(numeric_tags):
    """Maps Luogu numeric tag IDs to names using LUOGU_TAG_MAP."""
    return [LUOGU_TAG_MAP.get(tag_id, f"UnknownTag({tag_id})") for tag_id in numeric_tags]

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
    """Fetches Luogu HTML page, parses embedded JSON, and extracts difficulty, title, and tags."""
    url = f"https://www.luogu.com.cn/problem/{luogu_pid}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    # Initialize details dict with tags as an empty list and custom as None
    details = {"rating": None, "title": None, "tags": [], "custom": None}

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

                        # Extract tags (numeric IDs)
                        tags = problem_data.get('tags')
                        if isinstance(tags, list): # Check if tags is a list
                            details["tags"] = [str(tag) for tag in tags if isinstance(tag, int)] # Store as list of strings
                            print(f"Found Luogu tags via embedded JSON ({luogu_pid}): {details['tags']}")
                        else:
                            print(f"Tags key not found or not a list within embedded JSON structure for {luogu_pid}.")

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


# --- Codeforces Scraping Logic (Revised) ---
def _scrape_codeforces_details(code):
    """
    Attempts to scrape title, tag names, and *rating directly from Codeforces.
    Puts *rating into 'rating' field, tag names into 'tags'. 'custom' is None.
    Returns details dict or None if scraping fails significantly.
    """
    # Initialize details with custom=None
    details = {"rating": None, "title": None, "tags": [], "custom": None}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    urls_to_try = []
    match = re.match(r"(\d+)([A-Z]\d*)", code, re.IGNORECASE)
    if match:
        contest_id, problem_index = match.groups()
        urls_to_try = [
            f"https://codeforces.com/problemset/problem/{contest_id}/{problem_index}",
            f"https://codeforces.com/contest/{contest_id}/problem/{problem_index}"
        ]
    else:
        print(f"Codeforces code format not recognized for scraping: {code}")
        return None

    response = None
    successful_url = None
    for url in urls_to_try:
        print(f"Attempting to scrape Codeforces URL: {url}")
        response = _fetch_with_retries(url, headers)
        if response:
            successful_url = url
            break
        else:
            print(f"Scraping failed for URL: {url}")

    if not response:
        print(f"Failed to fetch Codeforces page for {code} (tried: {urls_to_try}). Scraping failed.")
        return None

    try:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract Title (remains the same)
        title_div = soup.find('div', class_='title')
        if title_div:
            details["title"] = re.sub(r"^[A-Z]\d*\.\s*", "", title_div.get_text(strip=True))
            # Use a temporary variable before the f-string
            scraped_title = details['title']
            print(f"Scraped CF Title: {scraped_title}") # Modified line
        else:
            print(f"Could not find title div for CF {code}")

        # Extract Tags and Rating (into 'rating' field)
        tags_div = soup.find('div', class_='tags')
        scraped_tags = []
        if tags_div:
            tag_boxes = tags_div.find_all('span', class_='tag-box')
            for tag_span in tag_boxes:
                tag_text = tag_span.get_text(strip=True)
                if tag_text.startswith('*'):
                    try:
                        rating_value = int(tag_text[1:])
                        details["rating"] = rating_value
                        print(f"Scraped CF Rating into Rating field: {details['rating']}")
                    except ValueError:
                        print(f"Could not parse rating from CF tag: {tag_text}")
                        scraped_tags.append(tag_text)
                else:
                    scraped_tags.append(tag_text)
            details["tags"] = scraped_tags
            print(f"Scraped CF Tags (names): {details['tags']}")
        else:
            print(f"Could not find tags div for CF {code}")

        if details["title"] or details["rating"] is not None:
            return details
        else:
            print(f"Scraping CF page {successful_url} yielded no title or rating.")
            return None

    except Exception as e:
        print(f"Error parsing Codeforces page {successful_url}: {e}")
        return None


# --- AtCoder Score Scraping Logic (Revised) ---
def _scrape_atcoder_score(code):
    """
    Attempts to scrape score (points) directly from AtCoder problem page.
    Looks for <p> containing 'Score :' or '配点 :', then extracts from <var>.
    Returns score as a string or None if not found/failed.
    """
    score = None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = None
    parts = code.split('_')
    if len(parts) >= 1:
        contest_id_guess = parts[0]
        # Updated regex to better match common AtCoder contest IDs
        if re.match(r"^(abc|arc|agc|ahc|typical90|dp|tdpc|practice)\d*$", contest_id_guess, re.IGNORECASE):
             url = f"https://atcoder.jp/contests/{contest_id_guess}/tasks/{code}"
        else:
             print(f"Cannot reliably determine AtCoder contest URL from code: {code}")
             return None
    else:
        print(f"AtCoder code format not recognized for scraping: {code}")
        return None

    print(f"Attempting to scrape AtCoder URL for score: {url}")
    response = _fetch_with_retries(url, headers)

    if not response:
        print(f"Failed to fetch AtCoder page for score scraping: {url}")
        return None

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        # Find the task statement div first for better targeting
        task_statement = soup.find('div', id='task-statement')
        if not task_statement:
            print(f"Could not find task statement div for AtCoder {code}")
            return None # Cannot proceed without the main content area

        # Method 1: Find <p> containing "Score :" or "配点 :", then find <var> inside
        score_p_tag = None
        for p_tag in task_statement.find_all('p'):
            p_text = p_tag.get_text()
            if "Score :" in p_text or "配点 :" in p_text:
                score_p_tag = p_tag
                break

        if score_p_tag:
            var_tag = score_p_tag.find('var')
            if var_tag:
                score_text = var_tag.get_text(strip=True)
                if score_text.isdigit():
                    score = score_text
                    print(f"Scraped AtCoder Score (Method 1: p > var): {score}")

        # Method 2 (Fallback): Regex on the whole task statement text (less reliable)
        if not score:
            score_pattern = re.compile(r"(?:Score|配点)\s*:\s*(\d+)\s*(?:points|点)", re.IGNORECASE)
            match = score_pattern.search(task_statement.get_text())
            if match:
                score = match.group(1)
                print(f"Scraped AtCoder Score (Method 2: Regex Fallback): {score}")

        # Method 3 (Fallback): Find any <var> whose parent mentions score (original fallback)
        if not score:
            var_tag = task_statement.find('var')
            if var_tag and var_tag.parent and ("score" in var_tag.parent.get_text(strip=True).lower() or "配点" in var_tag.parent.get_text(strip=True)):
                 score_text = var_tag.get_text(strip=True)
                 if score_text.isdigit():
                      score = score_text
                      print(f"Scraped AtCoder Score (Method 3: Parent Fallback): {score}")

        if not score:
            print(f"Could not find score pattern/structure on AtCoder page for {code}")

    except Exception as e:
        print(f"Error parsing AtCoder page {url} for score: {e}")

    return score


# --- Combined Fetching Logic ---

def fetch_luogu_details(oj, code):
    """
    Fetches difficulty rating, title, AND tags from Luogu.cn based on OJ and code.
    Constructs appropriate Luogu PIDs before fetching.
    Returns a dictionary {"rating": value, "title": value, "tags": [...], "custom": None}.
    """
    luogu_pid = None
    details = {"rating": None, "title": None, "tags": [], "custom": None}
    pids_tried = []

    print(f"\nAttempting to fetch Luogu details for OJ: {oj}, Code: {code}")

    # If the OJ is Luogu, the code IS the PID. Also try raw code for CF/AC/UVA first.
    raw_code_ojs = ["Codeforces", "AtCoder", "UVA", "Luogu"]
    if oj in raw_code_ojs:
        print(f"Attempt 1 (Luogu): Trying raw code '{code}' directly.")
        pids_tried.append(code)
        details = _fetch_luogu_json(code)
        if details["rating"] is not None or details["title"] is not None or details["tags"]:
            print(f"Successfully fetched Luogu details using raw code '{code}'. Rating: {details['rating']}, Title: {details['title']}, Tags: {details['tags']}")
            # If the OJ was Luogu and we succeeded, we are done.
            if oj == "Luogu":
                return details
        else:
            print(f"Raw code '{code}' Luogu fetch failed or returned no details.")
            # If the OJ was Luogu and raw code failed, we are done for Luogu.
            if oj == "Luogu":
                 print(f"Failed to fetch Luogu details for Luogu problem {code}.")
                 return details # Return empty details

    # If we are here, it means either:
    # 1. OJ was CF/AC/UVA and raw code failed, OR
    # 2. OJ was SPOJ (which doesn't try raw code first)
    # Proceed with OJ-specific PID construction only if not Luogu OJ.
    if oj != "Luogu":
        print("Proceeding with OJ-specific PID construction for Luogu.")

        if oj == "Codeforces":
            # Example: try constructed PID for Codeforces
            if not code.upper().startswith("CF"):
                luogu_pid = f"CF{code}"
                print(f"Attempt 2 (Luogu): Trying constructed PID '{luogu_pid}'.")
                pids_tried.append(luogu_pid)
                if details["rating"] is None and details["title"] is None and not details["tags"]:
                    details = _fetch_luogu_json(luogu_pid)
        elif oj == "SPOJ":
            luogu_sp_code = _find_spoj_luogu_code(code)
            if luogu_sp_code:
                luogu_pid = luogu_sp_code
                print(f"Attempt 1 (Luogu): Trying mapped PID '{luogu_pid}'.")
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

            if pid1.lower() != code.lower() and (details["rating"] is None and details["title"] is None and not details["tags"]):
                print(f"Attempt 2 (Luogu): Trying constructed PID '{pid1}'.")
                pids_tried.append(pid1)
                details = _fetch_luogu_json(pid1)
            elif pid1.lower() == code.lower():
                print(f"Constructed PID '{pid1}' is same as raw code, skipping attempt 2.")

            if (details["rating"] is None and details["title"] is None and not details["tags"]) and pid2 and pid2.lower() != code.lower():
                print(f"Attempt 3 (Luogu): Trying constructed PID '{pid2}'.")
                pids_tried.append(pid2)
                details = _fetch_luogu_json(pid2)
                if details["rating"] is None and details["title"] is None and not details["tags"]:
                    print(f"Second constructed AtCoder format ({pid2}) also failed on Luogu.")
            elif pid2 and pid2.lower() == code.lower():
                print(f"Constructed PID '{pid2}' is same as raw code, skipping attempt 3.")
            elif not pid2:
                print("Original AtCoder code did not contain '_' or task part, skipping second format attempt.")

            if details["rating"] is not None or details["title"] is not None or details["tags"]:
                if pid2 in pids_tried:
                    luogu_pid = pid2
                elif pid1 in pids_tried:
                    luogu_pid = pid1
                else:
                    luogu_pid = code
            elif pid2 in pids_tried: luogu_pid = pid2
            elif pid1 in pids_tried: luogu_pid = pid1
            else: luogu_pid = code

        elif oj == "UVA":
            if not code.upper().startswith("UVA"):
                luogu_pid = f"UVA{code}"
                print(f"Attempt 2 (Luogu): Trying constructed PID '{luogu_pid}'.")
                pids_tried.append(luogu_pid)
                if details["rating"] is None and details["title"] is None and not details["tags"]:
                    details = _fetch_luogu_json(luogu_pid)
            else:
                print("Raw code already started with UVA and failed, skipping second Luogu attempt.")
                luogu_pid = code
        else:
            print(f"OJ '{oj}' not currently supported for Luogu detail fetching.")
            return details

        # Check results after construction attempts (only if not Luogu OJ)
        if details["rating"] is not None or details["title"] is not None or details["tags"]:
            log_pid = luogu_pid if luogu_pid else code # Use constructed PID if available
            print(f"Successfully fetched Luogu details for {oj} {code} (Luogu PID: {log_pid}): Rating={details['rating']}, Title='{details['title']}', Tags={details['tags']}")
        else:
            unique_pids = sorted(list(set(pids_tried)))
            print(f"Failed to fetch Luogu details for {oj} {code} (Tried Luogu PID(s): {', '.join(unique_pids)})")

    return details


def fetch_details(oj, code):
    """
    Fetches details based on OJ.
    - Codeforces: Tries scrape (title, names, rating). Fetches Luogu (title, numbers, rating). Merges results, mapping Luogu numbers to names.
    - AtCoder: Fetches Luogu (title, rating, numbers->names). Scrapes AC (score->custom).
    - SPOJ/UVA: Fetches Luogu (title, rating, numbers->names).
    - Luogu: Fetches Luogu directly (title, rating, numbers->names).
    """
    print(f"\nFetching details for {oj} {code}...")
    # Default structure
    final_details = {"rating": None, "title": None, "tags": [], "custom": None}
    luogu_details = None # Initialize luogu_details

    if oj == "Codeforces":
        # --- Start Indented Block for Codeforces ---
        print("Using Codeforces fetching logic.")
        # 1. Scrape Codeforces directly
        cf_scraped_details = _scrape_codeforces_details(code)
        if cf_scraped_details:
            final_details["rating"] = cf_scraped_details.get("rating") # Rating from CF scrape
            final_details["title"] = cf_scraped_details.get("title")
            # Tags from CF scrape are names, store them directly
            final_details["tags"] = cf_scraped_details.get("tags", [])
            print(f"CF Scrape results: Rating={final_details['rating']}, Title='{final_details['title']}', Tags={final_details['tags']}")
        else:
            print("Codeforces direct scraping failed or yielded no useful data.")

        # 2. Fetch Luogu details (potentially overriding title/rating, adding tags)
        luogu_details = fetch_luogu_details(oj, code)
        if luogu_details:
            # Override rating if Luogu has one and CF didn't, or if Luogu's is non-zero
            if luogu_details.get("rating") is not None and (final_details["rating"] is None or luogu_details.get("rating") != 0):
                final_details["rating"] = luogu_details.get("rating")
                print(f"Using Luogu rating: {final_details['rating']}")
            # Override title if Luogu has one and CF didn't
            if luogu_details.get("title") and not final_details["title"]:
                final_details["title"] = luogu_details.get("title")
                print(f"Using Luogu title: {final_details['title']}")
            # Map Luogu numeric tags to names
            luogu_numeric_tags = luogu_details.get("tags", [])
            luogu_mapped_tags = _map_luogu_tags(luogu_numeric_tags)
            print(f"Mapped Luogu tags for CF: {luogu_mapped_tags}")
            # Combine unique tags (preferring CF scraped names if duplicates exist conceptually)
            existing_tags_lower = {tag.lower() for tag in final_details["tags"]}
            for tag in luogu_mapped_tags:
                if tag.lower() not in existing_tags_lower:
                    final_details["tags"].append(tag)
            print(f"Combined unique tags for CF: {final_details['tags']}")
        else:
            print("Failed to fetch additional details from Luogu for CF.")
        # custom remains None for CF
        return final_details
        # --- End Indented Block for Codeforces ---

    elif oj == "AtCoder":
        # --- Start Indented Block for AtCoder ---
        print("Using AtCoder fetching logic.")
        # 1. Fetch Luogu details (Title, Rating, Tags)
        luogu_details = fetch_luogu_details(oj, code)
        if luogu_details:
            final_details["rating"] = luogu_details.get("rating")
            final_details["title"] = luogu_details.get("title")
            # Fetch and map Luogu tags
            luogu_numeric_tags = luogu_details.get("tags", [])
            final_details["tags"] = _map_luogu_tags(luogu_numeric_tags)
            print(f"Fetched from Luogu for AC: Rating={final_details['rating']}, Title='{final_details['title']}', Tags={final_details['tags']}")
        else:
            print("Failed to fetch details from Luogu for AC.")

        # 2. Scrape AtCoder for score (into 'custom' field)
        atcoder_score = _scrape_atcoder_score(code)
        if atcoder_score:
            final_details["custom"] = atcoder_score
            print(f"Scraped AtCoder score into Custom field: {final_details['custom']}")
        else:
            print("Failed to scrape score from AtCoder.")
        return final_details
        # --- End Indented Block for AtCoder ---

    elif oj == "Luogu":
        print(f"Using Luogu fetching logic directly for {oj}.")
        luogu_details = fetch_luogu_details(oj, code) # Should use raw code
        if luogu_details:
            final_details["rating"] = luogu_details.get("rating")
            final_details["title"] = luogu_details.get("title")
            # Fetch and map Luogu tags
            luogu_numeric_tags = luogu_details.get("tags", [])
            final_details["tags"] = _map_luogu_tags(luogu_numeric_tags)
            print(f"Mapped Luogu tags for {oj}: {final_details['tags']}")
        else:
             print(f"Failed to fetch details from Luogu for {oj}.")
        # custom remains None
        return final_details

    elif oj in ["SPOJ", "UVA"]:
        print(f"Using {oj} fetching logic (via Luogu).")
        luogu_details = fetch_luogu_details(oj, code)
        if luogu_details:
            final_details["rating"] = luogu_details.get("rating")
            final_details["title"] = luogu_details.get("title")
            # Fetch and map Luogu tags
            luogu_numeric_tags = luogu_details.get("tags", [])
            final_details["tags"] = _map_luogu_tags(luogu_numeric_tags)
            print(f"Mapped Luogu tags for {oj}: {final_details['tags']}")
        else:
             print(f"Failed to fetch details from Luogu for {oj}.")
        # custom remains None
        return final_details
    else:
        print(f"OJ '{oj}' not supported for automatic detail fetching.")
        return final_details # Return default empty structure

# --- Routes ---

@problem_bp.route('/fetch-luogu-details', methods=['GET'])
@login_required
def fetch_details_route():
    oj = request.args.get('oj')
    code = request.args.get('code')

    if not oj or not code:
        return jsonify({"error": "Missing 'oj' or 'code' parameter"}), 400

    details = fetch_details(oj, code)

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

