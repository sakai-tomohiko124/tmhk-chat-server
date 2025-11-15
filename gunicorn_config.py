# Gunicorn Configuration File

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
workers = 2  # Reduced from 3 to save memory
worker_class = "sync"
worker_connections = 100  # Limit concurrent connections per worker
max_requests = 1000  # Restart workers after 1000 requests to prevent memory leaks
max_requests_jitter = 50  # Add jitter to prevent all workers restarting simultaneously

# Timeout settings
timeout = 0  # No timeout (infinite)
graceful_timeout = 30  # Reduced from 120 to speed up worker restarts
keepalive = 2  # Reduced from 5 to free connections faster

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Process naming
proc_name = "tmhk-chat-server"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None
preload_app = True  # Preload app to save memory across workers

# SSL (if needed in future)
# keyfile = None
# certfile = None
