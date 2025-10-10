/**
 * ARE - PM2 Configuration for AWS EC2
 * Python Flask + Gunicorn用のPM2設定
 */

module.exports = {
  apps: [
    {
      name: 'are-backend',
      script: '/home/ubuntu/are-backend/venv/bin/gunicorn',
      args: '-c gunicorn_config.py wsgi:app',
      cwd: '/home/ubuntu/are-backend/ARE/backend',
      interpreter: 'none',  // Python仮想環境を直接使用
      instances: 1,
      exec_mode: 'fork',
      watch: false,  // 本番環境ではfalse推奨
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      max_memory_restart: '1G',
      env: {
        FLASK_ENV: 'production',
        PORT: 5000,
        NODE_ENV: 'production'
      },
      env_development: {
        FLASK_ENV: 'development',
        PORT: 5000,
        NODE_ENV: 'development'
      },
      error_file: 'logs/pm2_error.log',
      out_file: 'logs/pm2_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      time: true
    }
  ]
};
