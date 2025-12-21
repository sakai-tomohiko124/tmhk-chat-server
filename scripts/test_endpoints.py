import requests

paths = ['http://127.0.0.1:5000/', 'http://127.0.0.1:5000/chat']
for p in paths:
    try:
        r = requests.get(p, timeout=5)
        print(f'{p} -> {r.status_code}')
    except Exception as e:
        print(f'{p} -> ERROR: {e}')
