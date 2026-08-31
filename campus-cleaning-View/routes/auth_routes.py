
from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from services import auth_service
from utils.password import validate_password_strength
import re

auth_bp = Blueprint("auth", __name__)

GENERIC_LOGIN_ERROR = "Invalid email or password."


def _is_valid_email(email):
    return re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email or "") is not None


def _redirect_target(account):
    if account["Must_Change_Password"]:
        return redirect(url_for("auth.change_password_page"))
    if account["Role"] == "SUPERVISOR":
        return redirect(url_for("dashboard.supervisor_dashboard"))
    return redirect(url_for("dashboard.cleaning_dashboard"))


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if session.get("user_id"):
        account = auth_service.find_account_by_id(session["user_id"])
        if account:
            return _redirect_target(account)
    return render_template("auth/login.html")


@auth_bp.route("/login", methods=["POST"])
def login():
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""

    if not email or not password:
        flash("Please enter both your university email and password.", "error")
        return redirect(url_for("auth.login_page"))
    if not _is_valid_email(email):
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("auth.login_page"))

    result = auth_service.authenticate(email.lower(), password)

    if result["status"] == "invalid":
        flash(GENERIC_LOGIN_ERROR, "error")
        return redirect(url_for("auth.login_page"))
    if result["status"] == "inactive":
        flash("Your account is currently inactive. Please contact the university administration.", "error")
        return redirect(url_for("auth.login_page"))
    if result["status"] == "suspended":
        flash("Your account has been suspended. Please contact the university administration.", "error")
        return redirect(url_for("auth.login_page"))

    account = result["account"]

    session.clear()
    session["user_id"] = account["User_ID"]
    session["staff_id"] = account["Staff_ID"]
    session["role"] = account["Role"]
    session["user_name"] = account["Full_Name"]
    session.permanent = True

    try:
        auth_service.touch_last_login(account["User_ID"])
    except Exception as e:
        print("Failed to update Last_Login:", e)

    return _redirect_target(account)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/change-password", methods=["GET"])
def change_password_page():
    if not session.get("user_id"):
        return redirect(url_for("auth.login_page"))
    return render_template("auth/change_password.html")


@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    if not session.get("user_id"):
        return redirect(url_for("auth.login_page"))

    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not current_password or not new_password or not confirm_password:
        flash("All fields are required.", "error")
        return redirect(url_for("auth.change_password_page"))
    if new_password != confirm_password:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("auth.change_password_page"))

    valid, message = validate_password_strength(new_password)
    if not valid:
        flash(message, "error")
        return redirect(url_for("auth.change_password_page"))

    result = auth_service.change_password(session["user_id"], current_password, new_password)
    if not result["ok"]:
        flash("Current password is incorrect.", "error")
        return redirect(url_for("auth.change_password_page"))

    account = auth_service.find_account_by_id(session["user_id"])
    if account["Role"] == "SUPERVISOR":
        return redirect(url_for("dashboard.supervisor_dashboard"))
    return redirect(url_for("dashboard.cleaning_dashboard"))


@auth_bp.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    return render_template("auth/forgot_password.html")


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    email = (request.form.get("email") or "").strip()
    user_id = request.form.get("user_id")

    if not email or not user_id:
        flash("Please enter both your university email and User ID.", "error")
        return redirect(url_for("auth.forgot_password_page"))

    try:
        numeric_user_id = int(user_id)
    except ValueError:
        flash("Invalid User ID.", "error")
        return redirect(url_for("auth.forgot_password_page"))

    account = auth_service.find_account_by_id_and_email(numeric_user_id, email.lower())
    if not account:
        flash("We could not verify those details. Please check and try again.", "error")
        return redirect(url_for("auth.forgot_password_page"))

    session["reset_verified"] = {"userId": account["User_ID"], "email": account["University_Email"]}
    return redirect(url_for("auth.reset_password_page"))


@auth_bp.route("/reset-password", methods=["GET"])
def reset_password_page():
    if not session.get("reset_verified"):
        flash("Please verify your identity first.", "error")
        return redirect(url_for("auth.forgot_password_page"))
    return render_template("auth/reset_password.html")


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    verified = session.get("reset_verified")
    if not verified:
        flash("Identity not verified. Please restart the password reset process.", "error")
        return redirect(url_for("auth.forgot_password_page"))

    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not new_password or not confirm_password:
        flash("All fields are required.", "error")
        return redirect(url_for("auth.reset_password_page"))
    if new_password != confirm_password:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("auth.reset_password_page"))

    valid, message = validate_password_strength(new_password)
    if not valid:
        flash(message, "error")
        return redirect(url_for("auth.reset_password_page"))

    ok = auth_service.reset_password(verified["userId"], verified["email"], new_password)
    if not ok:
        flash("Could not reset password. Please restart the process.", "error")
        return redirect(url_for("auth.forgot_password_page"))

    session.pop("reset_verified", None)
    flash("Password reset successfully. Please log in.", "success")
    return redirect(url_for("auth.login_page"))
