import { Request, Response, NextFunction } from "express";
import { performance } from "perf_hooks";
import winston from 'winston';
import * as promClient from 'prom-client';
import logger from "./logConfig";

// Initialize Prometheus Registry
const register = new promClient.Registry();

// Default metrics
promClient.collectDefaultMetrics({ 
  register,
  prefix: 'socialpulse_',
  labels: { service: 'web' }
});

// Custom metrics
const httpRequestDuration = new promClient.Histogram({
  name: 'socialpulse_http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.3, 0.5, 0.7, 1, 2, 3, 5, 10]
});

const httpRequestTotal = new promClient.Counter({
  name: 'socialpulse_http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});

const apiLatency = new promClient.Histogram({
  name: 'socialpulse_api_latency_seconds',
  help: 'API response time in seconds',
  labelNames: ['api_name'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

const memoryUsage = new promClient.Gauge({
  name: 'socialpulse_memory_usage_bytes',
  help: 'Memory usage in bytes',
  labelNames: ['type']
});

const activeConnections = new promClient.Gauge({
  name: 'socialpulse_active_connections',
  help: 'Number of active connections'
});

register.registerMetric(httpRequestDuration);
register.registerMetric(httpRequestTotal);
register.registerMetric(apiLatency);
register.registerMetric(memoryUsage);
register.registerMetric(activeConnections);

// Performance monitoring middleware
export const performanceMonitor = (req: Request, res: Response, next: NextFunction) => {
  const start = performance.now();
  const path = req.path;

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
      duration: `${duration.toFixed(2)}ms`,
      userAgent: req.get('user-agent'),
      ip: req.ip
    });

    // Track slow requests (more than 1000ms)
    if (duration > 1000) {
      logger.warn({
        message: 'Slow request detected',
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
    query: req.query,
    body: req.body,
    headers: req.headers,
    timestamp
  });

  res.status(500).json({
    error: true,
    message: process.env.NODE_ENV === 'production' 
      ? 'An internal system error occurred' 
      : err.message,
    errorId,
    timestamp
  });
};

// Memory monitoring
const memoryMonitor = () => {
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

  // Run every 5 minutes
  setTimeout(memoryMonitor, 300000);
};

// Health check data collector
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

// Metrics endpoint handler
export const metricsHandler = async (_req: Request, res: Response) => {
  try {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (error) {
    logger.error('Error fetching metrics:', error);
    res.status(500).end(error);
  }
};

// API request counter
let requestCount = 0;
export const requestCounter = (req: Request, res: Response, next: NextFunction) => {
  requestCount++;
  if (requestCount % 100 === 0) {
    logger.info(`[Stats] Total requests processed: ${requestCount}`);
  }
  next();
};

// API monitor
export const apiMonitor = (apiName: string) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    const start = performance.now();

    res.on('finish', () => {
      const duration = performance.now() - start;
      apiLatency.labels(apiName).observe(duration / 1000);

      if (duration > 2000) { // Warning for requests taking more than 2 seconds
        logger.warn({
          message: 'Slow API request',
          api: apiName,
          duration: `${duration.toFixed(2)}ms`
        });
      }
    });

    next();
  };
};

// Start monitoring
export const startMonitoring = () => {
  memoryMonitor();
  logger.info('Monitoring system started');
};