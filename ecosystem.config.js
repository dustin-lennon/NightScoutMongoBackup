// PM2 ecosystem configuration for production and development

const path = require('path');

module.exports = {
  apps: [
    {
      // Development Config
      name: 'nightscout-backup-bot-dev',
      script: 'poetry',
      args: 'run nightscout-backup-bot',
      cwd: path.resolve(__dirname),
      exec_mode: 'fork',
      interpreter: '/bin/sh',
      instances: 1,
      autorestart: true,
      watch: ['src/'],
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'development',
      },
      error_file: './logs/error.log',
      out_file: './logs/output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
    },
    {
      // Production Config
      name: 'nightscout-backup-bot-prod',
      script: 'poetry',
      args: 'run nightscout-backup-bot',
      cwd: '~/NightScoutMongoBackup',
      exec_mode: 'fork',
      interpreter: '/bin/sh',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
      },
      error_file: './logs/error.log',
      out_file: './logs/output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
    },
  ],
};
