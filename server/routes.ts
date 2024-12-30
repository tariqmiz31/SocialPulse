import type { Express } from "express";
import { createServer, type Server } from "http";
import helmet from "helmet";
import cors from "cors";
import { db } from "@db";
import { posts } from "@db/schema";

export function registerRoutes(app: Express): Server {
  // Security middlewares with custom domain support
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        connectSrc: ["'self'", "https://silvariumsocial.com"],
        imgSrc: ["'self'", "data:", "blob:"],
        scriptSrc: ["'self'", "'unsafe-inline'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
      },
    },
    crossOriginEmbedderPolicy: false,
    crossOriginResourcePolicy: { policy: "cross-origin" }
  }));

  // CORS configuration for custom domain
  const allowedOrigins = [
    "https://silvariumsocial.com",
    process.env.APP_URL,
  ].filter(Boolean);

  app.use(cors({
    origin: (origin, callback) => {
      if (!origin || allowedOrigins.includes(origin)) {
        callback(null, true);
      } else {
        callback(new Error('Not allowed by CORS'));
      }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  }));

  // Health check endpoint
  app.get("/api/health", (_req, res) => {
    res.json({ 
      status: "healthy",
      domain: process.env.APP_URL,
      timestamp: new Date().toISOString()
    });
  });

  // API routes
  app.post("/api/posts", async (req, res) => {
    try {
      const { content, platforms } = req.body;

      if (!content || !platforms || !Array.isArray(platforms)) {
        return res.status(400).json({
          error: "Invalid request body",
          message: "Content and platforms are required, and platforms must be an array."
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
      });
    } catch (error: any) {
      console.error("Error processing request:", error);
      return res.status(500).json({
        error: "Internal server error",
        details: process.env.NODE_ENV === "development" ? error.message : undefined,
      });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}