import os

import click
from datetime import date
from flask import Flask, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import inspect, or_

from config import Config
from .extensions import csrf, db, login_manager


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    if os.getenv("APP_ENV", "development").lower() == "production":
        if app.config["SECRET_KEY"] == "dev-only-change-this-secret-key":
            raise RuntimeError("Set a strong SECRET_KEY in the production environment.")
        app.config["SESSION_COOKIE_SECURE"] = True

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .attendance import bp as attendance_bp
    from .people import bp as people_bp
    from .users import bp as users_bp
    from .reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(people_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)

    @app.before_request
    def enforce_password_change():
        # New/demo credentials must be changed before protected parts of the app are used.
        if current_user.is_authenticated and getattr(current_user, "must_change_password", False):
            allowed_endpoints = {"auth.change_password", "auth.logout", "static"}
            if request.endpoint not in allowed_endpoints:
                return redirect(url_for("auth.change_password"))
        return None

    @app.context_processor
    def inject_global_template_values():
        return {"app_name": "PAZO Attendance Tracker", "current_user": current_user, "now_year": date.today().year}

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables from the ORM models."""
        with app.app_context():
            db.create_all()
        click.echo("Database tables created. For a fresh installation, also review sql/schema.sql.")

    @app.cli.command("seed-admin")
    def seed_admin_command():
        """Create the first admin from ADMIN_USERNAME/EMAIL/PASSWORD environment variables."""
        username = os.getenv("ADMIN_USERNAME", "admin").strip()
        email = os.getenv("ADMIN_EMAIL", "admin@pazo.local").strip().lower()
        password = os.getenv("ADMIN_PASSWORD", "ChangeMe@2026!")
        if len(password) < 12:
            raise click.ClickException("ADMIN_PASSWORD must contain at least 12 characters.")
        with app.app_context():
            if not inspect(db.engine).has_table("users"):
                raise click.ClickException("Tables do not exist. Run: flask --app run.py init-db")
            existing = User.query.filter(or_(User.username == username, User.email == email)).first()
            if existing:
                click.echo(f"A user with username/email already exists: {existing.username}. No changes made.")
                return
            user = User(username=username, email=email, role="admin", active=True, must_change_password=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        click.echo(f"Created admin account '{username}'. Sign in and change the initial password if applicable.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin_command(username, email, password):
        """Interactively create an additional admin account."""
        if len(password) < 12:
            raise click.ClickException("Password must contain at least 12 characters.")
        with app.app_context():
            if User.query.filter(or_(User.username == username.strip(), User.email == email.strip().lower())).first():
                raise click.ClickException("That username or email is already registered.")
            user = User(username=username.strip(), email=email.strip().lower(), role="admin", active=True, must_change_password=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        click.echo("Admin account created.")

    return app
