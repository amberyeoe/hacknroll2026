# HACKNROLL2026

A Flask fitness web app for tracking IPPT-style workouts, earning XP and credits, buying avatar items, and comparing progress on a leaderboard.

## Features

- User registration, login, logout, and profile setup
- Dashboard with latest workout metrics, XP, level progress, credits, avatar, and IPPT badge status
- Workout logging for push-ups, sit-ups, and 2.4 km run timing
- Workout tracker chart data
- Shop system with credits, owned items, and equipped avatar items
- Avatar item combinations for accessories and one active top item
- Leaderboard ordered by user XP

## Tech Stack

- Python
- Flask
- Flask-Login
- SQLite
- Jinja templates
- Bootstrap and custom CSS
- Pillow for avatar image generation

## Project Structure

```text
.
|-- app.py
|-- requirements.txt
|-- scripts/
|   `-- generate_avatar_combinations.py
|-- static/
|   |-- avatar/
|   |-- css/
|   `-- images/
`-- templates/
```

## Local Setup

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Set a Flask secret key for local development:

```powershell
$env:FLASK_SECRET_KEY = "replace-this-with-a-long-random-value"
```

Run the app:

```powershell
python app.py
```

The app runs at:

```text
http://127.0.0.1:5000
```

## Database

The app uses SQLite through `database.db`.

`database.db` is intentionally ignored by Git because it contains local runtime data such as users, password hashes, profiles, XP, credits, workout records, owned items, and equipped items.

When the app starts, it creates the required tables automatically if they do not already exist.

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `FLASK_SECRET_KEY` | Secret used by Flask to sign session cookies. Set this in deployment instead of committing a value into the repo. |

If `FLASK_SECRET_KEY` is not set, the app generates a temporary random key at startup. That is convenient for local testing, but a fixed secret should be configured in production so user sessions remain valid across restarts.

## Avatar Assets

The avatar shop uses pre-rendered image combinations stored in:

```text
static/avatar/combinations/
```

To regenerate those combinations after editing avatar source images, run:

```powershell
python scripts/generate_avatar_combinations.py
```

## Security Notes

- Do not commit `.env` files.
- Do not commit `database.db`.
- Set `FLASK_SECRET_KEY` in the deployment environment.
- Treat password hashes and user data as sensitive even when passwords are not stored in plain text.
