from flask import Flask, render_template, request, url_for, redirect, g
import sqlite3
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user      
from werkzeug.security import generate_password_hash, check_password_hash  
from datetime import datetime       
import requests       

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
            xp INTEGER DEFAULT 0,
            credits INTEGER DEFAULT 0,
            dob DATE,
            goal TEXT,
            avatar_path TEXT DEFAULT '/static/avatar/default.jpg',
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
    db = get_db()
    
    # Get profile info
    profile = db.execute(
        "SELECT xp, credits, avatar_path FROM profiles WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()

    # Get latest workout (most recent submission)
    latest_workout = db.execute(
        "SELECT pushup, situp, run, score FROM workout_tracking WHERE user_id = ? ORDER BY date_submitted DESC LIMIT 1",
        (current_user.id,)
    ).fetchone()

    # Calculate level + progress (example: every 100 XP = next level)
    xp = profile["xp"] if profile else 0
    level = (xp // 100) + 1
    xp_progress = xp % 100
    xp_need = 100
    xp_percent = int((xp_progress / xp_need) * 100)

    # Tier based on latest IPPT score
    tier = "PASS"
    if latest_workout:
        score = latest_workout["score"]
        if score >= 85:
            tier = "GOLD"
        elif score >= 65:
            tier = "SILVER"
        elif score >= 51:
            tier = "PASS"
        else:
            tier = "FAIL"
        pushups = latest_workout["pushup"]
        situps = latest_workout["situp"]
        run_time = str(latest_workout["run"])
    else:
        score = 0
        pushups = 0
        situps = 0
        run_time = "00:00"

    avatar_url = profile["avatar_path"] if profile and profile["avatar_path"] else None
    credits = profile["credits"] if profile else 0

    return render_template(
        "home.html",
        xp=xp,
        level=level,
        xp_progress=xp_progress,
        xp_need=xp_need,
        xp_percent=xp_percent,
        tier=tier,
        score=score,
        pushups=pushups,
        situps=situps,
        run_time=run_time,
        avatar_url=avatar_url,
        credits=credits
    )

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
    return render_template("shop.html", credits=1000)


@app.route("/tracker")
@login_required
def tracker():
    db = get_db()
    results = db.execute("SELECT date_submitted, score FROM workout_tracking ORDER BY date_submitted").fetchall()
    dates = [row[0] for row in results]
    scores = [row[1] for row in results]
    return render_template("tracker.html", dates=dates, scores=scores)


@app.route("/workout", methods=["GET", "POST"])
@login_required
def workout():
    db = get_db()
    if request.method == "POST":
        pushup = int(request.form["pushup"])
        situp = int(request.form["situp"])
        run = float(request.form["run"])
        dob_row = db.execute(
            "SELECT dob FROM profiles WHERE user_id = ?", (current_user.id,)
        ).fetchone()


        response = requests.get(
            f"https://ippt.vercel.app/api?age={age}&situps={situp}&pushups={pushup}&run={run}"
        )

        if response.status_code == 200:
            data = response.json()
            score = data.get("points")  # the API returns total points
            grade = data.get("grade")   # Gold/Silver/Pass/Fail
        else:
            return f"Error fetching IPPT score: {response.status_code}"

        db.execute(
            """
            INSERT INTO workout_tracking (user_id, pushup, situp, run, score, date_submitted)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (current_user.id, pushup, situp, run, score, "2025-10-17") #to replace with below
            #(current_user.id, pushup, situp, run, score, datetime.now())
        )
        db.commit()
          # or redirect somewhere

    return render_template("workout.html")

@app.route("/setworkout", methods=["GET", "POST"])
@login_required
def setworkout():
    db = get_db()
    if request.method == "POST":
        pushup = int(request.form["pushup"])
        situp = int(request.form["situp"])
        run = float(request.form["run"])
        dob_row = db.execute(
            "SELECT dob FROM profiles WHERE user_id = ?", (current_user.id,)
        ).fetchone()
        dob = datetime.strptime(dob_row["dob"], "%Y-%m-%d")
        today = datetime.today()
        age = today.year - dob.year
        print(age)
        response = requests.get(
            f"https://ippt.vercel.app/api?age={age}&situps={situp}&pushups={pushup}&run={run}"
        )

        # if response.status_code == 200:
        #     data = response.json()
        #     score = data.get("points")  # the API returns total points
        #     grade = data.get("grade")   # Gold/Silver/Pass/Fail
        # else:
        #     return f"Error fetching IPPT score: {response.status_code}, {age}, {response}"

        db.execute(
            """
            INSERT INTO workout_tracking (user_id, pushup, situp, run, score, date_submitted)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (current_user.id, pushup, situp, run, 0, "2025-10-17") #to replace with below
            #(current_user.id, pushup, situp, run, score, datetime.now())
        )
        db.commit()
        #   # or redirect somewhere

    return render_template("setworkout.html")

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
        SELECT users.username, profiles.xp
        FROM profiles
        JOIN users ON profiles.user_id = users.id
        ORDER BY profiles.xp DESC
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
