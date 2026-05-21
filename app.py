import os
import sqlite3
from datetime import datetime
from flask import Flask, redirect, render_template, request, session

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "static/avatars"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

TEST_PRICE = 10


def get_connection():
    return sqlite3.connect("users.db")


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        nickname TEXT,
        avatar TEXT,
        souls INTEGER DEFAULT 100,
        last_result TEXT
    )
    """
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        used INTEGER DEFAULT 0,
        booking_date TEXT
    )
    """
    )
    # Міграції на випадок, якщо таблиці вже створені без цих колонок
    try:
        c.execute("ALTER TABLE users ADD COLUMN last_result TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE services ADD COLUMN used INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE services ADD COLUMN booking_date TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


init_db()


def get_user_by_session():
    if "user" not in session:
        return None
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username=?", (session["user"],)
    ).fetchone()
    conn.close()
    return user


def format_booking_time(raw_time):
    if not raw_time:
        return ""
    dt = datetime.strptime(raw_time, "%Y-%m-%dT%H:%M")
    return dt.strftime("%d.%m.%Y %H:%M")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        c = conn.cursor()
        existing = c.execute(
            "SELECT id FROM users WHERE username=?", (username,)
        ).fetchone()

        if existing:
            conn.close()
            return "Користувач вже існує!"

        c.execute(
            "INSERT INTO users (username, password, nickname, souls) VALUES (?, ?, ?, ?)",
            (username, password, username, 100),
        )
        conn.commit()
        conn.close()

        session["user"] = username
        session["admin"] = username == "Бог" and password == "777"
        return redirect("/profile")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        user = conn.execute(
            "SELECT username FROM users WHERE username=? AND password=?",
            (username, password),
        ).fetchone()
        conn.close()

        if user:
            session["user"] = username
            session["admin"] = username == "Бог" and password == "777"
            return redirect("/profile")
        return "Невірний логін або пароль!"

    return render_template("login.html")


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = get_user_by_session()
    if not user:
        session.clear()
        return redirect("/login")

    conn = get_connection()
    c = conn.cursor()

    if request.method == "POST":
        nickname = request.form["nickname"]
        file = request.files.get("avatar")

        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            c.execute(
                "UPDATE users SET nickname=?, avatar=? WHERE id=?",
                (nickname, filename, user[0]),
            )
        else:
            c.execute(
                "UPDATE users SET nickname=? WHERE id=?", (nickname, user[0])
            )
        conn.commit()
        conn.close()
        return redirect("/profile")

    services = c.execute(
        "SELECT * FROM services WHERE user_id=? AND used=0 AND name NOT LIKE '%Тест%'",
        (user[0],),
    ).fetchall()
    conn.close()

    return render_template("profile.html", user=user, services=services)


@app.route("/services")
def services():
    user = get_user_by_session()
    if not user:
        session.clear()
        return redirect("/login")
    return render_template("services.html", user=user)


# Об'єднали старт і повтор тесту в один економний маршрут
@app.route("/start_test")
@app.route("/repeat_test")
def handle_test_payment():
    user = get_user_by_session()
    if not user:
        session.clear()
        return redirect("/login")

    if user[5] < TEST_PRICE:
        return "Недостатньо душ!"

    conn = get_connection()
    conn.execute(
        "UPDATE users SET souls = souls - ? WHERE id=?", (TEST_PRICE, user[0])
    )
    conn.commit()
    conn.close()
    return redirect("/test")


@app.route("/test")
def test():
    user = get_user_by_session()
    if not user:
        session.clear()
        return redirect("/login")
    return render_template("test.html", user=user, test_price=TEST_PRICE)


@app.route("/save_test_result", methods=["POST"])
def save_test_result():
    if "user" not in session:
        return "Не авторизований", 401

    result = request.form.get("result")
    conn = get_connection()
    conn.execute(
        "UPDATE users SET last_result=? WHERE username=?",
        (result, session["user"]),
    )
    conn.commit()
    conn.close()
    return "OK"


@app.route("/guide", methods=["GET", "POST"])
def guide():
    user = get_user_by_session()
    if not user:
        return redirect("/login")

    if request.method == "POST":
        guide_type = request.form.get("guide_type")
        hours = max(int(request.form.get("hours", 1)), 1)
        booking_time = format_booking_time(request.form.get("booking_time", ""))

        prices = {"basic": 20, "premium": 40}
        titles = {
            "basic": f"Провідник Basic — {hours} год.",
            "premium": f"Провідник Premium — {hours} год.",
        }

        if guide_type not in prices:
            return "Невірний тип провідника!"

        session["pending_service"] = {
            "type": "guide",
            "title": titles[guide_type],
            "price": prices[guide_type] * hours,
            "booking_date": booking_time,
        }
        return redirect("/confirm_service")

    return render_template("guide.html", user=user)


@app.route("/boiler", methods=["GET", "POST"])
def boiler():
    user = get_user_by_session()
    if not user:
        return redirect("/login")

    if request.method == "POST":
        boiler_type = request.form.get("boiler_type")
        days = max(int(request.form.get("days", 1)), 1)
        booking_time = format_booking_time(request.form.get("booking_time", ""))

        prices = {"standard": 30, "vip": 60}
        titles = {
            "standard": f"Котел Standard — {days} дн.",
            "vip": f"Котел VIP — {days} дн.",
        }

        if boiler_type not in prices:
            return "Невірний тип котла!"

        session["pending_service"] = {
            "type": "boiler",
            "title": titles[boiler_type],
            "price": prices[boiler_type] * days,
            "booking_date": booking_time,
        }
        return redirect("/confirm_service")

    return render_template("boiler.html", user=user)


@app.route("/confirm_service", methods=["GET", "POST"])
def confirm_service():
    pending = session.get("pending_service")
    if not pending:
        return redirect("/services")

    user = get_user_by_session()
    if not user:
        session.clear()
        return redirect("/login")

    if request.method == "POST":
        price = pending["price"]
        if user[5] < price:
            return "Недостатньо душ!"

        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE users SET souls = souls - ? WHERE id=?", (price, user[0])
        )
        c.execute(
            "INSERT INTO services (user_id, name, used, booking_date) VALUES (?, ?, ?, ?)",
            (user[0], pending["title"], 0, pending.get("booking_date", "")),
        )
        conn.commit()
        conn.close()

        done_type = pending["type"]
        session.pop("pending_service", None)
        return redirect(f"/success_service?service={done_type}")

    return render_template(
        "confirm_service.html", pending=pending, user=user
    )


@app.route("/success_service")
def success_service():
    if "user" not in session:
        return redirect("/login")
    return render_template(
        "success_service.html", service=request.args.get("service", "")
    )


@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/profile")

    conn = get_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    active_services = conn.execute(
        """
        SELECT services.id, users.id, users.nickname, users.username, services.name, services.booking_date
        FROM services
        JOIN users ON services.user_id = users.id
        WHERE services.used = 0 AND services.name NOT LIKE '%Тест%'
        ORDER BY services.booking_date ASC
    """
    ).fetchall()
    conn.close()

    return render_template(
        "admin.html", users=users, active_services=active_services
    )


@app.route("/use_service/<int:service_id>")
def use_service(service_id):
    if not session.get("admin"):
        return redirect("/profile")

    conn = get_connection()
    conn.execute("UPDATE services SET used = 1 WHERE id=?", (service_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/give/<int:user_id>/<int:amount>")
def give(user_id, amount):
    if not session.get("admin"):
        return redirect("/profile")

    conn = get_connection()
    conn.execute(
        "UPDATE users SET souls = souls + ? WHERE id=?", (amount, user_id)
    )
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)