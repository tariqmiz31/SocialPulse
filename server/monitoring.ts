import { Request, Response, NextFunction } from "express";
import { performance } from "perf_hooks";
import { log } from "./vite";

// Performance monitoring middleware
export const performanceMonitor = (req: Request, res: Response, next: NextFunction) => {
  const start = performance.now();
  const path = req.path;
  
  // Track response time
  res.on('finish', () => {
    const duration = performance.now() - start;
    const status = res.statusCode;
    
    log(`[PERF] ${req.method} ${path} ${status} - ${duration.toFixed(2)}ms`, 'monitor');
    
    // Track slow requests (over 1000ms)
    if (duration > 1000) {
      log(`[WARN] Slow request: ${req.method} ${path} took ${duration.toFixed(2)}ms`, 'monitor');
    }
  });

  next();
};

// Error tracking middleware
export const errorTracker = (err: Error, req: Request, res: Response, next: NextFunction) => {
  const timestamp = new Date().toISOString();
  const errorId = Math.random().toString(36).substring(7);
  
  // Log detailed error information
  log(`[ERROR] ${errorId} at ${timestamp}`, 'monitor');
  log(`Path: ${req.method} ${req.path}`, 'monitor');
  log(`Error: ${err.message}`, 'monitor');
  log(`Stack: ${err.stack}`, 'monitor');
  
  // Send error response
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
  
  log(`[MEMORY] RSS: ${Math.round(used.rss / 1024 / 1024)}MB`, 'monitor');
  log(`[MEMORY] Heap Total: ${Math.round(used.heapTotal / 1024 / 1024)}MB`, 'monitor');
  log(`[MEMORY] Heap Used: ${Math.round(used.heapUsed / 1024 / 1024)}MB`, 'monitor');
  
  // Alert if memory usage is high (>80% of available memory)
  const memoryLimit = process.env.MEMORY_LIMIT_MB ? parseInt(process.env.MEMORY_LIMIT_MB) : 512;
  if (used.heapUsed / 1024 / 1024 > memoryLimit * 0.8) {
    log(`[ALERT] High memory usage detected!`, 'monitor');
  }
};

// API request counter
let requestCount = 0;
export const requestCounter = (req: Request, res: Response, next: NextFunction) => {
  requestCount++;
  if (requestCount % 100 === 0) {
    log(`[STATS] Total requests processed: ${requestCount}`, 'monitor');
  }
  next();
};

// Health check data collector
export const getHealthData = () => {
  const uptime = process.uptime();
  const memory = process.memoryUsage();
  
  return {
    status: 'healthy',
    uptime: uptime,
    uptimeFormatted: `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`,
    memory: {
      rss: `${Math.round(memory.rss / 1024 / 1024)}MB`,
      heapTotal: `${Math.round(memory.heapTotal / 1024 / 1024)}MB`,
      heapUsed: `${Math.round(memory.heapUsed / 1024 / 1024)}MB`
    },
    timestamp: new Date().toISOString(),
    requestCount
  };
};
