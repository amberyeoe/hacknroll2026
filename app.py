from flask import Flask, render_template, request, url_for, redirect, g, request, jsonify
import sqlite3
import os
import secrets
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user      
from werkzeug.security import generate_password_hash, check_password_hash  
from datetime import datetime       
import requests       

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

DATABASE = "database.db"

SHOP_ITEMS = [
    {
        "key": "headband",
        "name": "Headband",
        "desc": "Keeps sweat off",
        "price": 50,
        "category": "accessory",
        "preview_image": "images/shop/items/headband.png",
    },
    {
        "key": "headphones",
        "name": "Headphones",
        "desc": "Workout soundtrack",
        "price": 180,
        "category": "accessory",
        "preview_image": "images/shop/items/headphones.png",
    },
    {
        "key": "wristband",
        "name": "Wristband",
        "desc": "Grip & comfort",
        "price": 60,
        "category": "accessory",
        "preview_image": "images/shop/items/wristband.png",
    },
    {
        "key": "watch",
        "name": "Sports Watch",
        "desc": "Track your runs",
        "price": 220,
        "category": "accessory",
        "preview_image": "images/shop/items/watch.png",
    },
    {
        "key": "nikeshirt",
        "name": "Nike T-Shirt",
        "desc": "Classic training fit",
        "price": 140,
        "category": "top",
        "preview_image": "images/shop/items/nikeshirt.png",
    },
    {
        "key": "nikesinglet",
        "name": "Nike Singlet",
        "desc": "Light & breathable",
        "price": 130,
        "category": "top",
        "preview_image": "images/shop/items/nikesinglet.png",
    },
]

SHOP_ITEM_ORDER = [item["key"] for item in SHOP_ITEMS]
SHOP_ITEM_BY_KEY = {item["key"]: item for item in SHOP_ITEMS}
SHOP_ITEM_CATEGORIES = {item["key"]: item["category"] for item in SHOP_ITEMS}
TOP_ITEM_KEYS = {
    item["key"] for item in SHOP_ITEMS if item["category"] == "top"
}
ITEM_KEY_ALIASES = {
    "headband": "headband",
    "headphones": "headphones",
    "headphone": "headphones",
    "wristband": "wristband",
    "watch": "watch",
    "nikeshirt": "nikeshirt",
    "nikesinglet": "nikesinglet",
}

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

def item_keys_from_value(value):
    if not value:
        return []

    raw_value = str(value).replace("\\", "/").lower()
    if raw_value in SHOP_ITEM_BY_KEY:
        return [raw_value]

    filename = raw_value.rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0]
    if "__" in stem:
        return [
            ITEM_KEY_ALIASES[item_key]
            for item_key in stem.split("__")
            if item_key in ITEM_KEY_ALIASES
        ]

    item_key = ITEM_KEY_ALIASES.get(stem)
    return [item_key] if item_key else []

def normalize_item_key(value):
    keys = item_keys_from_value(value)
    return keys[0] if keys else None

def normalize_item_keys(values):
    normalized = []
    seen = set()
    selected_top = None

    for value in values or []:
        for key in item_keys_from_value(value):
            if not key:
                continue

            if key in TOP_ITEM_KEYS:
                if selected_top and selected_top in seen:
                    normalized = [item_key for item_key in normalized if item_key != selected_top]
                    seen.remove(selected_top)
                selected_top = key

            if key not in seen:
                normalized.append(key)
                seen.add(key)

    return [key for key in SHOP_ITEM_ORDER if key in seen]

def avatar_filename_for_items(item_keys):
    normalized = normalize_item_keys(item_keys)
    if not normalized:
        return "avatar/default.jpg"
    return "avatar/combinations/" + "__".join(normalized) + ".png"

def avatar_path_for_items(item_keys):
    return "/static/" + avatar_filename_for_items(item_keys)

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
            run INTEGER,
            score INTEGER,
            date_submitted DATE,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    #ITEMS OWNED TABLES
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS owned_items (
        user_id INTEGER,
        item_path TEXT,
        PRIMARY KEY (user_id, item_path),
        FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipped_items (
        user_id INTEGER,
        item_path TEXT,
        PRIMARY KEY (user_id, item_path),
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
    tier = "FAIL"
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
        run_time = latest_workout["run"]
    else:
        score = 0
        pushups = 0
        situps = 0
        run_time = 0

    avatar_url = profile["avatar_path"] if profile and profile["avatar_path"] else None
    credits = profile["credits"] if profile else 0

    run = format_time(run_time)

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
        run_time=run,
        avatar_url=avatar_url,
        credits=credits
    )

def format_time(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"

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

# @app.route("/shop")
# @login_required
# def shop():
#     db = get_db()
#     row = db.execute(
#             "SELECT credits FROM profiles WHERE user_id = ?", 
#             (current_user.id,)
#     ).fetchone()
#     credits = row["credits"] if row else 0
#     return render_template("shop.html", credits=credits)

@app.route("/shop")
@login_required
def shop():
    db = get_db()

    profile = db.execute("""
        SELECT credits, avatar_path
        FROM profiles
        WHERE user_id = ?
    """, (current_user.id,)).fetchone()
    if not profile:
        return redirect(url_for("onboarding"))

    owned = db.execute("""
        SELECT item_path FROM owned_items
        WHERE user_id = ?
    """, (current_user.id,)).fetchall()

    equipped = db.execute("""
        SELECT item_path FROM equipped_items
        WHERE user_id = ?
    """, (current_user.id,)).fetchall()

    owned_items = normalize_item_keys(row["item_path"] for row in owned)
    equipped_items = normalize_item_keys(row["item_path"] for row in equipped)
    if not equipped_items:
        equipped_items = normalize_item_keys([profile["avatar_path"]])

    for item_key in equipped_items:
        if item_key not in owned_items:
            owned_items.append(item_key)

    avatar_path = avatar_path_for_items(equipped_items)

    return render_template(
        "shop.html",
        credits=profile["credits"],
        avatar_path=avatar_path,
        owned_items=owned_items,
        equipped_items=equipped_items,
        shop_items=SHOP_ITEMS,
        item_order=SHOP_ITEM_ORDER,
        item_categories=SHOP_ITEM_CATEGORIES
    )



@app.route("/shop/save", methods=["POST"])
@login_required
def save_shop():
    data = request.get_json(silent=True) or {}

    try:
        credits = int(data.get("credits", 0))
    except (TypeError, ValueError):
        return jsonify({"message": "Invalid credits"}), 400

    owned_items = normalize_item_keys(data.get("owned_items", []))
    equipped_items = normalize_item_keys(data.get("equipped_items", []))

    for item_key in equipped_items:
        if item_key not in owned_items:
            owned_items.append(item_key)

    avatar_path = avatar_path_for_items(equipped_items)

    db = get_db()

    # Save credits + equipped avatar
    db.execute("""
        UPDATE profiles
        SET credits = ?, avatar_path = ?
        WHERE user_id = ?
    """, (credits, avatar_path, current_user.id))

    # Replace owned/equipped items
    db.execute("DELETE FROM owned_items WHERE user_id = ?", (current_user.id,))
    for item in owned_items:
        db.execute("""
            INSERT INTO owned_items (user_id, item_path)
            VALUES (?, ?)
        """, (current_user.id, item))

    db.execute("DELETE FROM equipped_items WHERE user_id = ?", (current_user.id,))
    for item in equipped_items:
        db.execute("""
            INSERT INTO equipped_items (user_id, item_path)
            VALUES (?, ?)
        """, (current_user.id, item))

    db.commit()
    return jsonify({"avatar_path": avatar_path}), 200



@app.route("/purchase_items", methods=["POST"]) #888
@login_required
def purchase_items():
    data = request.get_json(silent=True) or {}
    avatar_path = data.get("avatar_path")
    try:
        price = int(data.get("price", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid price"}), 400

    item_key = normalize_item_key(avatar_path)
    if not item_key:
        return jsonify({"success": False, "message": "Invalid item"}), 400

    db = get_db()

    # Get current credits
    row = db.execute(
        "SELECT credits FROM profiles WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()

    if not row or row["credits"] < price:
        return jsonify({"success": False, "message": "Insufficient Credits"}), 400

    # Deduct credits
    new_credits = row["credits"] - price
    db.execute(
        "UPDATE profiles SET credits = ? WHERE user_id = ?",
        (new_credits, current_user.id)
    )

    equipped = db.execute("""
        SELECT item_path FROM equipped_items
        WHERE user_id = ?
    """, (current_user.id,)).fetchall()
    equipped_items = normalize_item_keys([row["item_path"] for row in equipped] + [item_key])
    avatar_path = avatar_path_for_items(equipped_items)

    db.execute("""
        INSERT OR IGNORE INTO owned_items (user_id, item_path)
        VALUES (?, ?)
    """, (current_user.id, item_key))

    db.execute("DELETE FROM equipped_items WHERE user_id = ?", (current_user.id,))
    for equipped_item in equipped_items:
        db.execute("""
            INSERT INTO equipped_items (user_id, item_path)
            VALUES (?, ?)
        """, (current_user.id, equipped_item))

    db.execute(
        "UPDATE profiles SET avatar_path = ? WHERE user_id = ?",
        (avatar_path, current_user.id)
    )

    db.commit()

    return jsonify({"success": True, "credits": new_credits, "avatar_path": avatar_path})

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
        pushup = int(request.form["pushups"])
        situp = int(request.form["situps"])
        run_min = int(request.form["run_min"]) 
        run_sec = int(request.form["run_sec"])
        run = (run_min* 60) + run_sec
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
        # return f"Response: {response.status_code}, {response.json().get('total')}, {situp}, {pushup}, {run}"
        if response.status_code == 200:
            score = response.json().get('total')
        else:
            return f"Error fetching IPPT score: {response.status_code}, {age}, {response}"

        today = datetime.now()           # full datetime
        today_str = today.strftime("%Y-%m-%d")

        db.execute(
            """
            DELETE FROM workout_tracking
            WHERE user_id = ? AND date_submitted = ?
            """,
            (current_user.id, today_str)
        )

        db.execute(
            """
            INSERT INTO workout_tracking (user_id, pushup, situp, run, score, date_submitted)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            # (current_user.id, pushup, situp, run, score, "2025-10-17") #to replace with below
            (current_user.id, pushup, situp, run, score, today_str)
        )

        profile = db.execute(
        "SELECT xp FROM profiles WHERE user_id = ?",
        (current_user.id,)
        ).fetchone()

        old_xp = profile["xp"]
        old_level = (old_xp // 100) + 1

        # 2️⃣ Calculate new XP & level
        new_xp = old_xp + score
        new_level = (new_xp // 100) + 1

        # 3️⃣ Calculate credits earned
        levels_gained = new_level - old_level
        credits_earned = max(0, levels_gained * 10)

        # 4️⃣ Update profile
        db.execute(
            """
            UPDATE profiles
            SET xp = ?, credits = credits + ?
            WHERE user_id = ?
            """,
            (new_xp, credits_earned, current_user.id)
        )


        db.commit()
        return redirect(url_for("home"))
          # or redirect somewhere

    return render_template("workout.html")

@app.route("/setworkout", methods=["GET", "POST"])
@login_required
def setworkout():
    db = get_db()
    if request.method == "POST":
        pushup = int(request.form["pushup"])
        situp = int(request.form["situp"])
        run = int(request.form["run"])
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
        # return f"Response: {response.status_code}, {response.json().get('total')}, {situp}, {pushup}, {run}"
        if response.status_code == 200:
            score = response.json().get('total')
        else:
            return f"Error fetching IPPT score: {response.status_code}, {age}, {response}"
        
        today = datetime.now()           # full datetime
        today_str = today.strftime("%Y-%m-%d")

        db.execute(
            """
            DELETE FROM workout_tracking
            WHERE user_id = ? AND date_submitted = ?
            """,
            (current_user.id, today_str)
        )

        db.execute(
            """
            INSERT INTO workout_tracking (user_id, pushup, situp, run, score, date_submitted)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            # (current_user.id, pushup, situp, run, score, "2025-10-17") #to replace with below
            (current_user.id, pushup, situp, run, score, today_str)
        )

        db.execute(
            """
            UPDATE profiles 
            SET xp = xp + ?
            WHERE user_id = ?
            """,
            # (current_user.id, pushup, situp, run, score, "2025-10-17") #to replace with below
            (score, current_user.id)
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


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()

    if request.method == "POST":
        dob = request.form.get("dob")
        next_ippt_date = request.form.get("next_ippt_date")
        prev_ippt_score = request.form.get("last_ippt_score")

        db.execute("""
            UPDATE profiles
            SET dob = ?, next_ippt_date = ?, prev_ippt_score = ?
            WHERE user_id = ?
        """, (dob, next_ippt_date, prev_ippt_score, current_user.id))
        db.commit()

        return redirect(url_for("profile"))

    # GET: fetch existing profile
    user = db.execute("""
        SELECT dob, next_ippt_date, prev_ippt_score
        FROM profiles
        WHERE user_id = ?
    """, (current_user.id,)).fetchone()

    return render_template("profile.html", user=user)

with app.app_context():
    create_tables()


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
