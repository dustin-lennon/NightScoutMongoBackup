// PM2 ecosystem configuration for production and development

const path = require('path');

module.exports = {
  apps: [
    {
      name: 'nightscout-backup-bot',
      script: 'poetry',
      args: 'run nightscout-backup-bot',
      cwd: path.resolve(__dirname),
      exec_mode: 'fork',
      interpreter: '/bin/sh',
      instances: 1,
      autorestart: true,
      watch: ['src/'],
      max_memory_restart: '500M',
      error_file: './logs/error.log',
      out_file: './logs/output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      env: {
        NODE_ENV: 'development',
        // Add other development environment variables here
      },
      env_production: {
        NODE_ENV: 'production',
        // Add other production environment variables here
      }
    }
  ]
};
