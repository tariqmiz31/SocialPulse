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

// CDN and Security Headers
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      connectSrc: ["'self'", process.env.APP_URL || "", process.env.CUSTOM_DOMAIN ? `*.${process.env.CUSTOM_DOMAIN}` : ""].filter(Boolean),
      imgSrc: ["'self'", "data:", "blob:", "*.${process.env.CUSTOM_DOMAIN}", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
      scriptSrc: ["'self'", "'unsafe-inline'", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
      styleSrc: ["'self'", "'unsafe-inline'", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
      fontSrc: ["'self'", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
      mediaSrc: ["'self'", "cdn.${process.env.CUSTOM_DOMAIN}"].filter(Boolean),
      frameSrc: ["'self'"],
      objectSrc: ["'none'"],
      upgradeInsecureRequests: []
    }
  },
  crossOriginEmbedderPolicy: false,
  crossOriginResourcePolicy: { policy: "cross-origin" },
  dnsPrefetchControl: { allow: true }
}));

// Enable compression with CDN-friendly settings
app.use(compression({
  level: 6,
  threshold: 1024,
  filter: (req) => {
    // Don't compress if client is a CDN that already handles compression
    const userAgent = req.headers['user-agent'] || '';
    if (userAgent.includes('CloudFront') || userAgent.includes('Cloudflare')) {
      return false;
    }
    return compression.filter(req);
  }
}));

// Configure CORS with CDN support
const allowedOrigins = [
  process.env.APP_URL,
  process.env.CUSTOM_DOMAIN,
  process.env.CUSTOM_DOMAIN ? `*.${process.env.CUSTOM_DOMAIN}` : null,
  process.env.CUSTOM_DOMAIN ? `cdn.${process.env.CUSTOM_DOMAIN}` : null
].filter(Boolean);

app.use(cors({
  origin: (origin, callback) => {
    if (!origin || allowedOrigins.some(allowed => {
      if (allowed.startsWith('*.')) {
        const domain = allowed.slice(2);
        return origin.endsWith(domain);
      }
      return origin === allowed;
    })) {
      callback(null, true);
      return;
    }
    callback(new Error('Not allowed by CORS'));
  },
  credentials: true,
  maxAge: 86400 // CORS preflight cache for 24 hours
}));

// Cache Control Headers for static assets
app.use((req, res, next) => {
  // Skip for API routes
  if (req.path.startsWith('/api/')) {
    return next();
  }

  // Cache static assets
  if (req.method === 'GET' && (
    req.path.match(/\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$/)
  )) {
    res.setHeader('Cache-Control', 'public, max-age=31536000'); // 1 year
    res.setHeader('Vary', 'Accept-Encoding');
  }
  next();
});

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
        logger.info(`Supporting CDN on cdn.${domain}`);
        logger.info(`Supporting subdomains for: *.${domain}`);
      }
    });
  } catch (error) {
    logger.error("Failed to start the server:", error);
    process.exit(1);
  }
})();

export { app };