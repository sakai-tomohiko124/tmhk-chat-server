#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/ubuntu/tmhk-chat-server"
SOCKET_PATH="$APP_DIR/chat.sock"
SERVICE_NAME="tmhk-chat"
SITE_PATH="/etc/nginx/sites-available/tmhk-chat"

sudo apt-get update -y
sudo apt-get install -y nginx

# Ensure permissions
sudo mkdir -p "$APP_DIR/logs"
sudo chown -R ubuntu:www-data "$APP_DIR"
sudo chmod -R 775 "$APP_DIR"

# Nginx site
sudo bash -c "cat > $SITE_PATH" <<'NGINX'
server {
    listen 80 default_server;
    server_name tmhk-chat.ddns.net _;

    location /static/ {
        alias /home/ubuntu/tmhk-chat-server/static/;
        expires 7d;
        access_log off;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/tmhk-chat-server/chat.sock;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
    }
}
NGINX

sudo ln -sf "$SITE_PATH" /etc/nginx/sites-enabled/tmhk-chat
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# systemd service for gunicorn
sudo bash -c "cat > /etc/systemd/system/${SERVICE_NAME}.service" <<SYSTEMD
[Unit]
Description=Gunicorn for TMHK Chat Server
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn_config.py app:app
Restart=always
TimeoutSec=300

[Install]
WantedBy=multi-user.target
SYSTEMD

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

# Verify
systemctl --no-pager --full status ${SERVICE_NAME} || true
ss -lntp | grep ':80 ' || true
curl -sI http://127.0.0.1/ | head -n 1 || true

echo "Setup complete. Access via http://tmhk-chat.ddns.net/"
