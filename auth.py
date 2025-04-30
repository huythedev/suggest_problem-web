from flask import Blueprint, request, session, redirect, url_for, flash, render_template, jsonify
from functools import wraps
# Use absolute import
from config import ADMINS

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
        login_successful = False
        for admin in ADMINS:
            if admin['username'] == username_attempt and admin['password'] == password_attempt:
                session['logged_in'] = True
                session['username'] = username_attempt
                flash('Login successful!', 'success')
                next_url = request.args.get('next')
                login_successful = True
                # Use blueprint name for other routes if they are in blueprints
                return redirect(next_url or url_for('problem.admin_dashboard')) # Assuming admin_dashboard is in 'problem' blueprint

        if not login_successful:
            flash('Invalid credentials. Please try again.', 'danger')
            return render_template('admin_login.html')

    if 'logged_in' in session:
        # Use blueprint name
        return redirect(url_for('problem.admin_dashboard'))
    return render_template('admin_login.html')


@auth_bp.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    # Use blueprint name
    return redirect(url_for('auth.admin_login'))
