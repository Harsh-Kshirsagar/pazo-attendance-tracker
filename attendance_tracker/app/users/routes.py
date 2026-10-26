from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ..decorators import admin_required
from ..extensions import db
from ..models import User
from . import bp


def _last_active_admin(user, new_role, new_active):
    removes_admin_access = user.role == "admin" and user.active and (new_role != "admin" or not new_active)
    if not removes_admin_access:
        return False
    active_admins = User.query.filter_by(role="admin", active=True).count()
    return active_admins <= 1


@bp.route("/")
@admin_required
def index():
    query = request.args.get("q", "").strip()
    users_query = User.query
    if query:
        like = f"%{query}%"
        users_query = users_query.filter(or_(User.username.ilike(like), User.email.ilike(like)))
    users = users_query.order_by(User.role.desc(), User.username.asc()).all()
    return render_template("users/list.html", users=users, query=query)


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        active = request.form.get("active") == "on"
        errors = []
        if not username or len(username) > 80:
            errors.append("Username is required and must be no longer than 80 characters.")
        if not email or "@" not in email:
            errors.append("Enter a valid email address.")
        if len(password) < 12:
            errors.append("Password must contain at least 12 characters.")
        if role not in {"admin", "user"}:
            errors.append("Choose a valid role.")
        if errors:
            for message in errors:
                flash(message, "danger")
        else:
            user = User(username=username, email=email, role=role, active=active, must_change_password=True)
            user.set_password(password)
            try:
                db.session.add(user)
                db.session.commit()
                flash(f"Account '{username}' created.", "success")
                return redirect(url_for("users.index"))
            except IntegrityError:
                db.session.rollback()
                flash("Username or email is already registered.", "danger")
    return render_template("users/form.html", user=None, page_title="Create user")


@bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        active = request.form.get("active") == "on"
        errors = []
        if not username or len(username) > 80:
            errors.append("Username is required and must be no longer than 80 characters.")
        if not email or "@" not in email:
            errors.append("Enter a valid email address.")
        if password and len(password) < 12:
            errors.append("A new password must contain at least 12 characters.")
        if role not in {"admin", "user"}:
            errors.append("Choose a valid role.")
        if _last_active_admin(user, role, active):
            errors.append("You cannot remove or deactivate the last active administrator.")
        if errors:
            for message in errors:
                flash(message, "danger")
        else:
            user.username = username
            user.email = email
            user.role = role
            user.active = active
            if password:
                user.set_password(password)
                user.must_change_password = True
            try:
                db.session.commit()
                flash(f"Account '{username}' updated.", "success")
                return redirect(url_for("users.index"))
            except IntegrityError:
                db.session.rollback()
                flash("Username or email is already registered by another account.", "danger")
    return render_template("users/form.html", user=user, page_title="Edit user")
