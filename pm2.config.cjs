module.exports = {
  apps: [
    {
      name: "silvarium-social",
      script: "server/start_production.py",
      interpreter: "python3",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env_production: {
        NODE_ENV: "production",
        PORT: 3000,
        APP_URL: process.env.APP_URL || "https://silvariumsocial.com",
        CUSTOM_DOMAIN: process.env.CUSTOM_DOMAIN,
        DATABASE_URL: process.env.DATABASE_URL,
        PGHOST: process.env.PGHOST,
        PGPORT: process.env.PGPORT,
        PGUSER: process.env.PGUSER,
        PGPASSWORD: process.env.PGPASSWORD,
        PGDATABASE: process.env.PGDATABASE
      },
      env_development: {
        NODE_ENV: "development",
        PORT: 3000
      },
      error_file: "/tmp/silvarium-err.log",
      out_file: "/tmp/silvarium-out.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      listen_timeout: 10000,
      kill_timeout: 5000,
      wait_ready: true,
      max_restarts: 10,
      restart_delay: 4000,
      exp_backoff_restart_delay: 100
    }
  ]
};