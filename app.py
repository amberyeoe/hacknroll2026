from flask import Flask, render_template, request, url_for, redirect, g
import sqlite3
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user      
from werkzeug.security import generate_password_hash, check_password_hash  
from datetime import datetime              

app = Flask(__name__)

DATABASE = "database.db"

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    db.commit()


#ROUTES
# check
@app.route("/") 
def base():
    return render_template("base.html")

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
def home():
    return render_template("home.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Here you would normally verify the username and password
        user = User(username)
        login_user(user)
        return redirect(url_for("base"))
    return render_template("login.html")


@app.route("/shop")
def shop():
    return render_template("shop.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # Handle user registration logic here
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/tracker")
def tracker():
    return render_template("tracker.html")


@app.route("/workout")
def workout():
    return render_template("workout.html")

if __name__ == "__main__":
    app.run(debug=True)
