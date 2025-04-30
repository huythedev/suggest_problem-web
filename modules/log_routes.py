import json
from flask import Blueprint, render_template, flash, redirect, url_for, session
# Fix imports - use db directly instead of logs_collection
from modules.config import db
from modules.auth import login_required
from bson import json_util

log_bp = Blueprint('log', __name__)

@log_bp.route('/admin/logs')
@login_required
def view_logs():
    # Check DB connection first
    if db is None:
        flash('Database connection not available.', 'danger')
        # Use blueprint name
        return redirect(url_for('problem.admin_dashboard')) # Redirect if no DB

    try:
        # Use db['logs'] instead of logs_collection
        log_entries = list(db['logs'].find().sort('timestamp', -1))

        # Process details for better display
        for entry in log_entries:
            if 'details' in entry and entry['details']:
                try:
                    # Convert details (which might contain BSON types) to a pretty JSON string
                    entry['details_json'] = json.dumps(
                        entry['details'],
                        indent=2,
                        default=json_util.default # Use bson.json_util for proper serialization
                    )
                except Exception as json_e:
                    print(f"Error converting log details to JSON: {json_e}")
                    entry['details_json'] = f"Error displaying details: {json_e}"
            else:
                entry['details_json'] = None # Ensure the key exists even if details are empty

        return render_template('logs.html', logs=log_entries)
    except Exception as e:
        print(f"Error fetching/rendering logs: {e}") # Log the specific error
        flash(f'Could not retrieve logs due to an internal error: {e}', 'danger')
        # Ensure the except block also returns a response
        return redirect(url_for('problem.admin_dashboard')) # Redirect on error
