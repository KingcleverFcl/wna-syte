import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2 import OperationalError

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-key')

# Конфигурация подключения к БД
def get_db_config():
    return {
        'host': os.environ.get('DB_HOST'),
        'database': os.environ.get('DB_NAME'),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'port': os.environ.get('DB_PORT', '5432')
    }

def get_db_connection():
    try:
        return psycopg2.connect(**get_db_config())
    except OperationalError as e:
        print(f"Database connection error: {e}")
        raise

def init_db():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS codes (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(64) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise
    finally:
        if conn: conn.close()

def generate_code(length=64):
    chars = string.ascii_uppercase + string.digits + '-_='
    return ''.join(random.SystemRandom().choice(chars) for _ in range(length))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST' and 'generate' in request.form:
        code = generate_code()
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute('INSERT INTO codes (code) VALUES (%s)', (code,))
                conn.commit()
            return render_template('index.html', code=code)
        except psycopg2.IntegrityError:
            if conn: conn.rollback()
            flash('Ошибка генерации, попробуйте снова', 'error')
        finally:
            if conn: conn.close()
    
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    code = request.form.get('code', '')[:64]
    if len(code) != 64:
        flash('Код должен содержать 64 символа', 'error')
        return redirect(url_for('index'))
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM codes WHERE code = %s', (code,))
            if cur.fetchone():
                return render_template('success.html', code=code)
        flash('Неверный код', 'error')
    finally:
        if conn: conn.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
