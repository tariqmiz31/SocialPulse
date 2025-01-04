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

// Create Express app
const app = express();

// Basic middleware
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

// Security Headers with configuration for Firebase and development
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'", "https://*.firebaseapp.com"],
      connectSrc: ["'self'", "https://*.firebaseapp.com", "https://*.firebase.com"],
      scriptSrc: ["'self'", "'unsafe-inline'", "https://*.firebaseapp.com", "https://*.gstatic.com"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      fontSrc: ["'self'", "https://*.gstatic.com"],
      imgSrc: ["'self'", "data:", "blob:", "https://*.google.com"],
      frameSrc: ["'self'", "https://*.firebaseapp.com"],
      objectSrc: ["'none'"],
      upgradeInsecureRequests: []
    }
  }
}));

// Enable compression
app.use(compression());

// Configure CORS for development
const corsOptions = {
  origin: process.env.NODE_ENV === 'production' 
    ? [process.env.APP_URL].filter(Boolean)
    : ['http://localhost:5000', 'http://0.0.0.0:5000'],
  credentials: true
};
app.use(cors(corsOptions));

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

    // importantly only setup vite in development and after
    // setting up all the other routes so the catch-all route
    // doesn't interfere with the other routes
    if (process.env.NODE_ENV !== 'production') {
      await setupVite(app, server);
    } else {
      serveStatic(app);
    }

    // Start server on port 5000
    const PORT = parseInt(process.env.PORT || "5000", 10);
    server.listen(PORT, "0.0.0.0", () => {
      logger.info(`Server running on port ${PORT} in ${process.env.NODE_ENV || 'development'} mode`);
      logger.info(`Database connected successfully`);
    });

    // Handle cleanup on shutdown
    process.on('SIGTERM', () => {
      logger.info('SIGTERM signal received. Closing HTTP server...');
      server.close(() => {
        logger.info('HTTP server closed');
        process.exit(0);
      });
    });

  } catch (error) {
    logger.error("Failed to start the server:", error);
    process.exit(1);
  }
})();

export { app };