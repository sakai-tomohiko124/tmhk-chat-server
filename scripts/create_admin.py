from dotenv import load_dotenv
import os
import sqlite3
from werkzeug.security import generate_password_hash

load_dotenv()
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL') or ''
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD') or ''

# strip surrounding quotes if present
if ADMIN_EMAIL.startswith('"') and ADMIN_EMAIL.endswith('"'):
    ADMIN_EMAIL = ADMIN_EMAIL[1:-1]
if ADMIN_EMAIL.startswith("'") and ADMIN_EMAIL.endswith("'"):
    ADMIN_EMAIL = ADMIN_EMAIL[1:-1]
if ADMIN_PASSWORD.startswith('"') and ADMIN_PASSWORD.endswith('"'):
    ADMIN_PASSWORD = ADMIN_PASSWORD[1:-1]
if ADMIN_PASSWORD.startswith("'") and ADMIN_PASSWORD.endswith("'"):
    ADMIN_PASSWORD = ADMIN_PASSWORD[1:-1]

if not ADMIN_EMAIL or not ADMIN_PASSWORD:
    print('ADMIN_EMAIL or ADMIN_PASSWORD not set in .env')
    exit(1)

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'chat.db'))
print('Using DB:', db_path)

if not os.path.exists(db_path):
    print(f'Database not found: {db_path}')
    print('Please run: flask init-db')
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    # check if admin exists
    c.execute('SELECT id FROM users WHERE email = ?', (ADMIN_EMAIL,))
    if c.fetchone():
        print(f'Admin already exists for {ADMIN_EMAIL}')
    else:
        hashed = generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256')
        username = ADMIN_EMAIL.split('@')[0]
        c.execute(
            'INSERT INTO users (username, email, password, is_admin, status) VALUES (?, ?, ?, ?, ?)',
            (username, ADMIN_EMAIL, hashed, 1, 'active')
        )
        conn.commit()
        print(f'Admin created: {ADMIN_EMAIL}')
except Exception as e:
    print(f'ERROR: {e}')
finally:
    conn.close()
