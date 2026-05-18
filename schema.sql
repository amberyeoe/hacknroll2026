CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

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
);

CREATE TABLE IF NOT EXISTS workout_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    pushup INTEGER,
    situp INTEGER,
    run INTEGER,
    score INTEGER,
    date_submitted DATE,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS owned_items (
    user_id INTEGER,
    item_path TEXT,
    PRIMARY KEY (user_id, item_path),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS equipped_items (
    user_id INTEGER,
    item_path TEXT,
    PRIMARY KEY (user_id, item_path),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_workout_tracking_user_date
    ON workout_tracking (user_id, date_submitted);

CREATE INDEX IF NOT EXISTS idx_profiles_xp
    ON profiles (xp DESC);
