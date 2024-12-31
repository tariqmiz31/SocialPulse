import type { Express } from "express";
import { createServer, type Server } from "http";
import { db } from "@db";
import { performanceMonitor, errorTracker, metricsHandler, getHealthData } from "./monitoring";
import rateLimit from "express-rate-limit";
import helmet from "helmet";
import cors from "cors";
import compression from "compression";

export function registerRoutes(app: Express): Server {
  // Enable monitoring middleware
  app.use(performanceMonitor);

  // Enable compression
  app.use(compression());

  // Rate limiting
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
  });

  // Apply rate limiting to all routes
  app.use(limiter);

  // Enhanced security middlewares with subdomain support
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
    },
    crossOriginEmbedderPolicy: false,
    crossOriginResourcePolicy: { policy: "cross-origin" },
    dnsPrefetchControl: { allow: false },
    referrerPolicy: { policy: "strict-origin-when-cross-origin" }
  }));

  // Enhanced CORS configuration with wildcard subdomain support
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
        if (domain && domain.startsWith("*.")) {
          const baseDomain = domain.slice(2);
          return origin.endsWith(baseDomain);
        }
        return domain && origin === domain;
      });

      if (isAllowed) {
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

  // Monitoring Routes
  app.get("/metrics", metricsHandler);

  app.get("/api/monitoring/health", async (_req, res) => {
    const healthData = await getHealthData();
    res.json(healthData);
  });

  app.get("/api/monitoring/status", (_req, res) => {
    const dbStatus = db ? "متصل" : "غير متصل";

    res.json({
      server: "يعمل",
      database: dbStatus,
      environment: process.env.NODE_ENV,
      domain: process.env.CUSTOM_DOMAIN || process.env.APP_URL
    });
  });

  // Error tracking middleware should be last
  app.use(errorTracker);

  const httpServer = createServer(app);
  return httpServer;
}