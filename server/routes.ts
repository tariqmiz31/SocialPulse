import type { Express } from "express";
import { createServer, type Server } from "http";
import { db } from "@db";
import { performanceMonitor, errorTracker, metricsHandler, getHealthData, apiMonitor } from "./monitoring";
import { setupAuth } from "./auth";
import { createBackup, restoreBackup, scheduleBackups } from "./backup";
import rateLimit from "express-rate-limit";
import helmet from "helmet";
import cors from "cors";
import compression from "compression";
import logger from "./logConfig";

export function registerRoutes(app: Express): Server {
  // تكوين الأمان المحسّن
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        connectSrc: ["'self'", process.env.APP_URL || ""],
        scriptSrc: ["'self'", "'unsafe-inline'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        fontSrc: ["'self'"],
        imgSrc: ["'self'", "data:", "blob:"],
        frameSrc: ["'self'"],
        objectSrc: ["'none'"],
        upgradeInsecureRequests: []
      }
    }
  }));

  // تكوين CORS
  app.use(cors({
    origin: process.env.APP_URL,
    credentials: true
  }));

  // تمكين ضغط الاستجابة
  app.use(compression());

  // تكوين تحديد معدل الطلبات
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    skip: (req) => {
      const userAgent = req.headers['user-agent'] || '';
      return userAgent.includes('CloudFront') || userAgent.includes('Cloudflare');
    }
  });

  app.use(limiter);

  // إعداد المصادقة
  setupAuth(app);

  // تمكين وسائط المراقبة
  app.use(performanceMonitor);

  // نقطة نهاية الحالة الأساسية
  app.get("/api/monitoring/status", (_req, res) => {
    try {
      res.json({
        server: "running",
        timestamp: new Date().toISOString(),
        environment: process.env.NODE_ENV,
        database: "connected"
      });
    } catch (error) {
      logger.error('Error in status endpoint:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });

  // نقاط نهاية المراقبة المتقدمة
  app.get("/api/monitoring/metrics", metricsHandler);
  app.get("/api/monitoring/health", async (_req, res) => {
    try {
      const healthData = await getHealthData();
      res.json(healthData);
    } catch (error) {
      logger.error('Error in health endpoint:', error);
      res.status(500).json({ error: 'Failed to get health data' });
    }
  });

  // مراقبة النظام والأخطاء
  app.use(errorTracker);
  app.use(apiMonitor);

  const httpServer = createServer(app);
  return httpServer;
}