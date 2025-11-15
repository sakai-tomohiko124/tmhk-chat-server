/**
 * PM2 Ecosystem Configuration for TMHKchat
 * 
 * このファイルはPM2プロセスマネージャーの設定を定義します。
 * 本番環境でGunicornを使用してFlaskアプリケーションを管理します。
 * 
 * 使用方法:
 *   pm2 start ecosystem.config.js --env production
 *   pm2 restart tmhk-chat
 *   pm2 stop tmhk-chat
 *   pm2 logs tmhk-chat
 *   pm2 monit
 */

module.exports = {
  apps: [
    {
      name: 'tmhk-chat',
      script: '/home/ubuntu/tmhk-chat-server/venv/bin/gunicorn',
      args: '--workers 3 --bind unix:chat.sock -m 007 wsgi:app --timeout 120 --log-level info --access-logfile logs/access.log --error-logfile logs/error.log',
      cwd: '/home/ubuntu/tmhk-chat-server',
      interpreter: 'none', // Gunicornは既にPython実行ファイル
      
      // 環境変数
      env_production: {
        FLASK_ENV: 'production',
        FLASK_APP: 'app.py',
        PYTHONUNBUFFERED: '1',
        PATH: '/home/ubuntu/tmhk-chat-server/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
      },
      
      env_development: {
        FLASK_ENV: 'development',
        FLASK_APP: 'app.py',
        FLASK_DEBUG: '1',
        PYTHONUNBUFFERED: '1',
        PATH: '/home/ubuntu/tmhk-chat-server/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
      },
      
      // プロセス管理設定
      instances: 1, // Gunicornが既にワーカーを管理
      exec_mode: 'fork',
      autorestart: true,
      watch: false, // 本番環境ではwatchを無効化
      max_memory_restart: '1G',
      
      // ログ設定
      error_file: '/home/ubuntu/tmhk-chat-server/logs/pm2-error.log',
      out_file: '/home/ubuntu/tmhk-chat-server/logs/pm2-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      
      // 再起動設定
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 4000,
      
      // クラッシュ時の設定
      kill_timeout: 5000,
      wait_ready: false,
      listen_timeout: 3000,
      
      // その他の設定
      vizion: true,
      post_update: ['npm install', 'echo "Application updated"'],
      
      // 環境変数ファイル
      env_file: '/home/ubuntu/tmhk-chat-server/.env'
    },
    
    // オプション: Socket.IOワーカー専用プロセス（必要に応じて有効化）
    /*
    {
      name: 'tmhk-chat-socketio',
      script: '/home/ubuntu/tmhk-chat-server/venv/bin/python',
      args: '-m socketio.server wsgi:socketio --host 0.0.0.0 --port 5001',
      cwd: '/home/ubuntu/tmhk-chat-server',
      interpreter: 'none',
      
      env_production: {
        FLASK_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        PATH: '/home/ubuntu/tmhk-chat-server/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
      },
      
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      
      error_file: '/home/ubuntu/tmhk-chat-server/logs/socketio-error.log',
      out_file: '/home/ubuntu/tmhk-chat-server/logs/socketio-out.log'
    }
    */
  ],
  
  // デプロイ設定
  deploy: {
    production: {
      user: 'ubuntu',
      host: '52.69.241.31',
      ref: 'origin/main',
      repo: 'git@github.com:sakai-tomohiko124/tmhk-chat-server.git',
      path: '/home/ubuntu/tmhk-chat-server',
      'post-deploy': 'source venv/bin/activate && pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': 'sudo apt-get update && sudo apt-get install -y python3-pip python3-venv git',
      ssh_options: 'StrictHostKeyChecking=no',
      key: '/path/to/tmhk-chat.pem'
    }
  }
};
