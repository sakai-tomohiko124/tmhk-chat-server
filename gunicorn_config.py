# Gunicorn Configuration File

# Server socket (use UNIX domain socket for Nginx proxy)
# Absolute path to avoid cwd issues
bind = "/home/ubuntu/tmhk-chat-server/chat.sock"

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
# Ensure socket permissions: user ubuntu, group www-data, mask 007
umask = 0o007
user = "ubuntu"
group = "www-data"
tmp_upload_dir = None
preload_app = True  # Preload app to save memory across workers

# SSL (if needed in future)
# keyfile = None
# certfile = None
