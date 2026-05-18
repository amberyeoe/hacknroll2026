from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import get_db


def format_time(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def register_main_routes(app):
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        return redirect(url_for("login_page"))

    @app.route("/home")
    @login_required
    def home():
        db = get_db()

        profile = db.execute(
            "SELECT xp, credits, avatar_path FROM profiles WHERE user_id = ?",
            (current_user.id,),
        ).fetchone()
        if not profile:
            return redirect(url_for("onboarding"))

        latest_workout = db.execute(
            """
            SELECT pushup, situp, run, score
            FROM workout_tracking
            WHERE user_id = ?
            ORDER BY date_submitted DESC
            LIMIT 1
            """,
            (current_user.id,),
        ).fetchone()

        xp = profile["xp"] if profile else 0
        level = (xp // 100) + 1
        xp_progress = xp % 100
        xp_need = 100
        xp_percent = int((xp_progress / xp_need) * 100)

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
            run_time=format_time(run_time),
            avatar_url=profile["avatar_path"],
            credits=profile["credits"],
        )

    @app.route("/onboarding", methods=["GET", "POST"])
    @login_required
    def onboarding():
        if request.method == "POST":
            dob = request.form.get("birthdate")
            next_ippt_date = request.form.get("next_ippt")
            prev_ippt_score = request.form.get("prev_ippt_score")
            goal = request.form.get("goal")

            if not all([dob, next_ippt_date, prev_ippt_score, goal]):
                return "Missing onboarding fields", 400

            db = get_db()
            db.execute(
                """
                INSERT INTO profiles (user_id, dob, next_ippt_date, prev_ippt_score, goal)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    dob = excluded.dob,
                    next_ippt_date = excluded.next_ippt_date,
                    prev_ippt_score = excluded.prev_ippt_score,
                    goal = excluded.goal
                """,
                (current_user.id, dob, next_ippt_date, prev_ippt_score, goal),
            )
            db.commit()
            return redirect(url_for("home"))

        return render_template("onboarding.html")

    @app.route("/leaderboard")
    def leaderboard():
        db = get_db()
        users_points = db.execute(
            """
            SELECT users.username, profiles.xp
            FROM profiles
            JOIN users ON profiles.user_id = users.id
            ORDER BY profiles.xp DESC
            """
        ).fetchall()

        return render_template("leaderboard.html", users_points=users_points)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        db = get_db()

        if request.method == "POST":
            dob = request.form.get("dob")
            next_ippt_date = request.form.get("next_ippt_date")
            prev_ippt_score = request.form.get("last_ippt_score")

            db.execute(
                """
                UPDATE profiles
                SET dob = ?, next_ippt_date = ?, prev_ippt_score = ?
                WHERE user_id = ?
                """,
                (dob, next_ippt_date, prev_ippt_score, current_user.id),
            )
            db.commit()

            return redirect(url_for("profile"))

        user = db.execute(
            """
            SELECT dob, next_ippt_date, prev_ippt_score
            FROM profiles
            WHERE user_id = ?
            """,
            (current_user.id,),
        ).fetchone()

        return render_template("profile.html", user=user)
