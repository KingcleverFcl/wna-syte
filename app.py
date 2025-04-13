import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']  # Получаем из Railway Variables

def get_db_connection():
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        port=os.environ.get('DB_PORT', '5432')
    )

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
            flash('Generation error, please try again', 'error')
        finally:
            if conn: conn.close()
    
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    code = (request.form.get('code') or '')[:64]
    if len(code) != 64:
        flash('Code must be 64 characters', 'error')
        return redirect(url_for('index'))
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM codes WHERE code = %s', (code,))
            if cur.fetchone():
                return render_template('success.html', code=code)
        flash('Invalid code', 'error')
    finally:
        if conn: conn.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
