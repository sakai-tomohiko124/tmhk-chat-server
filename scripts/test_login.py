import requests
from dotenv import load_dotenv
import os

load_dotenv()
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', '')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

if ADMIN_EMAIL.startswith('"') and ADMIN_EMAIL.endswith('"'):
    ADMIN_EMAIL = ADMIN_EMAIL[1:-1]
if ADMIN_PASSWORD.startswith('"') and ADMIN_PASSWORD.endswith('"'):
    ADMIN_PASSWORD = ADMIN_PASSWORD[1:-1]

s = requests.Session()
base = 'http://127.0.0.1:5000'

print(f'Testing login for {ADMIN_EMAIL}')

# GET login page to establish any cookies
r = s.get(base + '/')
print(f'/ GET -> {r.status_code}')

# POST credentials
payload = {
    'username': ADMIN_EMAIL.split('@')[0],
}

r2 = s.post(base + '/', data=payload, allow_redirects=True)
print(f'/ POST -> {r2.status_code}')
print(f'Final URL after POST: {r2.url}')

# Try to access /chat
r3 = s.get(base + '/chat')
print(f'/chat GET -> {r3.status_code}')

# Check if username appears in response
if ADMIN_EMAIL.split('@')[0] in r3.text:
    print('Login appears successful (username in /chat)')
else:
    print('Login may have failed (username not found in /chat)')
    snippet = r3.text[:500]
    print(f'Snippet of /chat response:\n{snippet}')
