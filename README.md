# Web Task Manager (Suggest Problem)

A Flask-based web application for managing a list of competitive programming problems from various online judges (OJs). It allows administrators to add, edit, delete, and view problems, and provides a public view for browsing.

## Features

*   **Problem Management:** Add, edit, and delete problems with details like OJ, Code, Title, Rating, Tags, Custom data (e.g., AtCoder score), and Contest link.
*   **Multi-OJ Support:** Configured for Codeforces, AtCoder, SPOJ, UVA, and potentially others.
*   **Automatic Detail Fetching:**
    *   Attempts to fetch problem Title, Rating, Tags, and Custom data from the source OJ (Codeforces, AtCoder) or Luogu.
    *   Fetches Luogu difficulty rating as a fallback or primary rating.
    *   Fetches Luogu tags (numeric IDs) and maps them to English names.
    *   Combines tags from direct scraping (Codeforces) and Luogu mapping.
    *   Fetches AtCoder problem score into the 'Custom' field.
    *   Parses problem OJ/Code from URLs (Codeforces, AtCoder, UVA).
    *   Fetches UVA problem ID and Title from its URL via a backend endpoint.
*   **Filtering & Sorting:** Filter problems by selected OJs (multi-select), tags (AND/OR mode), and sort columns.
*   **Admin Interface:** Secure login for administrators to manage problems.
*   **Public View:** A read-only view of the problem list for non-logged-in users.
*   **Activity Logging:** Records actions (add, update, delete) performed by administrators.
*   **Environment Configuration:** Uses `.env` file for sensitive settings like database URI, secret key, and admin credentials.
*   **Deployment Ready:** Includes `run.py` script for running with Waitress (Windows) or Gunicorn (POSIX).

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/huythedev/suggest_problem-web
    cd suggest_problem-web
    ```
2.  **Run the custom setup command:**
    *   This command will attempt to find your Python installation, create a virtual environment named `venv`, install the required dependencies into it, and prompt you to create the `.env` configuration file.
    *   Try running with `python3` first if you are on macOS/Linux:
        ```bash
        python3 setup.py setup_dev_env
        ```
    *   If `python3` doesn't work or you are on Windows, use `python`:
        ```bash
        python setup.py setup_dev_env
        ```
    *   Follow the prompts to enter your MongoDB URI and initial admin credentials.
3.  **Activate the virtual environment:**
    *   The setup command will print the correct activation command for your OS at the end. Typically:
    *   Windows: `.\venv\Scripts\activate`
    *   POSIX (Linux/macOS): `source venv/bin/activate`
    *   **Important:** You need to activate the environment in *every new terminal session* before running the application.
4.  **(Optional) Review Environment Variables:**
    *   The `.env` file was created in step 2. You can review or edit it if needed (e.g., to add more admin users or change the `FLASK_SECRET_KEY`).

## Running the Application

1.  **Ensure the virtual environment is activated** (see step 3 in Setup). You should see `(venv)` at the beginning of your terminal prompt.
2.  Execute the `run.py` script from the project root directory:
    ```bash
    python run.py
    ```
3.  The script will first check if the environment setup (`venv` directory and `.env` file) is complete. If not, it will instruct you to run the setup command (`python setup.py setup_dev_env`).
4.  If the setup is complete, the application will be served by Waitress (on Windows) or Gunicorn (on POSIX) at `http://0.0.0.0:12345` by default. Access it via `http://localhost:12345` or `http://<your-ip-address>:12345`.

## Environment Variables (`.env`)

*   `MONGO_URI`: Your MongoDB connection string (set during setup).
*   `FLASK_SECRET_KEY`: A long, random string used for session security (generated during setup).
*   `ADMIN_USERNAME_X`: Username for admin user X (e.g., `ADMIN_USERNAME_1`, set during setup).
*   `ADMIN_PASSWORD_X`: Password for admin user X (e.g., `ADMIN_PASSWORD_1`, set during setup).
*   You can manually add more admins (e.g., `ADMIN_USERNAME_2`, `ADMIN_PASSWORD_2`) to this file.

## Utility Scripts

*   **`clear_logs.py`**: Clears all entries from the `logs` collection in the database after confirmation. Run with `python clear_logs.py` (ensure venv is active).

## Project Structure

```
/
|-- .env                  # Local environment variables (created by setup, ignored by git)
|-- .env_example          # Example environment variables
|-- .gitattributes        # Git line ending configuration
|-- .gitignore            # Files/directories ignored by git
|-- app.py                # Flask application factory
|-- clear_logs.py         # Script to clear database logs
|-- requirements.txt      # Python dependencies
|-- run.py                # Script to run the server (Waitress/Gunicorn)
|-- setup.py              # Standard packaging script + custom setup command
|
|-- modules/              # Application modules
|   |-- __init__.py
|   |-- auth.py           # Authentication logic and routes
|   |-- config.py         # Configuration loading (env vars, DB connection)
|   |-- log_routes.py     # Routes for viewing logs
|   |-- models.py         # Database interaction functions (CRUD, logging)
|   |-- problem_routes.py # Core problem fetching, CRUD routes
|
|-- static/               # Static files (CSS, JS)
|   |-- script.js         # Frontend JavaScript logic
|   |-- style.css         # CSS styles
|
|-- templates/            # HTML templates
|   |-- admin.html        # Admin dashboard view
|   |-- admin_login.html  # Admin login page
|   |-- index.html        # Public/main view
|   |-- logs.html         # Activity logs view
|
|-- venv/                 # Virtual environment directory (created by setup, ignored by git)
```
