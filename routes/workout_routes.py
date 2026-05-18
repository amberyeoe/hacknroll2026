from datetime import date, datetime

from flask import current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import get_db
from ippt import IPPTScoreError, age_on, fetch_ippt_score


def parse_nonnegative_int(value, field_name):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field_name}") from exc
    if parsed < 0:
        raise ValueError(f"Invalid {field_name}")
    return parsed


def get_user_age(db, user_id):
    dob_row = db.execute(
        "SELECT dob FROM profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not dob_row or not dob_row["dob"]:
        raise ValueError("Missing date of birth")
    dob = datetime.strptime(dob_row["dob"], "%Y-%m-%d").date()
    return age_on(dob)


def get_score(age, situp, pushup, run_seconds):
    return fetch_ippt_score(
        current_app.config["IPPT_API_URL"],
        current_app.config["IPPT_API_TIMEOUT"],
        age=age,
        situps=situp,
        pushups=pushup,
        run_seconds=run_seconds,
    )


def save_workout(db, user_id, pushup, situp, run_seconds, score):
    today_str = date.today().strftime("%Y-%m-%d")
    db.execute(
        """
        DELETE FROM workout_tracking
        WHERE user_id = ? AND date_submitted = ?
        """,
        (user_id, today_str),
    )
    db.execute(
        """
        INSERT INTO workout_tracking (user_id, pushup, situp, run, score, date_submitted)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, pushup, situp, run_seconds, score, today_str),
    )


def register_workout_routes(app):
    @app.route("/tracker")
    @login_required
    def tracker():
        db = get_db()
        results = db.execute(
            """
            SELECT date_submitted, score
            FROM workout_tracking
            WHERE user_id = ?
            ORDER BY date_submitted
            """,
            (current_user.id,),
        ).fetchall()
        dates = [row["date_submitted"] for row in results]
        scores = [row["score"] for row in results]
        return render_template("tracker.html", dates=dates, scores=scores)

    @app.route("/workout", methods=["GET", "POST"])
    @login_required
    def workout():
        db = get_db()
        if request.method == "POST":
            try:
                pushup = parse_nonnegative_int(request.form.get("pushups"), "push-ups")
                situp = parse_nonnegative_int(request.form.get("situps"), "sit-ups")
                run_min = parse_nonnegative_int(request.form.get("run_min"), "run minutes")
                run_sec = parse_nonnegative_int(request.form.get("run_sec"), "run seconds")
                if run_sec > 59:
                    return "Run seconds must be between 0 and 59", 400
                run_seconds = (run_min * 60) + run_sec
                age = get_user_age(db, current_user.id)
                score = get_score(age, situp, pushup, run_seconds)
            except ValueError as exc:
                return str(exc), 400
            except IPPTScoreError as exc:
                return str(exc), 502

            save_workout(db, current_user.id, pushup, situp, run_seconds, score)

            profile = db.execute(
                "SELECT xp FROM profiles WHERE user_id = ?",
                (current_user.id,),
            ).fetchone()
            old_xp = profile["xp"]
            old_level = (old_xp // 100) + 1
            new_xp = old_xp + score
            new_level = (new_xp // 100) + 1
            credits_earned = max(0, (new_level - old_level) * 10)

            db.execute(
                """
                UPDATE profiles
                SET xp = ?, credits = credits + ?
                WHERE user_id = ?
                """,
                (new_xp, credits_earned, current_user.id),
            )
            db.commit()
            return redirect(url_for("home"))

        return render_template(
            "workout.html",
            workout_test_seconds=current_app.config["WORKOUT_TEST_SECONDS"],
        )

    @app.route("/setworkout", methods=["GET", "POST"])
    @login_required
    def setworkout():
        db = get_db()
        if request.method == "POST":
            try:
                pushup = parse_nonnegative_int(request.form.get("pushup"), "push-ups")
                situp = parse_nonnegative_int(request.form.get("situp"), "sit-ups")
                run_seconds = parse_nonnegative_int(request.form.get("run"), "run")
                age = get_user_age(db, current_user.id)
                score = get_score(age, situp, pushup, run_seconds)
            except ValueError as exc:
                return str(exc), 400
            except IPPTScoreError as exc:
                return str(exc), 502

            save_workout(db, current_user.id, pushup, situp, run_seconds, score)
            db.execute(
                """
                UPDATE profiles
                SET xp = xp + ?
                WHERE user_id = ?
                """,
                (score, current_user.id),
            )
            db.commit()

        return render_template("setworkout.html")
