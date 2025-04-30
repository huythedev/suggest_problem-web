from flask import Blueprint, request, session, redirect, url_for, flash, render_template, jsonify
from functools import wraps
# Use absolute import with modules. prefix
from modules.config import ADMIN_CREDENTIALS as ADMINS # ADMINS is a dict {username: password}

auth_bp = Blueprint('auth', __name__)

# --- Authentication Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                 return jsonify({'error': 'Authentication required'}), 401
            # Use blueprint name in url_for
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username_attempt = request.form.get('username')
        password_attempt = request.form.get('password')

        # Check if the username exists in the ADMINS dict and the password matches
        if username_attempt in ADMINS and ADMINS[username_attempt] == password_attempt:
            session['logged_in'] = True
            session['username'] = username_attempt
            flash('Login successful!', 'success')
            next_url = request.args.get('next')
            # Use blueprint name for other routes if they are in blueprints
            return redirect(next_url or url_for('problem.admin_dashboard')) # Assuming admin_dashboard is in 'problem' blueprint
        else:
            # Login failed
            flash('Invalid credentials. Please try again.', 'danger')
            # No need to return render_template here, let it fall through to the GET part if needed

    # Handle GET request or failed POST attempt (render login page)
    if 'logged_in' in session:
        # If already logged in, redirect to dashboard
        return redirect(url_for('problem.admin_dashboard'))
    return render_template('admin_login.html') # Render login page for GET or failed POST


@auth_bp.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    # Use blueprint name
    return redirect(url_for('auth.admin_login'))
