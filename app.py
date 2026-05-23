import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key-afterlife-123")

# Глобальне підключення до бази в пам'яті
_SHARED_CONN = sqlite3.connect(":memory:", check_same_thread=False)

def get_connection():
    """Повертає підключення, ГАРАНТОВАНО створюючи таблиці чіткої структури."""
    conn = _SHARED_CONN
    c = conn.cursor()
    
    # Створюємо таблиці з фіксованим порядком колонок під твої шаблони
    # u[0]=id, u[1]=username, u[2]=password, u[3]=nickname, u[4]=avatar, u[5]=souls, u[6]=last_result
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            nickname TEXT,
            avatar TEXT DEFAULT 'default.png',
            souls INTEGER DEFAULT 100,
            last_result TEXT DEFAULT ''
        )
    ''')
    
    # s[0]=id, s[1]=user_id, s[2]=name, s[3]=used, s[4]=booking_date
    c.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            used INTEGER DEFAULT 0,
            booking_date TEXT
        )
    ''')
    
    # Автоматично додаємо тестових користувачів, якщо таблиця порожня
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT OR IGNORE INTO users (id, username, password, nickname, avatar, souls, last_result) VALUES (1, 'Admin', 'admin123', 'Адміністратор', 'default.png', 500, '')")
        c.execute("INSERT OR IGNORE INTO users (id, username, password, nickname, avatar, souls, last_result) VALUES (2, 'User', 'user123', 'Грішник', 'default.png', 100, '')")
    conn.commit()
    return conn

@app.route('/')
def index():
    get_connection()
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
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_result=? WHERE id=?", (result_text, user_id))
        conn.commit()
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

            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT souls FROM users WHERE id=?", (session['user_id'],))
            row = c.fetchone()
            user_souls = row[0] if row else 100
            
            if user_souls >= total_cost:
                new_souls = user_souls - total_cost
                c.execute("UPDATE users SET souls=? WHERE id=?", (new_souls, session['user_id']))
                c.execute("INSERT INTO services (user_id, name, booking_date) VALUES (?, ?, ?)",
                          (session['user_id'], service_title, formatted_date))
                conn.commit()
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

            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT souls FROM users WHERE id=?", (session['user_id'],))
            row = c.fetchone()
            user_souls = row[0] if row else 100
            
            if user_souls >= total_cost:
                new_souls = user_souls - total_cost
                c.execute("UPDATE users SET souls=? WHERE id=?", (new_souls, session['user_id']))
                c.execute("INSERT INTO services (user_id, name, booking_date) VALUES (?, ?, ?)",
                          (session['user_id'], service_title, formatted_date))
                conn.commit()
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
        
    conn = get_connection()
    c = conn.cursor()
    # Вибираємо користувачів з потрібним для admin.html набором індексів
    c.execute("SELECT id, username, password, nickname, avatar, souls FROM users")
    users = c.fetchall()
    
    users_data = []
    for u in users:
        # Для сумісності з логікою твого admin.html, де послуги перебираються всередині картки юзера
        # Створюємо розширений кортеж, де s[1]=user_id, s[4]=назва, s[5]=дата
        c.execute("SELECT id, user_id, used, used, name, booking_date FROM services WHERE user_id=? AND used=0", (u[0],))
        srv = c.fetchall()
        users_data.append({'info': u, 'services': srv})
        
    return render_template('admin.html', users_data=users_data)

@app.route('/give/<int:user_id>/<int:amount>')
def give_souls(user_id, amount):
    if 'user_id' not in session or not session.get('admin'):
        return "Немає прав", 403
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET souls = souls + ? WHERE id = ?", (amount, user_id))
    conn.commit()
    return redirect(url_for('admin'))

@app.route('/use_service/<int:service_id>')
def use_service(service_id):
    if 'user_id' not in session or not session.get('admin'):
        return "Немає прав", 403
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE services SET used = 1 WHERE id = ?", (service_id,))
    conn.commit()
    return redirect(url_for('admin'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Фікс під register.html: поле нікнейму береться з input name="email"
        email_field = request.form.get('email')
        
        if not username or not password:
            return "Будь ласка, заповніть логін та пароль!"
            
        nickname = email_field if email_field and email_field.strip() != "" else username
            
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, nickname, avatar, souls, last_result) VALUES (?, ?, ?, 'default.png', 100, '')",
                      (username.strip(), password.strip(), nickname.strip()))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Користувач з таким логіном вже існує в Книзі Доль!"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, username, password, nickname, avatar, souls, last_result FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        
        if user:
            session.clear()  
            session['user_id'] = user[0]
            session['username'] = user[1]
            
            if user[1].lower() in ['god', 'admin']:
                session['admin'] = True
                
            return redirect(url_for('profile'))
        else:
            return "Невірний логін або пароль грішника! Спробуйте ще раз або зареєструйтесь."
    return render_template('login.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_connection()
    c = conn.cursor()
    
    if request.method == 'POST':
        new_nickname = request.form.get('nickname')
        if new_nickname:
            c.execute("UPDATE users SET nickname=? WHERE id=?", (new_nickname, session['user_id']))
            conn.commit()
            
    # Вибираємо чіткий порядок полів, який вимагає твій profile.html (наприклад, user[3] — це nickname)
    c.execute("SELECT id, username, password, nickname, avatar, souls, last_result FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Вибірка послуг під індекси у твоїй таблиці профілю (s[2] — назва послуги, s[4] — дата)
    c.execute("SELECT id, user_id, name, used, booking_date FROM services WHERE user_id=?", (session['user_id'],))
    user_services = c.fetchall()
    
    return render_template('profile.html', user=user, services=user_services)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
