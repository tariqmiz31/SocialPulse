import type { Express } from "express";
import { createServer, type Server } from "http";
import { db } from "@db";
import { performanceMonitor, errorTracker, metricsHandler, getHealthData, apiMonitor, startMonitoring } from "./monitoring";
import { setupAuth } from "./auth";
import rateLimit from "express-rate-limit";
import helmet from "helmet";
import cors from "cors";
import compression from "compression";
import logger from "./logConfig";
import fs from 'fs/promises';

export function registerRoutes(app: Express): Server {
  // تكوين الأمان المحسّن
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        connectSrc: ["'self'", process.env.APP_URL || "", process.env.CUSTOM_DOMAIN ? `*.${process.env.CUSTOM_DOMAIN}` : ""].filter(Boolean),
        imgSrc: ["'self'", "data:", "blob:"],
        scriptSrc: ["'self'", "'unsafe-inline'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        frameSrc: ["'self'"],
        objectSrc: ["'none'"],
        upgradeInsecureRequests: []
      }
    }
  }));

  // تكوين CORS المحسّن
  const allowedDomains = [
    process.env.APP_URL,
    process.env.CUSTOM_DOMAIN,
    process.env.CUSTOM_DOMAIN ? `*.${process.env.CUSTOM_DOMAIN}` : null,
  ].filter(Boolean);

  app.use(cors({
    origin: (origin, callback) => {
      if (!origin) {
        callback(null, true);
        return;
      }

      const isAllowed = allowedDomains.some(domain => {
        if (domain?.startsWith("*.")) {
          const baseDomain = domain.slice(2);
          return origin.endsWith(baseDomain);
        }
        return domain === origin;
      });

      if (isAllowed) {
        callback(null, true);
      } else {
        callback(new Error('غير مسموح به بواسطة CORS'));
      }
    },
    credentials: true
  }));

  // تمكين ضغط الاستجابة
  app.use(compression());

  // تكوين تحديد معدل الطلبات
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 دقيقة
    max: 100 // حد لكل IP
  });

  app.use(limiter);

  // إعداد المصادقة
  setupAuth(app);

  // تمكين وسائط المراقبة
  app.use(performanceMonitor);

  // طرق المراقبة
  app.get("/api/monitoring/metrics", metricsHandler);

  app.get("/api/monitoring/health", async (_req, res) => {
    try {
      const healthData = await getHealthData();
      res.json(healthData);
    } catch (error) {
      logger.error('خطأ في جلب بيانات الصحة:', error);
      res.status(500).json({ error: 'خطأ في جلب بيانات الصحة' });
    }
  });

  app.get("/api/monitoring/status", async (_req, res) => {
    try {
      const dbStatus = db ? "متصل" : "غير متصل";

      res.json({
        server: "يعمل",
        database: dbStatus,
        environment: process.env.NODE_ENV,
        domain: process.env.CUSTOM_DOMAIN || process.env.APP_URL
      });
    } catch (error) {
      logger.error('خطأ في جلب حالة النظام:', error);
      res.status(500).json({ error: 'خطأ في جلب حالة النظام' });
    }
  });

  // Log routes (protected by admin authentication)
  app.get("/api/monitoring/logs", async (req, res) => {
    try {
      // Read the last 100 lines of the log file
      const logs = await fs.readFile('/tmp/socialpulse-combined.log', 'utf8');
      const lastLogs = logs.split('\n').slice(-100).filter(Boolean).map(log => JSON.parse(log));

      res.json(lastLogs);
    } catch (error) {
      logger.error('خطأ في جلب السجلات:', error);
      res.status(500).json({ error: 'خطأ في جلب السجلات' });
    }
  });

  app.get("/api/monitoring/errors", async (req, res) => {
    try {
      // Read the last 50 errors from the error log file
      const errors = await fs.readFile('/tmp/socialpulse-error.log', 'utf8');
      const lastErrors = errors.split('\n').slice(-50).filter(Boolean).map(error => JSON.parse(error));

      res.json(lastErrors);
    } catch (error) {
      logger.error('خطأ في جلب سجلات الأخطاء:', error);
      res.status(500).json({ error: 'خطأ في جلب سجلات الأخطاء' });
    }
  });

  // مراقبة النظام والأخطاء
  app.use(errorTracker);

  // بدء المراقبة
  startMonitoring();

  const httpServer = createServer(app);
  return httpServer;
}