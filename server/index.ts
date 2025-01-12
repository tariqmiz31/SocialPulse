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
import net from "net";

// Function to check if a port is available
const waitForPort = (port: number, host: string = '0.0.0.0', timeout: number = 60): Promise<boolean> => {
  return new Promise((resolve) => {
    const startTime = Date.now();
    const checkPort = () => {
      const socket = new net.Socket();

      socket.on('error', () => {
        socket.destroy();
        logger.info(`Port ${port} is available | المنفذ ${port} متاح`);
        resolve(true);
      });

      socket.on('connect', () => {
        socket.destroy();
        if (Date.now() - startTime >= timeout * 1000) {
          logger.error(`Port ${port} is not available after timeout | المنفذ ${port} غير متاح بعد انتهاء المهلة`);
          resolve(false);
          return;
        }
        setTimeout(checkPort, 1000);
      });

      socket.connect(port, host);
    };
    checkPort();
  });
};

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

// Enable compression
app.use(compression());

// Add performance monitoring
app.use(performanceMonitor);

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
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
    }
  });

  next();
});

// Initialize server setup
(async () => {
  try {
    // Test database connection before starting server
    logger.info("Testing database connection before server start...");
    await db.execute(sql`SELECT 1`);
    logger.info("Initial database connection test successful");

    // Create HTTP server
    const server = createServer(app);

    // Register routes BEFORE Vite setup
    registerRoutes(app);

    // Start monitoring
    startMonitoring();

    // Setup scheduled tasks
    scheduleBackups();

    // Error handling middleware (must be after routes)
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

    // Setup vite in development
    if (process.env.NODE_ENV !== 'production') {
      await setupVite(app, server);
    } else {
      serveStatic(app);
    }

    // Start server on port 5000 after ensuring port is available
    const PORT = parseInt(process.env.PORT || "5000", 10);
    const isPortAvailable = await waitForPort(PORT);

    if (!isPortAvailable) {
      throw new Error(`Port ${PORT} is not available after timeout`);
    }

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