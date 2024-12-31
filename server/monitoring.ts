import { Request, Response, NextFunction } from "express";
import { performance } from "perf_hooks";
import winston from 'winston';
import * as promClient from 'prom-client';
import { log } from "./vite";

// Initialize Winston logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: '/tmp/socialpulse-error.log', level: 'error' }),
    new winston.transports.File({ filename: '/tmp/socialpulse.log' })
  ]
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}

// Initialize Prometheus metrics
const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

// Custom metrics
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

const httpRequestTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});

register.registerMetric(httpRequestDuration);
register.registerMetric(httpRequestTotal);

// Performance monitoring middleware
export const performanceMonitor = (req: Request, res: Response, next: NextFunction) => {
  const start = performance.now();
  const path = req.path;

  // Track response time
  res.on('finish', () => {
    const duration = performance.now() - start;
    const status = res.statusCode;

    // Update Prometheus metrics
    httpRequestDuration.labels(req.method, path, status.toString()).observe(duration / 1000);
    httpRequestTotal.labels(req.method, path, status.toString()).inc();

    // Log request details
    logger.info({
      method: req.method,
      path: path,
      status: status,
      duration: `${duration.toFixed(2)}ms`
    });

    // Track slow requests (over 1000ms)
    if (duration > 1000) {
      logger.warn({
        message: 'Slow request detected',
        method: req.method,
        path: path,
        duration: `${duration.toFixed(2)}ms`
      });
    }
  });

  next();
};

// Error tracking middleware
export const errorTracker = (err: Error, req: Request, res: Response, next: NextFunction) => {
  const timestamp = new Date().toISOString();
  const errorId = Math.random().toString(36).substring(7);

  logger.error({
    errorId,
    message: err.message,
    stack: err.stack,
    method: req.method,
    path: req.path,
    timestamp
  });

  res.status(500).json({
    error: true,
    message: process.env.NODE_ENV === 'production'
      ? 'حدث خطأ في النظام'
      : err.message,
    errorId,
    timestamp
  });
};

// Memory usage monitor
export const memoryMonitor = () => {
  const used = process.memoryUsage();
  const memoryGauge = new promClient.Gauge({
    name: 'node_memory_usage_bytes',
    help: 'Memory usage in bytes',
    labelNames: ['type']
  });

  memoryGauge.labels('rss').set(used.rss);
  memoryGauge.labels('heapTotal').set(used.heapTotal);
  memoryGauge.labels('heapUsed').set(used.heapUsed);

  logger.info({
    memory: {
      rss: `${Math.round(used.rss / 1024 / 1024)}MB`,
      heapTotal: `${Math.round(used.heapTotal / 1024 / 1024)}MB`,
      heapUsed: `${Math.round(used.heapUsed / 1024 / 1024)}MB`
    }
  });
};

// Health check data collector
export const getHealthData = async () => {
  const metrics = await register.getMetricsAsJSON();
  const uptime = process.uptime();
  const memory = process.memoryUsage();

  return {
    status: 'healthy',
    uptime,
    uptimeFormatted: `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`,
    memory: {
      rss: `${Math.round(memory.rss / 1024 / 1024)}MB`,
      heapTotal: `${Math.round(memory.heapTotal / 1024 / 1024)}MB`,
      heapUsed: `${Math.round(memory.heapUsed / 1024 / 1024)}MB`
    },
    metrics,
    timestamp: new Date().toISOString()
  };
};

// Metrics endpoint handler
export const metricsHandler = async (_req: Request, res: Response) => {
  try {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (error) {
    res.status(500).end(error);
  }
};

// API request counter
let requestCount = 0;
export const requestCounter = (req: Request, res: Response, next: NextFunction) => {
  requestCount++;
  if (requestCount % 100 === 0) {
    logger.info(`[STATS] Total requests processed: ${requestCount}`);
  }
  next();
};