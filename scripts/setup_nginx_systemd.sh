#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/ubuntu/tmhk-chat-server"
SOCKET_PATH="$APP_DIR/chat.sock"
SERVICE_NAME="tmhk-chat"
SITE_PATH="/etc/nginx/sites-available/tmhk-chat"

# Base packages
sudo apt-get update -y
sudo apt-get install -y nginx git python3-venv python3-pip

# Ensure application directory exists and owned by ubuntu
sudo mkdir -p "$APP_DIR"
sudo chown -R ubuntu:www-data "$APP_DIR"

# Fetch or update repository
if [ ! -d "$APP_DIR/.git" ]; then
    sudo -u ubuntu git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git "$APP_DIR"
else
    sudo -u ubuntu bash -lc "cd '$APP_DIR' && git fetch origin && git reset --hard origin/main"
fi

# Python venv and dependencies
if [ ! -d "$APP_DIR/venv" ]; then
    sudo -u ubuntu python3 -m venv "$APP_DIR/venv"
fi
sudo -u ubuntu bash -lc "source '$APP_DIR/venv/bin/activate' && pip install --upgrade pip && pip install -r '$APP_DIR/requirements.txt'"

# Ensure permissions
sudo mkdir -p "$APP_DIR/logs"
sudo chmod -R 775 "$APP_DIR"

# Nginx site (with WebSocket upgrade headers)
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
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection "upgrade";
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
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn_config.py wsgi:app
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
