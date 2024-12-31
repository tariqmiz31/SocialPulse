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

// Create Express app
const app = express();

// Basic middleware
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

// Security middleware
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

// Enable compression
app.use(compression());

// Configure CORS
const allowedOrigins = [
  process.env.APP_URL,
  process.env.CUSTOM_DOMAIN,
  process.env.CUSTOM_DOMAIN ? `*.${process.env.CUSTOM_DOMAIN}` : null
].filter(Boolean);

app.use(cors({
  origin: (origin, callback) => {
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
      return;
    }
    callback(new Error('Not allowed by CORS'));
  },
  credentials: true
}));

// Add performance monitoring middleware
app.use(performanceMonitor);

// Initialize server setup
(async () => {
  try {
    // Create HTTP server
    const server = createServer(app);

    // Register routes with domain configuration
    const domain = process.env.CUSTOM_DOMAIN || process.env.APP_URL;
    app.set('trust proxy', 1);

    // Force HTTPS in production
    app.use((req, res, next) => {
      if (process.env.NODE_ENV === 'production' && !req.secure) {
        return res.redirect(`https://${req.headers.host}${req.url}`);
      }
      next();
    });

    // Register routes
    registerRoutes(app);

    // Start monitoring and backup systems
    startMonitoring();
    scheduleBackups();

    // Error handling middleware
    app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
      const status = err.status || err.statusCode || 500;
      const message = err.message || "Internal Server Error";

      logger.error({
        error: err,
        status,
        message,
        timestamp: new Date().toISOString()
      });

      res.status(status).json({ 
        message,
        domain: process.env.CUSTOM_DOMAIN || process.env.APP_URL,
        timestamp: new Date().toISOString()
      });
    });

    // Setup Vite in development, static files in production
    if (app.get("env") === "development") {
      await setupVite(app, server);
    } else {
      serveStatic(app);
    }

    // Start server
    const PORT = parseInt(process.env.PORT || "5000", 10);
    server.listen(PORT, "0.0.0.0", () => {
      logger.info(`Server running on port ${PORT}`);
      logger.info(`Main domain: ${domain}`);

      if (domain) {
        logger.info(`Supporting subdomains for: *.${domain}`);
      }
    });
  } catch (error) {
    logger.error("Failed to start the server:", error);
    process.exit(1);
  }
})();

export { app };