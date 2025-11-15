# Gunicorn Configuration File

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
workers = 3
worker_class = "sync"

# Timeout settings
timeout = 0  # No timeout (infinite)
graceful_timeout = 120
keepalive = 5

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

# SSL (if needed in future)
# keyfile = None
# certfile = None
