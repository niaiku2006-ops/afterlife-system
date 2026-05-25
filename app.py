import os
import sqlite3
import base64
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key-afterlife-123")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

_SHARED_CONN = sqlite3.connect(":memory:", check_same_thread=False)

def get_connection():
    conn = _SHARED_CONN
    c = conn.cursor()
    
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
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            used INTEGER DEFAULT 0,
            booking_date TEXT
        )
    ''')
    
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
        
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT souls FROM users WHERE id=?", (session['user_id'],))
    row = c.fetchone()
    user_souls = row[0] if row else 0
    
    return render_template('test.html', user_souls=user_souls)

@app.route('/save_test_result', methods=['POST'])
def save_test_result():
    if 'user_id' not in session:
        return "Потрібна авторизація", 401
    
    user_id = session['user_id']
    result_text = request.form.get('result', 'Невідомий результат')
    test_cost = 50
    
    try:
        conn = get_connection()
        c = conn.cursor()
        
        c.execute("SELECT souls FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
        user_souls = row[0] if row else 0
        
        if user_souls >= test_cost:
            new_souls = user_souls - test_cost
            c.execute("UPDATE users SET souls=?, last_result=? WHERE id=?", (new_souls, result_text, user_id))
            conn.commit()
            return f"Результат збережено! З вашого рахунку списано {test_cost} душ. 😈"
        else:
            return "У вас недостатньо душ, щоб дізнатися свою долю! Проходження тесту коштує 50 душ. 💀", 403
            
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
            service_title = f"Провідник {guide_type.upper()} ({hours} god.)"
            
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
    
    c.execute("SELECT id, username, password, nickname, avatar, souls, last_result FROM users")
    users = c.fetchall()
    
    c.execute("SELECT id, user_id, name, used, booking_date FROM services WHERE used=0")
    active_services = c.fetchall()
    
    return render_template('admin.html', users=users, active_services=active_services)

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
        nickname = request.form.get('nickname')
        
        if not username or not password:
            return "Будь ласка, заповніть логін та пароль!"
            
        final_nickname = nickname if nickname and nickname.strip() != "" else username
        random_souls = random.randint(6, 777)
            
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, nickname, avatar, souls, last_result) VALUES (?, ?, ?, 'default.png', ?, '')",
                      (username.strip(), password.strip(), final_nickname.strip(), random_souls))
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
        try:
            new_nickname = request.form.get('nickname')
            if new_nickname:
                c.execute("UPDATE users SET nickname=? WHERE id=?", (new_nickname, session['user_id']))
                conn.commit()
                
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename != '' and allowed_file(file.filename):
                    file_bytes = file.read()
                    encoded_string = base64.b64encode(file_bytes).decode('utf-8')
                    mime_type = file.mimetype
                    avatar_data = f"data:{mime_type};base64,{encoded_string}"
                    
                    c.execute("UPDATE users SET avatar=? WHERE id=?", (avatar_data, session['user_id']))
                    conn.commit()
        except Exception as e:
            return f"Помилка при збереженні профілю: {e}", 500
            
    c.execute("SELECT id, username, password, nickname, avatar, souls, last_result FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    c.execute("SELECT id, user_id, name, used, booking_date FROM services WHERE user_id=?", (session['user_id'],))
    user_services = c.fetchall()
    
    return render_template('profile.html', user=user, services=user_services)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
