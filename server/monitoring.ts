import { Request, Response, NextFunction } from "express";
import { performance } from "perf_hooks";
import winston from 'winston';
import * as promClient from 'prom-client';
import logger from "./logConfig";
import fs from 'fs/promises';
import path from 'path';

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
      duration: `${duration.toFixed(2)}ms`
    });

    // Track slow requests
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
export const errorTracker = (err: Error, _req: Request, res: Response, next: NextFunction) => {
  logger.error({
    message: err.message,
    stack: err.stack,
    timestamp: new Date().toISOString()
  });

  next(err);
};

// Memory monitoring
const memoryMonitor = () => {
  const used = process.memoryUsage();
  memoryUsage.labels('rss').set(used.rss);
  memoryUsage.labels('heapTotal').set(used.heapTotal);
  memoryUsage.labels('heapUsed').set(used.heapUsed);
  memoryUsage.labels('external').set(used.external || 0);
  memoryUsage.labels('arrayBuffers').set(used.arrayBuffers || 0);

  // Run every minute
  setTimeout(memoryMonitor, 60000);
};

// API monitor middleware
export const apiMonitor = (req: Request, res: Response, next: NextFunction) => {
  const start = performance.now();

  res.on('finish', () => {
    const duration = performance.now() - start;
    apiLatency.labels(req.path).observe(duration / 1000);
  });

  next();
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

// Health check data collector
export const getHealthData = async () => {
  const metrics = await register.getMetricsAsJSON();
  const uptime = process.uptime();
  const memory = process.memoryUsage();

  return {
    status: 'healthy',
    uptime,
    memory: {
      rss: Math.round(memory.rss / 1024 / 1024),
      heapTotal: Math.round(memory.heapTotal / 1024 / 1024),
      heapUsed: Math.round(memory.heapUsed / 1024 / 1024)
    },
    metrics,
    timestamp: new Date().toISOString()
  };
};

// Start monitoring
export const startMonitoring = () => {
  memoryMonitor();
  logger.info('Monitoring system started');
};