# app.py
import os
import datetime
import tempfile
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, redirect, url_for, session
from flask_session import Session

from config.database import test_connection
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.task_routes import tasks_bp
from routes.staff_routes import staff_bp
from routes.attendance_routes import attendance_bp
from routes.schedule_routes import schedule_bp
from routes.material_routes import materials_bp
from routes.handout_routes import handouts_bp
from routes.issue_routes import issues_bp
from routes.report_routes import reports_bp

IS_PRODUCTION = os.environ.get("FLASK_ENV") == "production"

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SESSION_SECRET", "dev_only_change_me")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(tempfile.gettempdir(), "campus_cleaning_flask_sessions")
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(hours=8)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
Session(app)

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(schedule_bp)
app.register_blueprint(materials_bp)
app.register_blueprint(handouts_bp)
app.register_blueprint(issues_bp)
app.register_blueprint(reports_bp)

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response
@app.route("/")
def index():
    if session.get("user_id"):
        if session.get("role") == "SUPERVISOR":
            return redirect(url_for("dashboard.supervisor_dashboard"))
        return redirect(url_for("dashboard.cleaning_dashboard"))
    return redirect(url_for("auth.login_page"))


if __name__ == "__main__":
    try:
        test_connection()
        print("MySQL connection OK.")
    except Exception as e:
        print("Could not connect to MySQL. Check your .env settings.")
        print(str(e))
        raise SystemExit(1)

    port = int(os.environ.get("PORT", 5000))
    print(f"Server running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=not IS_PRODUCTION)
