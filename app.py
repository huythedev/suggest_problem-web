from flask import Flask
from flask_cors import CORS

from modules.config import SECRET_KEY, db
from modules.auth import auth_bp
from modules.problem_routes import problem_bp
from modules.log_routes import log_bp

# Create and configure the app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(problem_bp)
app.register_blueprint(log_bp)

# Add a check for database connection
if db is None:
    print("\n" + "="*50)
    print("FATAL: Database connection failed. Application might not work correctly.")
    print("Please check your MONGO_URI in .env and network connectivity.")
    print("="*50 + "\n")
    # You might add a simple route to display an error page if DB is down
    @app.route('/db_error')
    def db_error():
        return "Database connection failed. Please contact the administrator.", 503

# Main execution handled by run.py or WSGI server
# No need for app.run() here if using run.py
