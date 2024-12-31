module.exports = {
  apps: [
    {
      name: "socialpulse",
      script: "./dist/index.js",
      instances: "max",
      exec_mode: "cluster",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env_production: {
        NODE_ENV: "production",
        PORT: 5000
      },
      error_file: "/tmp/socialpulse-err.log",
      out_file: "/tmp/socialpulse-out.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      // إعادة التشغيل عند استخدام أكثر من 70% من الذاكرة
      max_memory_restart: "70%",
      // التحقق من صحة التطبيق
      wait_ready: true,
      listen_timeout: 10000,
      // إعادة المحاولة عند الفشل
      restart_delay: 4000,
      // التعامل مع الأخطاء القاتلة
      exp_backoff_restart_delay: 100,
      // مراقبة استخدام الموارد
      monitor: true,
      // مراقبة الأداء
      metrics: {
        http: true
      }
    }
  ]
};
