import { Request, Response, NextFunction } from "express";
import { performance } from "perf_hooks";
import winston from 'winston';
import * as promClient from 'prom-client';
import { log } from "./vite";

// تكوين Winston logger مع تنسيق محسن
const logger = winston.createLogger({
  level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
  format: winston.format.combine(
    winston.format.timestamp({
      format: 'YYYY-MM-DD HH:mm:ss'
    }),
    winston.format.errors({ stack: true }),
    winston.format.splat(),
    winston.format.json()
  ),
  defaultMeta: { service: 'socialpulse' },
  transports: [
    new winston.transports.File({ 
      filename: '/tmp/socialpulse-error.log',
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    }),
    new winston.transports.File({ 
      filename: '/tmp/socialpulse-combined.log',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    })
  ]
});

// إضافة تسجيل في وحدة التحكم في بيئة التطوير
if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.simple()
    )
  }));
}

// تهيئة مقاييس Prometheus
const register = new promClient.Registry();

// المقاييس الافتراضية للنظام
promClient.collectDefaultMetrics({ 
  register,
  prefix: 'socialpulse_',
  labels: { service: 'web' }
});

// مقاييس مخصصة
const httpRequestDuration = new promClient.Histogram({
  name: 'socialpulse_http_request_duration_seconds',
  help: 'مدة طلبات HTTP بالثواني',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.3, 0.5, 0.7, 1, 2, 3, 5, 10]
});

const httpRequestTotal = new promClient.Counter({
  name: 'socialpulse_http_requests_total',
  help: 'إجمالي عدد طلبات HTTP',
  labelNames: ['method', 'route', 'status_code']
});

const apiLatency = new promClient.Histogram({
  name: 'socialpulse_api_latency_seconds',
  help: 'زمن استجابة API بالثواني',
  labelNames: ['api_name'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

const memoryUsage = new promClient.Gauge({
  name: 'socialpulse_memory_usage_bytes',
  help: 'استخدام الذاكرة بالبايت',
  labelNames: ['type']
});

const activeConnections = new promClient.Gauge({
  name: 'socialpulse_active_connections',
  help: 'عدد الاتصالات النشطة'
});

register.registerMetric(httpRequestDuration);
register.registerMetric(httpRequestTotal);
register.registerMetric(apiLatency);
register.registerMetric(memoryUsage);
register.registerMetric(activeConnections);

// وسيط مراقبة الأداء
export const performanceMonitor = (req: Request, res: Response, next: NextFunction) => {
  const start = performance.now();
  const path = req.path;

  // تتبع وقت الاستجابة
  res.on('finish', () => {
    const duration = performance.now() - start;
    const status = res.statusCode;

    // تحديث مقاييس Prometheus
    httpRequestDuration.labels(req.method, path, status.toString()).observe(duration / 1000);
    httpRequestTotal.labels(req.method, path, status.toString()).inc();

    // تسجيل تفاصيل الطلب
    logger.info({
      method: req.method,
      path: path,
      status: status,
      duration: `${duration.toFixed(2)}ms`,
      userAgent: req.get('user-agent'),
      ip: req.ip
    });

    // تتبع الطلبات البطيئة (أكثر من 1000ms)
    if (duration > 1000) {
      logger.warn({
        message: 'تم اكتشاف طلب بطيء',
        method: req.method,
        path: path,
        duration: `${duration.toFixed(2)}ms`,
        query: req.query,
        headers: req.headers
      });
    }
  });

  next();
};

// وسيط تتبع الأخطاء
export const errorTracker = (err: Error, req: Request, res: Response, next: NextFunction) => {
  const timestamp = new Date().toISOString();
  const errorId = Math.random().toString(36).substring(7);

  logger.error({
    errorId,
    message: err.message,
    stack: err.stack,
    method: req.method,
    path: req.path,
    query: req.query,
    body: req.body,
    headers: req.headers,
    timestamp
  });

  // إرسال رد مناسب للعميل
  res.status(500).json({
    error: true,
    message: process.env.NODE_ENV === 'production'
      ? 'حدث خطأ في النظام'
      : err.message,
    errorId,
    timestamp
  });
};

// مراقبة استخدام الذاكرة
export const memoryMonitor = () => {
  const used = process.memoryUsage();

  memoryUsage.labels('rss').set(used.rss);
  memoryUsage.labels('heapTotal').set(used.heapTotal);
  memoryUsage.labels('heapUsed').set(used.heapUsed);
  memoryUsage.labels('external').set(used.external || 0);
  memoryUsage.labels('arrayBuffers').set(used.arrayBuffers || 0);

  logger.debug({
    memory: {
      rss: `${Math.round(used.rss / 1024 / 1024)}MB`,
      heapTotal: `${Math.round(used.heapTotal / 1024 / 1024)}MB`,
      heapUsed: `${Math.round(used.heapUsed / 1024 / 1024)}MB`,
      external: `${Math.round((used.external || 0) / 1024 / 1024)}MB`,
      arrayBuffers: `${Math.round((used.arrayBuffers || 0) / 1024 / 1024)}MB`
    }
  });

  // تشغيل كل 5 دقائق
  setTimeout(memoryMonitor, 300000);
};

// جامع بيانات فحص الصحة
export const getHealthData = async () => {
  const metrics = await register.getMetricsAsJSON();
  const uptime = process.uptime();
  const memory = process.memoryUsage();
  const loadavg = require('os').loadavg();

  return {
    status: 'healthy',
    uptime,
    uptimeFormatted: `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`,
    memory: {
      rss: `${Math.round(memory.rss / 1024 / 1024)}MB`,
      heapTotal: `${Math.round(memory.heapTotal / 1024 / 1024)}MB`,
      heapUsed: `${Math.round(memory.heapUsed / 1024 / 1024)}MB`,
      external: `${Math.round((memory.external || 0) / 1024 / 1024)}MB`,
      arrayBuffers: `${Math.round((memory.arrayBuffers || 0) / 1024 / 1024)}MB`
    },
    loadAverage: {
      '1m': loadavg[0],
      '5m': loadavg[1],
      '15m': loadavg[2]
    },
    metrics,
    timestamp: new Date().toISOString()
  };
};

// معالج نقطة نهاية المقاييس
export const metricsHandler = async (_req: Request, res: Response) => {
  try {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (error) {
    logger.error('خطأ في جلب المقاييس:', error);
    res.status(500).end(error);
  }
};

// عداد طلبات API
let requestCount = 0;
export const requestCounter = (req: Request, res: Response, next: NextFunction) => {
  requestCount++;
  if (requestCount % 100 === 0) {
    logger.info(`[إحصائيات] إجمالي الطلبات المعالجة: ${requestCount}`);
  }
  next();
};

// مراقب API
export const apiMonitor = (apiName: string) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    const start = performance.now();

    res.on('finish', () => {
      const duration = performance.now() - start;
      apiLatency.labels(apiName).observe(duration / 1000);

      if (duration > 2000) { // تحذير للطلبات التي تستغرق أكثر من 2 ثوانٍ
        logger.warn({
          message: 'طلب API بطيء',
          api: apiName,
          duration: `${duration.toFixed(2)}ms`
        });
      }
    });

    next();
  };
};

// بدء المراقبة
export const startMonitoring = () => {
  memoryMonitor();
  logger.info('تم بدء نظام المراقبة');
};