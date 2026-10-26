from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from ..extensions import db
from ..models import User
from . import bp


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            or_(User.username == identity, User.email == identity.lower())
        ).first()
        if user and user.active and user.check_password(password):
            login_user(user, remember=request.form.get("remember") == "on")
            if user.must_change_password:
                flash("For security, update your starter password before continuing.", "warning")
                return redirect(url_for("auth.change_password"))
            flash("Welcome back.", "success")
            next_url = request.args.get("next", "")
            # Avoid open redirects: only allow local application paths.
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("main.dashboard"))
        flash("Sign-in failed. Check your username/email and password, and confirm your account is active.", "danger")
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not current_user.check_password(current_password):
            flash("Your current password is incorrect.", "danger")
        elif len(new_password) < 12:
            flash("Choose a password with at least 12 characters.", "danger")
        elif new_password != confirm_password:
            flash("The new password and confirmation do not match.", "danger")
        elif current_password == new_password:
            flash("Your new password must be different from the current password.", "warning")
        else:
            current_user.set_password(new_password)
            current_user.must_change_password = False
            db.session.commit()
            flash("Password updated successfully.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/change_password.html")
