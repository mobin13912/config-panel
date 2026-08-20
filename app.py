from flask import Flask, redirect, request, session, render_template_string
import sqlite3
import secrets
import hashlib

app = Flask(__name__)

app.secret_key = secrets.token_hex(32)

DATABASE = "users.db"


def init_db():
    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            github_id TEXT UNIQUE,
            github_username TEXT,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def get_user(telegram_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    user = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()

    conn.close()

    return user


@app.route("/")
def home():

    if "telegram_id" not in session:
        return render_template_string("""
        <!DOCTYPE html>
        <html lang="fa">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <title>پنل کانفیگ</title>

            <style>
                body {
                    background:#111827;
                    color:white;
                    font-family:sans-serif;
                    text-align:center;
                    padding:50px 20px;
                }

                .box {
                    max-width:400px;
                    margin:auto;
                    background:#1f2937;
                    padding:30px;
                    border-radius:20px;
                }

                button {
                    width:100%;
                    padding:15px;
                    border:0;
                    border-radius:10px;
                    background:#24292f;
                    color:white;
                    font-size:16px;
                }
            </style>
        </head>

        <body>

        <div class="box">

            <h1>⚙️ پنل کانفیگ اختصاصی</h1>

            <p>برای ورود ابتدا با GitHub ثبت‌نام کنید.</p>

            <button onclick="githubLogin()">
                🐙 ورود با GitHub
            </button>

        </div>

        <script>
        function githubLogin() {
            alert("GitHub Login در مرحله بعد فعال می‌شود.");
        }
        </script>

        </body>
        </html>
        """)

    user = get_user(session["telegram_id"])

    if not user:
        return "کاربر پیدا نشد."

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="fa">

    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">

        <title>پنل کاربری</title>

        <style>

        body {
            background:#0f172a;
            color:white;
            font-family:sans-serif;
            text-align:center;
            padding:30px 15px;
        }

        .box {
            max-width:450px;
            margin:auto;
        }

        .card {
            background:#1e293b;
            padding:20px;
            margin:15px 0;
            border-radius:18px;
        }

        </style>

    </head>

    <body>

        <div class="box">

            <h1>👋 سلام {{ username }}</h1>

            <div class="card">
                👤 حساب GitHub
                <br><br>
                <b>{{ github }}</b>
            </div>

            <div class="card">
                ⚙️ پنل کانفیگ
                <br><br>
                این بخش بعداً ساخته می‌شود.
            </div>

            <div class="card">
                📦 کانفیگ‌های من
                <br><br>
                هنوز کانفیگی ندارید.
            </div>

            <br>

            <a href="/logout" style="color:white;">
                🚪 خروج
            </a>

        </div>

    </body>
    </html>
    """,
    username=user["github_username"],
    github=user["github_username"])


@app.route("/login")
def login():

    telegram_id = request.args.get("telegram_id")

    if not telegram_id:
        return "Telegram ID ارسال نشده است.", 400

    session["telegram_id"] = int(telegram_id)

    return redirect("/")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


@app.route("/github/callback")
def github_callback():

    code = request.args.get("code")

    if not code:
        return "GitHub authorization code دریافت نشد.", 400

    return """
    <h2>GitHub Login</h2>
    <p>کد GitHub دریافت شد ✅</p>
    <p>اتصال واقعی GitHub در مرحله بعد فعال می‌شود.</p>
    """


if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
