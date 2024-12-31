import type { Express } from "express";
import { createServer, type Server } from "http";
import helmet from "helmet";
import cors from "cors";
import { db } from "@db";
import { posts } from "@db/schema";

export function registerRoutes(app: Express): Server {
  // Enhanced security middlewares with subdomain support
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        connectSrc: ["'self'", "*.silvariumsocial.com"],
        imgSrc: ["'self'", "data:", "blob:", "*.silvariumsocial.com"],
        scriptSrc: ["'self'", "'unsafe-inline'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        frameSrc: ["'self'", "*.silvariumsocial.com"],
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
    "silvariumsocial.com",
    "*.silvariumsocial.com",
    process.env.APP_URL,
  ].filter(Boolean);

  app.use(cors({
    origin: (origin, callback) => {
      if (!origin) {
        callback(null, true);
        return;
      }

      const isAllowed = allowedDomains.some(domain => {
        if (domain.startsWith("*.")) {
          const baseDomain = domain.slice(2);
          return origin.endsWith(baseDomain);
        }
        return origin === `https://${domain}`;
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

  // Health check endpoint with subdomain info
  app.get("/api/health", (req, res) => {
    const host = req.get('host') || '';
    const subdomain = host.split('.')[0];

    res.json({ 
      status: "healthy",
      domain: process.env.APP_URL,
      host: host,
      subdomain: subdomain !== 'www' ? subdomain : 'root',
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV
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
        .insert(posts)
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

  const httpServer = createServer(app);
  return httpServer;
}