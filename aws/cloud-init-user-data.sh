#cloud-config
package_update: true
package_upgrade: true
packages:
  - git
  - nginx
  - python3-venv
  - python3-pip
runcmd:
  - set -xe
  - sudo -u ubuntu bash -lc "if [ ! -d ~/tmhk-chat-server ]; then git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git ~/tmhk-chat-server; fi"
  - sudo -u ubuntu bash -lc "cd ~/tmhk-chat-server && git fetch origin && git reset --hard origin/main"
  - bash -lc "cd /home/ubuntu/tmhk-chat-server && scripts/setup_nginx_systemd.sh"
  - systemctl enable tmhk-chat
  - systemctl restart tmhk-chat
  - systemctl status tmhk-chat --no-pager || true
  - nginx -t && systemctl reload nginx
write_files:
  - path: /etc/motd
    content: |
      TMHK Chat Server: cloud-init bootstrap complete.
      Use: systemctl status tmhk-chat
