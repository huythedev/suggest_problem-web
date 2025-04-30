# Web Task Manager (Suggest Problem Web)

A simple web application to manage a list of competitive programming problems from various online judges (OJs). It allows viewing problems publicly and provides an admin interface for adding, editing, deleting, and logging changes.

## Features

*   **Public View:** Displays a filterable and sortable list of problems.
*   **Admin Dashboard:** Secure login for managing problems.
    *   Add new problems with details (OJ, Code, Title, Rating, Tags, Contest Link, Problem Link, Custom Notes).
    *   Edit existing problems.
    *   Delete problems.
*   **Automatic Data Fetching:**
    *   Fetches problem rating and title from Luogu.cn based on OJ and Code (supports Codeforces, AtCoder, SPOJ, UVA).
    *   Parses OJ, Code, and Problem Link from pasted URLs (supports Codeforces, AtCoder, UVA).
    *   Fetches UVA Problem ID and Title directly from the UVA website URL.
*   **Filtering & Sorting:**
    *   Filter problems by multiple OJs.
    *   Filter problems by tags (AND/OR logic).
    *   Sort problems by any column.
*   **Activity Logging:** Records add, update, and delete actions performed by admins.
*   **Environment Configuration:** Uses `.env` file for sensitive settings like database URI and admin credentials.
*   **Cross-Platform:** Uses Waitress on Windows and Gunicorn on POSIX systems.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/huythedev/suggest_problem-web
    cd suggest_problem-web
    ```

2.  **Create a Virtual Environment:**
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Create `.env` file:** Copy the example file:
    ```bash
    # Windows
    copy .env_example .env

    # macOS/Linux
    cp .env_example .env
    ```

2.  **Edit `.env` file:**
    *   **`MONGO_URI`**: Replace the placeholder with your actual MongoDB connection string (e.g., from MongoDB Atlas). Make sure the database name in the URI (like `YourDbName`) is correct or change it as needed.
    *   **`FLASK_SECRET_KEY`**: Change this to a long, random, and secret string. This is crucial for session security.
    *   **Admin Credentials**: Define admin users using numbered pairs starting from 1 (e.g., `ADMIN_USERNAME_1`, `ADMIN_PASSWORD_1`, `ADMIN_USERNAME_2`, `ADMIN_PASSWORD_2`, etc.). The application will load all consecutive pairs found.

    **Example `.env`:**
    ```properties
    MONGO_URI='mongodb+srv://myuser:mypassword@mycluster.mongodb.net/problem_database?retryWrites=true&w=majority'
    FLASK_SECRET_KEY='generate-a-very-secure-random-key-here'

    # Admin Credentials - Use numbered format
    ADMIN_USERNAME_1='admin'
    ADMIN_PASSWORD_1='supersecretpassword'

    ADMIN_USERNAME_2='user2'
    ADMIN_PASSWORD_2='anotherpassword'

    ADMIN_USERNAME_3='editor'
    ADMIN_PASSWORD_3='editpass123'
    ```

## Running the Application

Make sure your virtual environment is activated. Run the application from the project root directory (`e:\Github\suggest_problem-web`):

```bash
python run.py
```

The script will detect your operating system and start the appropriate WSGI server (Waitress on Windows, Gunicorn on Linux/macOS) on `0.0.0.0:12345` by default.

You can access the application in your browser at `http://localhost:12345`.

## Usage

### Public View (`/`)

*   Anyone can view the list of problems.
*   Use the "Select OJ(s)" button to filter by one or more Online Judges.
*   Use the "Lọc tags" input to filter by tags (comma-separated). Select "OR" or "AND" logic.
*   Click on column headers (Tên OJ, Mã bài, Tên bài, Rating, etc.) to sort the table.
*   Problem codes and contest names that are valid URLs will be clickable links.

### Admin Login (`/admin/login`)

*   Access the login page via the link in the public view header or by navigating directly.
*   Enter credentials for any user defined in the `.env` file (using the numbered format).

### Admin Dashboard (`/admin`)

*   Accessible after successful login.
*   Provides the same filtering and sorting options as the public view.
*   **Add Task:**
    *   Click the "Add Task" button.
    *   Fill in the details in the modal.
    *   **OJ & Code:** Required. When you enter these and move focus, the app tries to fetch Rating and Title from Luogu.
    *   **Problem Link (Optional):** If you paste a supported URL (CF, AC, UVA), the OJ, Code, and potentially Title fields will be auto-filled.
    *   **Title & Rating:** Required. Can be auto-filled or entered manually.
    *   **Contest:** Enter a contest name or a URL to the contest page. Defaults to "No".
    *   **Tags:** Comma-separated list.
    *   Click "Save".
*   **Edit Task:**
    *   Click the "Edit" button on a problem row.
    *   Modify details in the modal.
    *   Click "Update".
*   **Delete Task:**
    *   Click the "Delete" button on a problem row.
    *   Confirm the deletion.
*   **Activity Logs:** Click the "Activity Logs" link in the header to view a history of add, update, and delete actions.
*   **Logout:** Click the "Logout" link.

### Clearing Logs (`clear_logs.py`)

A utility script is provided to clear the activity logs collection in the database. Run it from the project root with the virtual environment activated:

```bash
python clear_logs.py
```

It will ask for confirmation before deleting the logs.
