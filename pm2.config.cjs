module.exports = {
  apps: [
    {
      name: "socialpulse",
      script: "./dist/index.js",
      instances: "max",
      exec_mode: "cluster",
      autorestart: true,
      watch: false,
      max_memory_restart: "1024M",
      env_production: {
        NODE_ENV: "production",
        PORT: 5000,
        APP_URL: process.env.APP_URL || "https://silvariumsocial.com",
        CUSTOM_DOMAIN: process.env.CUSTOM_DOMAIN,
        DATABASE_URL: process.env.DATABASE_URL
      },
      env_development: {
        NODE_ENV: "development",
        PORT: 5000
      },
      error_file: "/tmp/socialpulse-err.log",
      out_file: "/tmp/socialpulse-out.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      listen_timeout: 10000,
      restart_delay: 4000,
      exp_backoff_restart_delay: 100,
      monitor: true,
      metrics: {
        http: true
      },
      backup: {
        enabled: true,
        path: "/tmp/backups",
        interval: "0 4 * * *"
      }
    }
  ]
};