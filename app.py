<<<<<<< Updated upstream
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("base.html")

@app.route("/home")
def home():
    return render_template("home.html")
=======
from flask import Flask, render_template, request, url_for, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user                      

app = Flask(__name__)

# check
@app.route("/") 
def getindex():
    return render_template("base.html");

# @app.route("/")
# def home():
#     if current_user.is_authenticated:
#         if current_user.get_user_type()=='staff':
#             return redirect(url_for('staff.staff_home'))
#     return render_template("home.html")
# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = "login"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Here you would normally verify the username and password
        user = User(username)
        login_user(user)
        return redirect(url_for("getindex"))
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
>>>>>>> Stashed changes

if __name__ == "__main__":
    app.run(debug=True)
