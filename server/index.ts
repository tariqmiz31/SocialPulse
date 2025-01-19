import dotenv from "dotenv";
dotenv.config();
import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";
import { createServer } from "http";
import helmet from "helmet";
import cors from "cors";
import compression from "compression";
import { performanceMonitor, startMonitoring } from "./monitoring";
import { scheduleBackups } from "./backup";
import logger from "./logConfig";
import { db } from "@db";
import { sql } from "drizzle-orm";
import session from "express-session";
import createMemoryStore from "memorystore";
import passport from "passport";

// Create Express app
const app = express();

// Basic middleware setup
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

// Configure CORS before routes
app.use(cors({
  origin: process.env.NODE_ENV === 'production' 
    ? [process.env.APP_URL].filter(Boolean) as string[]
    : ['http://localhost:5000', 'http://0.0.0.0:5000'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Security Headers
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      connectSrc: ["'self'", process.env.NODE_ENV === 'development' ? "*" : undefined].filter(Boolean) as string[],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "blob:"],
      frameSrc: ["'self'"],
      objectSrc: ["'none'"],
      upgradeInsecureRequests: []
    }
  }
}));

// Session configuration
const MemoryStore = createMemoryStore(session);
const sessionSettings: session.SessionOptions = {
  secret: process.env.REPL_ID || "silvarium-social-secret",
  resave: false,
  saveUninitialized: false,
  cookie: {},
  store: new MemoryStore({
    checkPeriod: 86400000, // prune expired entries every 24h
  }),
};

if (app.get("env") === "production") {
  app.set("trust proxy", 1);
  sessionSettings.cookie = {
    secure: true,
    sameSite: 'lax'
  };
}

app.use(session(sessionSettings));
app.use(passport.initialize());
app.use(passport.session());

// Enable compression
app.use(compression());

// Add performance monitoring
app.use(performanceMonitor);

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  logger.debug(`Incoming request: ${req.method} ${path}`);

  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      if (logLine.length > 80) {
        logLine = logLine.slice(0, 79) + "…";
      }

      log(logLine);
      logger.info(logLine);
    }
  });

  next();
});

// نقطة نهاية التحقق من صحة الخادم
app.get("/api/health", (_req, res) => {
  try {
    res.json({
      status: "healthy",
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || "development",
      version: process.env.npm_package_version || "1.0.0"
    });
  } catch (error) {
    logger.error("خطأ في نقطة نهاية الصحة:", error);
    res.status(500).json({ 
      status: "error", 
      message: "خطأ داخلي في الخادم",
      timestamp: new Date().toISOString()
    });
  }
});

// Error handling middleware
app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
  const status = err.status || err.statusCode || 500;
  const message = err.message || "Internal Server Error";

  logger.error({
    message: err.message,
    stack: err.stack,
    timestamp: new Date().toISOString()
  });

  res.status(status).json({ 
    error: true,
    message: process.env.NODE_ENV === 'production' ? 'An internal server error occurred' : message,
    timestamp: new Date().toISOString()
  });
});

// Initialize server setup
(async () => {
  try {
    // Test database connection before starting server
    logger.info("Testing database connection before server start...");
    await db.execute(sql`SELECT 1`);
    logger.info("Initial database connection test successful");

    // Create HTTP server and register routes
    const server = createServer(app);
    registerRoutes(app);
    logger.info("Routes registered successfully");

    // Start monitoring
    startMonitoring();

    // Setup scheduled tasks
    scheduleBackups();

    // Setup vite in development
    if (process.env.NODE_ENV !== 'production') {
      await setupVite(app, server);
    } else {
      serveStatic(app);
    }

    // Start server on port 5000
    const PORT = parseInt(process.env.PORT || "5000", 10);
    server.listen(PORT, "0.0.0.0", () => {
      logger.info(`Server running on port ${PORT} in ${process.env.NODE_ENV || 'development'} mode | الخادم يعمل على المنفذ ${PORT}`);
      // Signal ready for workflow
      console.log('ready');
    });

    // Handle cleanup on shutdown
    process.on('SIGTERM', () => {
      logger.info('SIGTERM signal received. Closing HTTP server... | تم استلام إشارة SIGTERM. جاري إغلاق الخادم');
      server.close(() => {
        logger.info('HTTP server closed | تم إغلاق الخادم');
        process.exit(0);
      });
    });

  } catch (error) {
    logger.error("Failed to start the server | فشل في بدء تشغيل الخادم:", error);
    process.exit(1);
  }
})();

export { app };