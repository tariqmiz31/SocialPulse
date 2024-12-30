import type { Express } from "express";
import { createServer, type Server } from "http";
import helmet from "helmet";
import cors from "cors";
import { db } from "@db";
import { posts } from "@db/schema";

export function registerRoutes(app: Express): Server {
  // Security middlewares
  app.use(helmet());
  app.use(cors({
    origin: process.env.ALLOWED_ORIGINS?.split(",") || ["https://*.repl.co"],
    credentials: true
  }));

  // Health check endpoint
  app.get("/api/health", (_req, res) => {
    res.json({ status: "healthy" });
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
    } catch (error) {
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