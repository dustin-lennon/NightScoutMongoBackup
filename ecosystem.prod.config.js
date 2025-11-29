// PM2 ecosystem configuration for production
//
// You have two options for running the API server:
//
// Option 1: Run API in the same process as the bot (recommended for simplicity)
//   - Set ENABLE_API_IN_BOT=true in your .env file
//   - Only start the 'nightscout-backup-bot' process
//   - The API will run in a background thread
//
// Option 2: Run API as a separate process (recommended for production)
//   - Set ENABLE_API_IN_BOT=false (or omit it)
//   - Start both 'nightscout-backup-bot' and 'nightscout-backup-api' processes
//   - Better isolation and independent scaling

const path = require('path');

module.exports = {
  apps: [
    {
      name: 'nightscout-backup-bot',
      script: 'poetry',
      args: 'run nightscout-backup-bot',
      cwd: path.resolve(__dirname),
      exec_mode: 'fork',
      interpreter: 'none',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: './logs/error.log',
      out_file: './logs/output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      env: {
        NODE_ENV: 'production',
        ENABLE_API_IN_BOT: 'false',  // Uncomment and set to 'true' to enable
      }
    },
    // Only include this if ENABLE_API_IN_BOT=false (API as separate process)
    {
      name: 'nightscout-backup-api',
      script: 'poetry',
      args: 'run nightscout-backup-api',
      cwd: path.resolve(__dirname),
      exec_mode: 'fork',
      interpreter: 'none',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: './logs/api-error.log',
      out_file: './logs/api-output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      env: {
        NODE_ENV: 'production',
      }
    }
  ]
};
