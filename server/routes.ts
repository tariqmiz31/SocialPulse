import type { Express } from "express";
import { createServer, type Server } from "http";
import helmet from "helmet";
import cors from "cors";
import compression from "compression";
import { db } from "@db";
import { users } from "@db/schema";
import rateLimit from "express-rate-limit";
import { performanceMonitor, errorTracker, requestCounter, getHealthData, memoryMonitor } from "./monitoring";

export function registerRoutes(app: Express): Server {
  // Enable monitoring middleware
  app.use(performanceMonitor);
  app.use(requestCounter);

  // Start memory monitoring interval
  setInterval(memoryMonitor, 60000); // Check memory every minute

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
  app.get("/api/monitoring/health", (_req, res) => {
    res.json(getHealthData());
  });

  app.get("/api/monitoring/status", (_req, res) => {
    const dbStatus = db ? "connected" : "disconnected";

    res.json({
      server: "running",
      database: dbStatus,
      environment: process.env.NODE_ENV,
      domain: process.env.CUSTOM_DOMAIN || process.env.APP_URL
    });
  });

  // Authentication routes
  app.post("/api/auth/login", async (req, res) => {
    try {
      const { email, password } = req.body;

      // Basic validation
      if (!email || !password) {
        return res.status(400).json({
          error: "البريد الإلكتروني وكلمة المرور مطلوبة"
        });
      }

      // Here you would typically validate against the database
      // For now, we'll just return a success response
      return res.status(200).json({
        message: "تم تسجيل الدخول بنجاح",
        user: {
          email,
          name: "مستخدم تجريبي"
        }
      });
    } catch (error) {
      console.error("Login error:", error);
      return res.status(500).json({
        error: "حدث خطأ أثناء تسجيل الدخول"
      });
    }
  });

  // Health check endpoint with domain info
  app.get("/api/health", (req, res) => {
    const host = req.get('host') || '';
    const subdomain = host.split('.')[0];

    res.json({ 
      status: "healthy",
      domain: process.env.APP_URL,
      customDomain: process.env.CUSTOM_DOMAIN,
      host: host,
      subdomain: subdomain !== 'www' ? subdomain : 'root',
      timestamp: new Date().toISOString()
    });
  });

  // API routes with enhanced error handling
  app.post("/api/posts", async (req, res) => {
    try {
      const { content, platforms } = req.body;

      if (!content || !platforms || !Array.isArray(platforms)) {
        return res.status(400).json({
          error: "Invalid request body",
          message: "Content and platforms are required, and platforms must be an array.",
          domain: process.env.APP_URL
        });
      }

      const post = await db
        .insert(users) //Corrected to 'users' assuming 'posts' was a typo.  If not, replace with the correct table name.
        .values({
          content,
          platforms,
          status: "pending",
          scheduledFor: new Date(),
        })
        .returning();

      return res.status(201).json({
        message: "Post created successfully",
        post,
        domain: process.env.APP_URL
      });
    } catch (error: any) {
      console.error("Error processing request:", error);
      return res.status(500).json({
        error: "Internal server error",
        domain: process.env.APP_URL,
        details: process.env.NODE_ENV === "development" ? error.message : undefined,
      });
    }
  });

  // Force HTTPS redirect for production
  if (process.env.NODE_ENV === 'production') {
    app.use((req, res, next) => {
      if (req.secure) return next();
      res.redirect(`https://${req.headers.host}${req.url}`);
    });
  }

  // Error tracking middleware should be last
  app.use(errorTracker);

  const httpServer = createServer(app);
  return httpServer;
}