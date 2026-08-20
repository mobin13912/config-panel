import os
import sqlite3
import secrets

import requests

from flask import (
    Flask,
    redirect,
    request,
    session,
    render_template_string,
    url_for
)

from werkzeug.security import generate_password_hash


app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    secrets.token_hex(32)
)

DATABASE = "users.db"

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            github_id TEXT UNIQUE,
            github_username TEXT,
            github_name TEXT,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_user_by_github(github_id):

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE github_id = ?",
        (github_id,)
    ).fetchone()

    conn.close()

    return user


def create_github_user(github_id, username, name):

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO users
        (github_id, github_username, github_name)
        VALUES (?, ?, ?)
    """, (
        str(github_id),
        username,
        name
    ))

    conn.commit()

    user_id = cursor.lastrowid

    conn.close()

    return user_id


def update_github_user(github_id, username, name):

    conn = get_db()

    conn.execute("""
        UPDATE users
        SET github_username = ?,
            github_name = ?
        WHERE github_id = ?
    """, (
        username,
        name,
        str(github_id)
    ))

    conn.commit()
    conn.close()


@app.route("/")
def home():

    if "user_id" not in session:

        return render_template_string("""
<!DOCTYPE html>
<html lang="fa">
<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>پنل کانفیگ</title>

<style>

body {
    margin:0;
    background:#0f172a;
    color:white;
    font-family:Arial,sans-serif;
}

.container {
    max-width:420px;
    margin:80px auto;
    padding:25px;
}

.card {
    background:#1e293b;
    padding:30px;
    border-radius:20px;
    text-align:center;
}

h1 {
    margin-bottom:10px;
}

button {
    width:100%;
    padding:15px;
    border:0;
    border-radius:12px;
    background:#24292f;
    color:white;
    font-size:16px;
    cursor:pointer;
}

</style>

</head>

<body>

<div class="container">

<div class="card">

<h1>⚙️ پنل کانفیگ</h1>

<p>
برای ورود به پنل با GitHub وارد شوید.
</p>

<a href="/github/login">

<button>
🐙 ورود با GitHub
</button>

</a>

</div>

</div>

</body>
</html>
        """)

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    if not user:
        session.clear()
        return redirect("/")

    if not user["password_hash"]:

        return redirect("/create-password")

    return render_template_string("""
<!DOCTYPE html>

<html lang="fa">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>پنل کاربری</title>

<style>

body {
    margin:0;
    background:#0f172a;
    color:white;
    font-family:Arial,sans-serif;
}

.container {
    max-width:500px;
    margin:40px auto;
    padding:20px;
}

.card {
    background:#1e293b;
    padding:22px;
    border-radius:18px;
    margin-bottom:15px;
}

.button {
    display:block;
    padding:15px;
    margin-top:10px;
    border-radius:12px;
    background:#334155;
    color:white;
    text-decoration:none;
    text-align:center;
}

</style>

</head>

<body>

<div class="container">

<h1>👋 سلام {{ name }}</h1>

<div class="card">

👤 حساب GitHub

<br><br>

<b>@{{ username }}</b>

</div>

<div class="card">

⚙️ پنل کانفیگ

<br><br>

مدیریت کانفیگ‌های شما

</div>

<div class="card">

📦 کانفیگ‌های من

<br><br>

هنوز کانفیگی برای شما ثبت نشده است.

</div>

<a class="button" href="/logout">
🚪 خروج
</a>

</div>

</body>

</html>
    """,
    name=user["github_name"] or user["github_username"],
    username=user["github_username"]
    )


@app.route("/github/login")
def github_login():

    if not GITHUB_CLIENT_ID:

        return "GITHUB_CLIENT_ID تنظیم نشده است.", 500

    state = secrets.token_urlsafe(32)

    session["oauth_state"] = state

    redirect_uri = url_for(
        "github_callback",
        _external=True
    )

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "read:user user:email",
        "state": state
    }

    response = requests.Request(
        "GET",
        GITHUB_AUTHORIZE_URL,
        params=params
    ).prepare()

    return redirect(response.url)


@app.route("/github/callback")
def github_callback():

    code = request.args.get("code")

    state = request.args.get("state")

    if not code:

        return "کد GitHub دریافت نشد.", 400

    if not state:

        return "State دریافت نشد.", 400

    if state != session.get("oauth_state"):

        return "خطای امنیتی OAuth.", 400

    session.pop("oauth_state", None)

    redirect_uri = url_for(
        "github_callback",
        _external=True
    )

    token_response = requests.post(
        GITHUB_TOKEN_URL,
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri
        },
        headers={
            "Accept": "application/json"
        },
        timeout=15
    )

    token_data = token_response.json()

    access_token = token_data.get(
        "access_token"
    )

    if not access_token:

        return "دریافت Access Token از GitHub ناموفق بود.", 400

    user_response = requests.get(
        GITHUB_USER_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json"
        },
        timeout=15
    )

    if user_response.status_code != 200:

        return "دریافت اطلاعات GitHub ناموفق بود.", 400

    github_user = user_response.json()

    github_id = github_user.get("id")

    username = github_user.get("login")

    name = github_user.get("name") or username

    if not github_id or not username:

        return "اطلاعات حساب GitHub ناقص است.", 400

    user = get_user_by_github(github_id)

    if user:

        update_github_user(
            github_id,
            username,
            name
        )

        user = get_user_by_github(github_id)

        session["user_id"] = user["id"]

    else:

        user_id = create_github_user(
            github_id,
            username,
            name
        )

        session["user_id"] = user_id

    return redirect("/")


@app.route("/create-password", methods=["GET", "POST"])
def create_password():

    if "user_id" not in session:

        return redirect("/")

    if request.method == "POST":

        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if len(password) < 6:

            return "رمز عبور باید حداقل ۶ کاراکتر باشد."

        if password != confirm:

            return "رمزها با هم مطابقت ندارند."

        password_hash = generate_password_hash(
            password
        )

        conn = get_db()

        conn.execute("""
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
        """, (
            password_hash,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template_string("""
<!DOCTYPE html>

<html lang="fa">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>ساخت رمز</title>

<style>

body {
    background:#0f172a;
    color:white;
    font-family:Arial,sans-serif;
}

.container {
    max-width:400px;
    margin:60px auto;
    padding:20px;
}

.card {
    background:#1e293b;
    padding:25px;
    border-radius:20px;
}

input {
    width:100%;
    box-sizing:border-box;
    padding:14px;
    margin:8px 0;
    border:0;
    border-radius:10px;
}

button {
    width:100%;
    padding:14px;
    margin-top:10px;
    border:0;
    border-radius:10px;
    background:#2563eb;
    color:white;
    font-size:16px;
}

</style>

</head>

<body>

<div class="container">

<div class="card">

<h2>🔐 ساخت رمز شخصی</h2>

<p>
برای ورودهای بعدی یک رمز حداقل ۶ کاراکتری بسازید.
</p>

<form method="POST">

<input
type="password"
name="password"
placeholder="رمز عبور"
required
>

<input
type="password"
name="confirm"
placeholder="تکرار رمز عبور"
required
>

<button type="submit">
ساخت رمز
</button>

</form>

</div>

</div>

</body>

</html>
    """)


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
