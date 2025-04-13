import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2 import OperationalError, errors

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-key')

class Database:
    @staticmethod
    def get_connection():
        try:
            conn = psycopg2.connect(
                host=os.environ['DB_HOST'],
                database=os.environ['DB_NAME'],
                user=os.environ['DB_USER'],
                password=os.environ['DB_PASSWORD'],
                port=os.environ.get('DB_PORT', '5432')
            )
            return conn
        except OperationalError as e:
            print(f"Database connection failed: {e}")
            raise

    @staticmethod
    def initialize():
        conn = None
        try:
            conn = Database.get_connection()
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS codes (
                        id SERIAL PRIMARY KEY,
                        code VARCHAR(64) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
                print("Database table 'codes' initialized")
        except Exception as e:
            print(f"Database initialization error: {e}")
            raise
        finally:
            if conn: conn.close()

def generate_code(length=64):
    chars = string.ascii_uppercase + string.digits + '-_='
    return ''.join(random.SystemRandom().choice(chars) for _ in range(length))

@app.before_first_request
def before_first_request():
    Database.initialize()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST' and 'generate' in request.form:
        code = generate_code()
        conn = None
        try:
            conn = Database.get_connection()
            with conn.cursor() as cur:
                cur.execute('INSERT INTO codes (code) VALUES (%s)', (code,))
                conn.commit()
                return render_template('index.html', code=code)
        except errors.UniqueViolation:
            if conn: conn.rollback()
            flash('Код уже существует, попробуйте снова', 'error')
        except errors.UndefinedTable:
            if conn: conn.rollback()
            Database.initialize()
            flash('Системная ошибка, попробуйте снова', 'error')
        except Exception as e:
            if conn: conn.rollback()
            print(f"Error generating code: {e}")
            flash('Ошибка генерации кода', 'error')
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
        conn = Database.get_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM codes WHERE code = %s', (code,))
            if cur.fetchone():
                return render_template('success.html', code=code)
        flash('Неверный код', 'error')
    except Exception as e:
        print(f"Login error: {e}")
        flash('Ошибка проверки кода', 'error')
    finally:
        if conn: conn.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    Database.initialize()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
