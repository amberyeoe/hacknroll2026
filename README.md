# Hacknroll 2026

Flask app for IPPT tracking, gamified XP, leaderboard ranking, and avatar cosmetics.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m flask --app app run
```

The app creates the SQLite schema from `schema.sql` automatically on startup.
Runtime database files such as `database.db` are ignored by Git.

## Configuration

Optional environment variables:

- `SECRET_KEY`: Flask session secret. Set this outside code for deployed apps.
- `DATABASE`: SQLite database path. Defaults to `database.db`.
- `HOST`: Flask run host. Defaults to `0.0.0.0`.
- `PORT`: Flask run port. Defaults to `5000`.
- `FLASK_DEBUG`: Set to `1` for local debug mode.
- `IPPT_API_URL`: IPPT score API URL.
- `IPPT_API_TIMEOUT`: IPPT API timeout in seconds. Defaults to `5.0`.
- `WORKOUT_TEST_SECONDS`: push-up and sit-up timer length. Defaults to `60`.

## Checks

```powershell
.\venv\Scripts\python.exe -m compileall app.py auth.py config.py db.py ippt.py shop_items.py routes scripts tests
.\venv\Scripts\python.exe -m unittest discover
```

## Asset Scripts

Regenerate avatar combination images:

```powershell
.\venv\Scripts\python.exe scripts\generate_avatar_combinations.py
```

Optimize static images:

```powershell
.\venv\Scripts\python.exe scripts\optimize_images.py
```
