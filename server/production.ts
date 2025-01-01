import express, { Request, Response, NextFunction } from "express";
import { app } from "./index";
import logger from "./logConfig";
import dotenv from "dotenv";
import helmet from "helmet";
import cors from "cors";
import rateLimit from "express-rate-limit";
import compression from "compression";

dotenv.config();

const PORT = parseInt(process.env.PORT || "5001", 10);
const HOST = "0.0.0.0";

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
    origin: process.env.APP_URL,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
  }));

  // تتبع الأخطاء وتسجيلها
  app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
    logger.error('Application error:', {
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

export function startProductionServer(app: express.Application) {
  try {
    const server = app.listen(PORT, HOST, () => {
      logger.info(`Production server running at http://${HOST}:${PORT}`);
      logger.info('Security headers and CORS configured');
    });

    // إضافة معالج لإغلاق الخادم بشكل نظيف
    process.on('SIGTERM', () => {
      logger.info('SIGTERM signal received: closing HTTP server');
      server.close(() => {
        logger.info('HTTP server closed');
      });
    });

    return server;
  } catch (error) {
    logger.error("Failed to start production server:", error);
    process.exit(1);
  }
}

const configuredApp = configureProduction(app);
startProductionServer(configuredApp);