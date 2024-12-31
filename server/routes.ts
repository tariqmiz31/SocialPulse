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

export function registerRoutes(app: Express): Server {
  // Enhanced security configuration
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

  // Enhanced CORS configuration
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
        callback(new Error('Not allowed by CORS'));
      }
    },
    credentials: true
  }));

  // Enable response compression
  app.use(compression());

  // Rate limiting configuration
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
  });

  app.use(limiter);

  // Setup authentication
  setupAuth(app);

  // Enable monitoring middleware
  app.use(performanceMonitor);

  // Monitoring routes
  app.get("/api/monitoring/metrics", metricsHandler);

  app.get("/api/monitoring/health", async (_req, res) => {
    try {
      const healthData = await getHealthData();
      res.json(healthData);
    } catch (error) {
      logger.error('Error fetching health data:', error);
      res.status(500).json({ error: 'Error fetching health data' });
    }
  });

  app.get("/api/monitoring/status", async (_req, res) => {
    try {
      const dbStatus = db ? "connected" : "disconnected";

      res.json({
        server: "running",
        database: dbStatus,
        environment: process.env.NODE_ENV,
        domain: process.env.CUSTOM_DOMAIN || process.env.APP_URL
      });
    } catch (error) {
      logger.error('Error fetching system status:', error);
      res.status(500).json({ error: 'Error fetching system status' });
    }
  });

  // System and error monitoring
  app.use(errorTracker);

  // Start monitoring
  startMonitoring();

  const httpServer = createServer(app);
  return httpServer;
}