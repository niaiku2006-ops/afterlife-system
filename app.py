import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key-afterlife-123")

DB_PATH = "afterlife.db"

def get_db():
    """Створює або повертає існуюче з'єднання з БД для поточного запиту."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row  # Тепер дані доступні за назвами колонок!
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Автоматично закриває з'єднання з БД після завершення запиту."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Ініціалізація бази даних: створюється один раз при запуску додатка."""
    with app.app_context():
        db = get_db()
        c = db.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                nickname TEXT,
                avatar TEXT,
                souls INTEGER DEFAULT 100,
                last_result TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                used INTEGER DEFAULT 0,
                booking_date TEXT
            )
        ''')
        
        # Додаємо тестових користувачів, якщо порожньо
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO users (id, username, password, nickname, avatar, souls) VALUES (1, 'Admin', 'admin123', 'Адміністратор', 'default.png', 500)")
            c.execute("INSERT INTO users (id, username, password, nickname, avatar, souls) VALUES (2, 'User', 'user123', 'Грішник', 'default.png', 100)")
        db.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('services.html')

@app.route('/test')
def test():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('test.html')

@app.route('/save_test_result', methods=['POST'])
def save_test_result():
    if 'user_id' not in session:
        return "Потрібна авторизація", 401
    
    user_id = session['user_id']
    result_text = request.form.get('result', 'Невідомий результат')
    
    try:
        db = get_db()
        c = db.cursor()
        c.execute("UPDATE users SET last_result=? WHERE id=?", (result_text, user_id))
        db.commit()
        return "Успішно збережено!"
    except Exception as e:
        return f"Помилка збереження тесту: {e}", 500

@app.route('/boiler', methods=['GET', 'POST'])
def boiler():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        try:
            boiler_type = request.form.get('boiler_type', 'standard')
            days = int(request.form.get('days', 1))
            booking_time = request.form.get('booking_time', '')
            
            cost_per_day = 30 if boiler_type == 'standard' else 60
            total_cost = cost_per_day * days
            service_title = f"Котел {boiler_type.upper()} ({days} дн.)"
            
            try:
                dt = datetime.strptime(booking_time, "%Y-%m-%dT%H:%M")
                formatted_date = dt.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = booking_time

            db = get_db()
            c = db.cursor()
            c.execute("SELECT souls FROM users WHERE id=?", (session['user_id'],))
            row = c.fetchone()
            user_souls = row['souls'] if row else 100
            
            if user_souls >= total_cost:
                new_souls = user_souls - total_cost
                c.execute("UPDATE users SET souls=? WHERE id=?", (new_souls, session['user_id']))
                c.execute("INSERT INTO services (user_id, name, booking_date) VALUES (?, ?, ?)",
                          (session['user_id'], service_title, formatted_date))
                db.commit()
                return render_template('success_service.html', service_name=service_title)
            else:
                return "У вас недостатньо душ для оренди цього котла! 💀"
        except Exception as e:
            return f"Помилка при бронюванні котла: {e}", 500
            
    return render_template('boiler.html')

@app.route('/guide', methods=['GET', 'POST'])
def guide():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        try:
            guide_type = request.form.get('guide_type', 'basic')
            hours = int(request.form.get('hours', 1))
            booking_time = request.form.get('booking_time', '')
            
            cost_per_hour = 20 if guide_type == 'basic' else 40
            total_cost = cost_per_hour * hours
            service_title = f"Провідник {guide_type.upper()} ({hours} год.)"
            
            try:
                dt = datetime.strptime(booking_time, "%Y-%m-%dT%H:%M")
                formatted_date = dt.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = booking_time

            db = get_db()
            c = db.cursor()
            c.execute("SELECT souls FROM users WHERE id=?", (session['user_id'],))
            row = c.fetchone()
            user_souls = row['souls'] if row else 100
            
            if user_souls >= total_cost:
                new_souls = user_souls - total_cost
                c.execute("UPDATE users SET souls=? WHERE id=?", (new_souls, session['user_id']))
                c.execute("INSERT INTO services (user_id, name, booking_date) VALUES (?, ?, ?)",
                          (session['user_id'], service_title, formatted_date))
                db.commit()
                return render_template('success_service.html', service_name=service_title)
            else:
                return "У вас недостатньо душ для найму провідника! 💀"
        except Exception as e:
            return f"Помилка при наймі провідника: {e}", 500
            
    return render_template('guide.html')

@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('admin'):
        return "Доступ заборонено! Ви не маєте божественних прав. ❌", 403
        
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, username, nickname, avatar, souls, last_result FROM users")
    users = c.fetchall()
    
    users_data = []
    for u in users:
        c.execute("SELECT id, name, used, booking_date FROM services WHERE user_id=?", (u['id'],))
        srv = c.fetchall()
        users_data.append({'info': u, 'services': srv})
    return render_template('admin.html', users_data=users_data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nickname = request.form.get('nickname')
        
        if not username or not password:
            return "Будь ласка, заповніть логін та пароль!"
            
        db = get_db()
        c = db.cursor()
        try:
            c.execute("INSERT INTO users (username, password, nickname, avatar) VALUES (?, ?, ?, 'default.png')",
                      (username, password, nickname if nickname else username))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Користувач з таким логіном вже існує в Книзі Доль!"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        
        if user:
            session.clear()  
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            if user['username'].lower() in ['god', 'admin']:
                session['admin'] = True
                
            return redirect(url_for('profile'))
        else:
            return "Невірний логін або пароль грішника! Спробуйте ще раз або зареєструйтесь."
    return render_template('login.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    c = db.cursor()
    
    if request.method == 'POST':
        new_nickname = request.form.get('nickname')
        if new_nickname:
            c.execute("UPDATE users SET nickname=? WHERE id=?", (new_nickname, session['user_id']))
            db.commit()
            
    c.execute("SELECT * FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    c.execute("SELECT * FROM services WHERE user_id=?", (session['user_id'],))
    user_services = c.fetchall()
    
    return render_template('profile.html', user=user, services=user_services)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()  # Ініціалізуємо базу один раз перед стартом сервера
    app.run(debug=True)
