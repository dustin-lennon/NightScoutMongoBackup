// PM2 ecosystem configuration for development

const path = require('path');

module.exports = {
  apps: [
    {
      name: 'nightscout-backup-bot',
    //   script: 'poetry',
      script: 'launcher.ts',
    //   args: 'run nightscout-backup-bot',
      cwd: path.resolve(__dirname),
      exec_mode: 'fork',
    //   interpreter: '/bin/sh',
      interpreter: 'bun',
      watch: ['src/', 'launcher.ts'],
	  ignore_watch: ["node_modules"],
      instances: 1,
      autorestart: true,
      max_memory_restart: '500M',
      error_file: './logs/error.log',
      out_file: './logs/output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      env: {
        NODE_ENV: 'development',
        // Add other development environment variables here
      }
    }
  ]
};
