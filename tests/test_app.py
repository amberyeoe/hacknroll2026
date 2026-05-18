import os
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash


_import_db_fd, _import_db_path = tempfile.mkstemp(suffix=".db")
os.close(_import_db_fd)
os.environ.setdefault("DATABASE", _import_db_path)
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from app import create_app
from db import get_db
from ippt import IPPTScoreError
from routes import workout_routes
from shop_items import expected_avatar_filenames


def tearDownModule():
    try:
        os.remove(_import_db_path)
    except OSError:
        pass


class AppTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.db_path,
                "SECRET_KEY": "test-secret-key",
                "IPPT_API_TIMEOUT": 0.25,
                "WORKOUT_TEST_SECONDS": 60,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def create_user(self, username, credits=999, xp=0):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, generate_password_hash("secret")),
            )
            user_id = db.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()["id"]
            db.execute(
                """
                INSERT INTO profiles (
                    user_id, credits, xp, dob, goal, avatar_path,
                    next_ippt_date, prev_ippt_score
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    credits,
                    xp,
                    "2000-01-01",
                    "Pass",
                    "/static/avatar/default.jpg",
                    "2026-06-01",
                    60,
                ),
            )
            db.commit()
            return user_id

    def login(self, username):
        return self.client.post(
            "/login",
            data={"username": username, "password": "secret"},
            follow_redirects=False,
        )

    def test_public_and_protected_route_smoke(self):
        for route in ["/login", "/register", "/leaderboard"]:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, route)

        for route in ["/home", "/workout", "/profile", "/shop", "/tracker"]:
            response = self.client.get(route, follow_redirects=False)
            self.assertEqual(response.status_code, 302, route)
            self.assertIn("/login", response.headers["Location"])

    def test_tracker_only_shows_current_users_workouts(self):
        alice_id = self.create_user("alice")
        bob_id = self.create_user("bob")

        with self.app.app_context():
            db = get_db()
            db.execute(
                """
                INSERT INTO workout_tracking
                    (user_id, pushup, situp, run, score, date_submitted)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (alice_id, 20, 30, 700, 71, "2026-01-01"),
            )
            db.execute(
                """
                INSERT INTO workout_tracking
                    (user_id, pushup, situp, run, score, date_submitted)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (bob_id, 50, 50, 600, 99, "2026-02-02"),
            )
            db.commit()

        self.login("alice")
        response = self.client.get("/tracker")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"2026-01-01", response.data)
        self.assertNotIn(b"2026-02-02", response.data)

    def test_shop_save_reload_and_home_avatar_use_combination(self):
        self.create_user("shopper")
        self.login("shopper")

        bad_save = self.client.post(
            "/shop/save",
            json={"credits": "bad", "owned_items": [], "equipped_items": []},
        )
        self.assertEqual(bad_save.status_code, 400)

        response = self.client.post(
            "/shop/save",
            json={
                "credits": 777,
                "owned_items": ["headband", "watch", "nikeshirt"],
                "equipped_items": ["headband", "watch", "nikeshirt"],
            },
        )
        expected = "/static/avatar/combinations/headband__watch__nikeshirt.png"

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["avatar_path"], expected)
        self.assertIn(expected.encode(), self.client.get("/shop").data)
        self.assertIn(expected.encode(), self.client.get("/home").data)

        with self.app.app_context():
            db = get_db()
            equipped = [
                row["item_path"]
                for row in db.execute(
                    "SELECT item_path FROM equipped_items ORDER BY item_path"
                ).fetchall()
            ]
        self.assertEqual(equipped, ["headband", "nikeshirt", "watch"])

    def test_expected_avatar_combinations_are_served(self):
        filenames = expected_avatar_filenames()
        self.assertEqual(len(filenames), 47)

        for filename in filenames:
            self.assertTrue(Path("static", filename).exists(), filename)
            response = self.client.get("/static/" + filename)
            try:
                self.assertEqual(response.status_code, 200, filename)
            finally:
                response.close()

    def test_workout_post_uses_configured_ippt_timeout_and_updates_profile(self):
        user_id = self.create_user("runner", credits=0, xp=0)
        self.login("runner")
        captured = {}
        original_fetch = workout_routes.fetch_ippt_score

        def fake_fetch(api_url, timeout, age, situps, pushups, run_seconds):
            captured.update(
                {
                    "api_url": api_url,
                    "timeout": timeout,
                    "age": age,
                    "situps": situps,
                    "pushups": pushups,
                    "run_seconds": run_seconds,
                }
            )
            return 100

        workout_routes.fetch_ippt_score = fake_fetch
        try:
            response = self.client.post(
                "/workout",
                data={
                    "pushups": "40",
                    "situps": "40",
                    "run_min": "10",
                    "run_sec": "30",
                },
                follow_redirects=False,
            )
        finally:
            workout_routes.fetch_ippt_score = original_fetch

        self.assertEqual(response.status_code, 302)
        self.assertEqual(captured["timeout"], 0.25)
        self.assertEqual(captured["run_seconds"], 630)

        with self.app.app_context():
            db = get_db()
            profile = db.execute(
                "SELECT xp, credits FROM profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            workout = db.execute(
                "SELECT pushup, situp, run, score FROM workout_tracking WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        self.assertEqual(dict(profile), {"xp": 100, "credits": 10})
        self.assertEqual(dict(workout), {"pushup": 40, "situp": 40, "run": 630, "score": 100})

    def test_workout_api_failures_return_bad_gateway(self):
        self.create_user("api-failure")
        self.login("api-failure")
        original_fetch = workout_routes.fetch_ippt_score

        def failing_fetch(*args, **kwargs):
            raise IPPTScoreError("Unable to fetch IPPT score")

        workout_routes.fetch_ippt_score = failing_fetch
        try:
            response = self.client.post(
                "/workout",
                data={
                    "pushups": "40",
                    "situps": "40",
                    "run_min": "10",
                    "run_sec": "30",
                },
            )
        finally:
            workout_routes.fetch_ippt_score = original_fetch

        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()
