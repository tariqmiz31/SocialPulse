import express, { Request, Response, NextFunction } from "express";
import { app } from "./index";
import logger from "./logConfig";
import dotenv from "dotenv";
import helmet from "helmet";
import cors from "cors";
import rateLimit from "express-rate-limit";
import compression from "compression";
import { createServer } from "http";
import { promisify } from "util";
import { exec } from "child_process";

dotenv.config();

const DEFAULT_PORT = 8080;
const PORT = parseInt(process.env.PORT || `${DEFAULT_PORT}`, 10);
const HOST = "0.0.0.0";

const execAsync = promisify(exec);

async function checkPort(port: number): Promise<boolean> {
  try {
    const server = createServer();
    return new Promise((resolve) => {
      server.once('error', (err: any) => {
        if (err.code === 'EADDRINUSE') {
          logger.warn(`المنفذ ${port} مشغول حالياً | Port ${port} is currently in use`);
          resolve(false);
        }
      });

      server.once('listening', () => {
        server.close();
        resolve(true);
      });

      server.listen(port, HOST);
    });
  } catch (error) {
    logger.error(`خطأ في فحص المنفذ ${port}: ${error}`);
    return false;
  }
}

async function waitForPort(port: number, maxAttempts: number = 30): Promise<boolean> {
  logger.info(`انتظار المنفذ ${port}... | Waiting for port ${port}...`);

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const isAvailable = await checkPort(port);
    if (isAvailable) {
      logger.info(`المنفذ ${port} متاح الآن | Port ${port} is now available`);
      return true;
    }

    if (attempt < maxAttempts) {
      logger.debug(`محاولة ${attempt}/${maxAttempts} - انتظار ثانيتين... | Attempt ${attempt}/${maxAttempts} - waiting 2 seconds...`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }

  logger.error(`فشل في انتظار المنفذ ${port} بعد ${maxAttempts} محاولة | Failed to wait for port ${port} after ${maxAttempts} attempts`);
  return false;
}

export function configureProduction(app: express.Application) {
  // تمكين وسائط الأمان
  app.use(helmet());

  // تمكين ضغط الاستجابة
  app.use(compression());

  // تكوين تحديد معدل الطلبات
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    message: "تم تجاوز عدد الطلبات المسموح به. يرجى المحاولة مرة أخرى لاحقاً."
  });
  app.use("/api", limiter);

  // تكوين CORS
  app.use(cors({
    origin: ["http://localhost:8080", "https://*.repl.co", "http://0.0.0.0:8080"],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
  }));

  // تتبع الأخطاء وتسجيلها
  app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
    logger.error('خطأ في التطبيق | Application error:', {
      error: err.message,
      stack: err.stack,
      path: req.path,
      method: req.method
    });

    res.status(500).json({
      error: 'حدث خطأ في الخادم'
    });
  });

  // تمكين HTTPS
  app.enable('trust proxy');

  return app;
}

export async function startProductionServer(app: express.Application) {
  try {
    // التحقق من توفر المنفذ
    const isPortAvailable = await waitForPort(PORT);
    if (!isPortAvailable) {
      logger.error(`المنفذ ${PORT} غير متاح، إنهاء التطبيق | Port ${PORT} unavailable, terminating application`);
      process.exit(1);
    }

    const server = app.listen(PORT, HOST, () => {
      logger.info(`خادم الإنتاج يعمل على http://${HOST}:${PORT}`);
      logger.info('تم تكوين رؤوس الأمان وCORS | Security headers and CORS configured');

      // إشارة إلى أن الخادم جاهز
      console.log('ready');
    });

    // إضافة معالج لإغلاق الخادم بشكل نظيف
    process.on('SIGTERM', () => {
      logger.info('تم استلام إشارة SIGTERM: إغلاق خادم HTTP');
      server.close(() => {
        logger.info('تم إغلاق خادم HTTP');
      });
    });

    return server;
  } catch (error) {
    logger.error("فشل في بدء خادم الإنتاج | Failed to start production server:", error);
    process.exit(1);
  }
}

const configuredApp = configureProduction(app);
startProductionServer(configuredApp);