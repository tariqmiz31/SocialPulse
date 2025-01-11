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
const waitForPort = (port: number, host: string = '0.0.0.0', timeout: number = 60000): Promise<boolean> => {
  return new Promise((resolve) => {
    const startTime = Date.now();
    const checkPort = () => {
      const socket = new net.Socket();
      socket.on('error', () => {
        socket.destroy();
        logger.info(`Port ${port} is available | المنفذ ${port} متاح`);
        // After port is available, signal ready
        console.log('ready');
        resolve(true);
      });

      socket.connect(port, host, () => {
        socket.destroy();
        if (Date.now() - startTime >= timeout) {
          logger.error(`Port ${port} is not available after timeout | المنفذ ${port} غير متاح بعد انتهاء المهلة`);
          resolve(false);
          return;
        }
        logger.info(`Waiting for port ${port}... | انتظار المنفذ ${port}...`);
        setTimeout(checkPort, 1000);
      });
    };
    checkPort();
  });
};

// Create Express app
const app = express();

// Basic middleware
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

// Security Headers with configuration for development
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

// Configure CORS
app.use(cors({
  origin: process.env.NODE_ENV === 'production' 
    ? [process.env.APP_URL].filter(Boolean) as string[]
    : ['http://localhost:5000', 'http://0.0.0.0:5000'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Add performance monitoring
app.use(performanceMonitor);

// Basic status endpoint for health checks
app.get("/api/monitoring/status", async (_req, res) => {
  try {
    await db.execute(sql`SELECT 1`);
    res.json({
      server: "running",
      database: "connected",
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV
    });
  } catch (error: any) {
    logger.error('Error in status endpoint:', error);
    res.status(500).json({ 
      server: "running",
      database: "error",
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
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

    // Register routes
    registerRoutes(app);

    // Start monitoring
    startMonitoring();

    // Setup scheduled tasks
    scheduleBackups();

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
      logger.info(`Database connected successfully | تم الاتصال بقاعدة البيانات بنجاح`);
      // Signal ready to workflow
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