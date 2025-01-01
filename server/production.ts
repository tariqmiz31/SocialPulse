import express, { Request, Response, NextFunction } from "express";
import { app } from "./index";
import logger from "./logConfig";
import dotenv from "dotenv";
import helmet from "helmet";
import cors from "cors";
import rateLimit from "express-rate-limit";
import compression from "compression";

dotenv.config();

const PORT = parseInt(process.env.PORT || "5000", 10);
const HOST = "0.0.0.0";
const CUSTOM_DOMAIN = process.env.CUSTOM_DOMAIN || "silvariumsocial.com";

export function configureProduction(app: express.Application) {
  // تمكين وسائط الأمان
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        connectSrc: ["'self'", `https://${CUSTOM_DOMAIN}`, `wss://*.${CUSTOM_DOMAIN}`],
        imgSrc: ["'self'", "data:", "blob:", `https://*.${CUSTOM_DOMAIN}`],
        scriptSrc: ["'self'", "'unsafe-inline'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        fontSrc: ["'self'"],
        objectSrc: ["'none'"],
        upgradeInsecureRequests: []
      }
    },
    crossOriginEmbedderPolicy: false,
    crossOriginResourcePolicy: { policy: "cross-origin" }
  }));

  // تمكين ضغط الاستجابة
  app.use(compression());

  // تكوين تحديد معدل الطلبات
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 دقيقة
    max: 100, // حد كل IP إلى 100 طلب لكل windowMs
    message: "تم تجاوز عدد الطلبات المسموح به. يرجى المحاولة مرة أخرى لاحقاً."
  });
  app.use(limiter);

  // تكوين CORS
  const allowedOrigins = [
    `https://${CUSTOM_DOMAIN}`,
    `https://www.${CUSTOM_DOMAIN}`,
    `https://*.${CUSTOM_DOMAIN}`,
    process.env.APP_URL
  ].filter(Boolean);

  app.use(cors({
    origin: (origin, callback) => {
      if (!origin || allowedOrigins.some(allowed => {
        if (allowed?.includes('*')) {
          const pattern = new RegExp(allowed.replace('*.', '.*\\.'));
          return pattern.test(origin);
        }
        return origin === allowed;
      })) {
        callback(null, true);
      } else {
        callback(new Error('Not allowed by CORS'));
      }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    maxAge: 86400 // CORS preflight cache for 24 hours
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
      error: process.env.NODE_ENV === 'production'
        ? 'حدث خطأ في الخادم'
        : err.message
    });
  });

  // تمكين HTTPS في بيئة الإنتاج
  if (process.env.NODE_ENV === 'production') {
    app.enable('trust proxy');
    app.use((req, res, next) => {
      if (req.secure) return next();
      res.redirect(`https://${req.headers.host}${req.url}`);
    });
  }

  // تسجيل معلومات التشغيل
  logger.info(`Server configured for production`, {
    port: PORT,
    host: HOST,
    domain: CUSTOM_DOMAIN,
    securityEnabled: true,
    compressionEnabled: true,
    corsEnabled: true
  });

  return app;
}

export function startProductionServer(app: express.Application) {
  try {
    app.listen(PORT, HOST, () => {
      logger.info(`Production server running at http://${HOST}:${PORT}`);
      logger.info(`Main domain: ${CUSTOM_DOMAIN}`);
      logger.info('Security headers and CORS configured for domain and subdomains');
    });
  } catch (error) {
    logger.error("Failed to start production server:", error);
    process.exit(1);
  }
}

const configuredApp = configureProduction(app);
startProductionServer(configuredApp);