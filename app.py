import os
import sqlite3
from datetime import datetime
from flask import Flask, redirect, render_template, request, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key-afterlife-123")


def get_connection():
    return sqlite3.connect("/tmp/users.db")


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
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
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/guide")
def guide():
    return render_template("guide.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        nickname = request.form.get("nickname")
        avatar = request.form.get("avatar", "default.png")

        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (username, password, nickname, avatar) VALUES (?, ?, ?, ?)",
                (username, password, nickname, avatar),
            )
            conn.commit()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return "Коривувач з таким логіном вже існує в Книзі Доль!"
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password),
        )
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            if user[1] == "God" or user[1] == "Admin":
                session["admin"] = True
            return redirect("/profile")
        else:
            return "Невірний логін або пароль грішника! Спробуйте ще раз."

    return render_template("login.html")


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    c = conn.cursor()

    if request.method == "POST":
        new_avatar = request.form.get("avatar")
        new_nickname = request.form.get("nickname")

        if new_avatar:
            c.execute(
                "UPDATE users SET avatar=? WHERE id=?",
                (new_avatar, session["user_id"]),
            )
        if new_nickname:
            c.execute(
                "UPDATE users SET nickname=? WHERE id=?",
                (new_nickname, session["user_id"]),
            )
        conn.commit()

    c.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))
    user = c.fetchone()

    c.execute("SELECT * FROM services WHERE user_id=?", (session["user_id"],))
    user_services = c.fetchall()
    conn.close()

    return render_template("profile.html", user=user, services=user_services)


@app.route("/test", methods=["GET", "POST"])
def test():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        score = 0
        for i in range(1, 6):
            answer = request.form.get(f"q{i}")
            if answer == "bad":
                score += 20
            elif answer == "neutral":
                score += 10

        result = "Рай" if score < 40 else "Пекло"

        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE users SET last_result=? WHERE id=?",
            (result, session["user_id"]),
        )
        conn.commit()
        conn.close()

        return render_template("test.html", result=result, submitted=True)

    return render_template("test.html", submitted=False)


# ОНОВЛЕНО: Додали підтримку POST про всяк випадок
@app.route("/services", methods=["GET", "POST"])
def services():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("services.html")


# ОНОВЛЕНО: Додали підтримку GET про всяк випадок
@app.route("/book_service", methods=["GET", "POST"])
def book_service():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        service_name = request.form.get("service_name")
        cost = int(request.form.get("cost", 0))

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT souls FROM users WHERE id=?", (session["user_id"],))
        user_souls = c.fetchone()[0]

        if user_souls >= cost:
            new_souls = user_souls - cost
            c.execute(
                "UPDATE users SET souls=? WHERE id=?",
                (new_souls, session["user_id"]),
            )
            c.execute(
                "INSERT INTO services (user_id, name, booking_date) VALUES (?, ?, ?)",
                (
                    session["user_id"],
                    service_name,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                ),
            )
            conn.commit()
            conn.close()
            return render_template(
                "success_service.html", service_name=service_name
            )
        else:
            conn.close()
            return "У вас недостатньо душ для купівлі цієї індульгенції чи послуги!"

    return redirect("/services")


@app.route("/admin")
def admin():
    if not session.get("admin"):
        return "Доступ закритий! Сюди пускають тільки Бога або Адміна.", 403

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, nickname, souls, last_result FROM users")
    all_users = c.fetchall()

    c.execute(
        """
        SELECT services.id, users.username, services.name, services.used, services.booking_date 
        FROM services 
        JOIN users ON services.user_id = users.id 
        WHERE services.used = 0
    """
    )
    pending_services = c.fetchall()
    conn.close()

    return render_template(
        "admin.html", users=all_users, services=pending_services
    )


@app.route("/use_service/<int:service_id>")
def use_service(service_id):
    if not session.get("admin"):
        return redirect("/profile")

    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE services SET used = 1 WHERE id=?", (service_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/give/<int:user_id>/<int:amount>")
def give(user_id, amount):
    if not session.get("admin"):
        return redirect("/profile")

    conn = get_connection()
    c = conn.cursor()
    c.execute(
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
