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
import fs from 'fs/promises';
import path from 'path';
import express from 'express';

export function registerRoutes(app: Express): Server {
  // تكوين الأمان المحسّن مع دعم CDN
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        connectSrc: ["'self'", process.env.APP_URL || "", process.env.CUSTOM_DOMAIN ? `*.${process.env.CUSTOM_DOMAIN}` : ""].filter(Boolean),
        imgSrc: ["'self'", "data:", "blob:", "*.${process.env.CUSTOM_DOMAIN}", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
        scriptSrc: ["'self'", "'unsafe-inline'", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
        styleSrc: ["'self'", "'unsafe-inline'", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
        fontSrc: ["'self'", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
        mediaSrc: ["'self'", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
        frameSrc: ["'self'"],
        objectSrc: ["'none'"],
        upgradeInsecureRequests: []
      }
    }
  }));

  // تكوين CORS المحسّن مع دعم CDN
  const allowedDomains = [
    process.env.APP_URL,
    process.env.CUSTOM_DOMAIN,
    process.env.CUSTOM_DOMAIN ? `*.${process.env.CUSTOM_DOMAIN}` : null,
    process.env.CUSTOM_DOMAIN ? `cdn.${process.env.CUSTOM_DOMAIN}` : null
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
        callback(new Error('Not allowed by CORS'));
      }
    },
    credentials: true,
    maxAge: 86400
  }));

  // تمكين ضغط الاستجابة مع إعدادات CDN
  app.use(compression({
    level: 6,
    threshold: 1024,
    filter: (req, res) => {
      const userAgent = req.headers['user-agent'] || '';
      if (userAgent.includes('CloudFront') || userAgent.includes('Cloudflare')) {
        return false;
      }
      return compression.filter(req, res);
    }
  }));

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

  // تكوين التخزين المؤقت للملفات الثابتة
  app.use('/static', express.static('public', {
    maxAge: '1y',
    etag: true,
    lastModified: true
  }));

  // نقاط نهاية إدارة النسخ الاحتياطي
  app.post("/api/backup/create", async (req, res) => {
    try {
      logger.info('بدء عملية النسخ الاحتياطي...');
      const result = await createBackup();
      logger.info('تم إنشاء النسخة الاحتياطية بنجاح:', result);
      res.json(result);
    } catch (error) {
      logger.error('خطأ في إنشاء النسخة الاحتياطية:', error);
      res.status(500).json({ error: 'فشل إنشاء النسخة الاحتياطية' });
    }
  });

  app.get("/api/backup/status", async (req, res) => {
    try {
      const backupDir = '/tmp/backups';
      const files = await fs.readdir(backupDir);
      const backupFiles = files.filter(file => file.startsWith('backup-') && file.endsWith('.sql'));

      const backupsInfo = await Promise.all(backupFiles.map(async (file) => {
        const stats = await fs.stat(path.join(backupDir, file));
        return {
          filename: file,
          createdAt: stats.mtime,
          size: stats.size
        };
      }));

      res.json({
        totalBackups: backupFiles.length,
        backups: backupsInfo.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
      });
    } catch (error) {
      if (error.code === 'ENOENT') {
        logger.warn('Directory not found:', error);
        res.json({ totalBackups: 0, backups: [] }); //Handle the case where the directory doesn't exist
      } else {
        logger.error('خطأ في جلب حالة النسخ الاحتياطي:', error);
        res.status(500).json({ error: 'فشل جلب حالة النسخ الاحتياطي' });
      }
    }
  });

  app.post("/api/backup/restore/:filename", async (req, res) => {
    try {
      const result = await restoreBackup(req.params.filename);
      logger.info('تم استعادة النسخة الاحتياطية بنجاح:', result);
      res.json(result);
    } catch (error) {
      logger.error('خطأ في استعادة النسخة الاحتياطية:', error);
      res.status(500).json({ error: 'فشل استعادة النسخة الاحتياطية' });
    }
  });

  // نقاط نهاية API للمراقبة
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

  // مراقبة النظام والأخطاء
  app.use(errorTracker);

  // بدء المراقبة والنسخ الاحتياطي التلقائي
  startMonitoring();
  scheduleBackups();

  const httpServer = createServer(app);
  return httpServer;
}