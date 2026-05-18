import sqlite3

from flask import redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db


login_manager = LoginManager()
login_manager.login_view = "login_page"


class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if user:
        return User(user["id"], user["username"])
    return None


def init_login(app):
    login_manager.init_app(app)


def register_auth_routes(app):
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not username or not password:
                return "Username and password are required", 400

            hashed_pw = generate_password_hash(password)
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, hashed_pw),
                )
                db.commit()
                user = db.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,),
                ).fetchone()

                login_user(User(user["id"], user["username"]))
                return redirect(url_for("onboarding"))
            except sqlite3.IntegrityError:
                return "Username already exists", 409

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login_page():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            db = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if user and check_password_hash(user["password"], password):
                login_user(User(user["id"], user["username"]))
                return redirect(url_for("home"))

            return "Invalid username or password", 401

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login_page"))
