import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'chat.db')
db_path = os.path.abspath(db_path)
print('Using DB:', db_path)

if not os.path.exists(db_path):
    print(f'Database file not found: {db_path}')
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()
try:
    c.execute("SELECT id, username, email, is_admin, status FROM users")
    rows = c.fetchall()
    if not rows:
        print('No users found in users table')
    else:
        print('Users:')
        for r in rows:
            print(r)
except Exception as e:
    print('ERROR querying users table:', e)
finally:
    conn.close()
