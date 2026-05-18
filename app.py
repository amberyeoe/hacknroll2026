from flask import Flask

from auth import init_login, register_auth_routes
from config import default_config, is_debug_enabled
from db import init_app as init_db_app
from db import init_db
from routes.main_routes import register_main_routes
from routes.shop_routes import register_shop_routes
from routes.workout_routes import register_workout_routes


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(default_config())

    if test_config:
        app.config.update(test_config)

    init_db_app(app)
    init_login(app)
    register_main_routes(app)
    register_auth_routes(app)
    register_shop_routes(app)
    register_workout_routes(app)

    with app.app_context():
        init_db()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=is_debug_enabled(),
    )
