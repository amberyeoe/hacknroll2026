from flask import Flask, render_template, request, url_for, redirect, g
import sqlite3
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user      
from werkzeug.security import generate_password_hash, check_password_hash  
from datetime import datetime              

app = Flask(__name__)
app.secret_key = "dev-secret-key"

DATABASE = "database.db"

login_manager = LoginManager()
login_manager.init_app(app)
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
        (user_id,)
    ).fetchone()

    if user:
        return User(user["id"], user["username"])
    return None

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()



def create_tables():
    db = get_db()
    cursor = db.cursor()

     # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
     # PROFILES TABLE (one profile per user, use user_id as primary key)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0,
            dob DATE,
            goal TEXT,
            next_ippt_date DATE,
            prev_ippt_score INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # WORKOUT TRACKING TABLE (multiple submissions per user)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            pushup INTEGER,
            situp INTEGER,
            run REAL,
            score INTEGER,
            date_submitted DATE,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)


    db.commit()


#ROUTES
# check
@app.route("/") 
def index():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    return redirect(url_for("login_page"))
# @app.route("/")
# def home():
#     if current_user.is_authenticated:
#         if current_user.get_user_type()=='staff':
#             return redirect(url_for('staff.staff_home'))
#     return render_template("home.html")
# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = "login"

@app.route("/home")
@login_required
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_pw = generate_password_hash(password)

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_pw)
            )
            db.commit()
            db = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            login_user(User(user["id"], user["username"]))
            return redirect(url_for("onboarding"))
        except sqlite3.IntegrityError:
            return "Username already exists"

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Here you would normally verify the username and password
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            login_user(User(user["id"], user["username"]))
            return redirect(url_for("home"))

        return "Invalid username or password"

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))

@app.route("/shop")
@login_required
def shop():
    return render_template("shop.html")


@app.route("/tracker")
@login_required
def tracker():
    return render_template("tracker.html")


@app.route("/workout")
@login_required
def workout():
    return render_template("workout.html")

@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    if request.method == "POST":
        dob = request.form["birthdate"]
        next_ippt_date = request.form["next_ippt"]
        prev_ippt_score = request.form["prev_ippt_score"]
        goal = request.form["goal"]  # <-- matches the updated HTML name

        db = get_db()
        try:
            db.execute(
                """
                INSERT INTO profiles (user_id, dob, next_ippt_date, prev_ippt_score, goal)
                VALUES (?, ?, ?, ?, ?)
                """,
                (current_user.id, dob, next_ippt_date, prev_ippt_score, goal)
            )
            db.commit()
            return redirect(url_for("home"))
        except sqlite3.IntegrityError:
            # If the profile already exists, you could update it instead
            db.execute(
                """
                UPDATE profiles
                SET dob = ?, next_ippt_date = ?, prev_ippt_score = ?, goal = ?
                WHERE user_id = ?
                """,
                (dob, next_ippt_date, prev_ippt_score, goal, current_user.id)
            )
            db.commit()
            return redirect(url_for("home"))

    return render_template("onboarding.html")

@app.route("/leaderboard")
@login_required
def leaderboard():
    db = get_db()
    # Get all users and points, sorted descending
    users_points = db.execute("""
        SELECT users.username, profiles.points
        FROM profiles
        JOIN users ON profiles.user_id = users.id
        ORDER BY profiles.points DESC
    """).fetchall()

    return render_template("leaderboard.html", users_points=users_points)


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


if __name__ == "__main__":
    with app.app_context():
        create_tables()
    app.run(debug=True)
