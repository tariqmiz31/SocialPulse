import type { Express } from "express";
import { createServer, type Server } from "http";
import { db } from "@db";
import { posts, analytics } from "@db/schema";
import { eq } from "drizzle-orm";

export function registerRoutes(app: Express): Server {
  const httpServer = createServer(app);

  // Get scheduled posts
  app.get("/api/scheduled-posts", async (req, res) => {
    try {
      const scheduledPosts = await db.query.posts.findMany({
        where: eq(posts.status, "scheduled"),
        orderBy: (posts, { asc }) => [asc(posts.scheduledFor)],
      });
      res.json(scheduledPosts);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch scheduled posts" });
    }
  });

  // Create new post
  app.post("/api/posts", async (req, res) => {
    try {
      const { content, platforms } = req.body;
      const post = await db.insert(posts).values({
        content,
        platforms,
        scheduledFor: new Date(),
        status: "scheduled",
        userId: 1, // TODO: Get from auth
      }).returning();
      res.json(post[0]);
    } catch (error) {
      res.status(500).json({ error: "Failed to create post" });
    }
  });

  // Get analytics
  app.get("/api/analytics", async (req, res) => {
    try {
      const results = await db.query.analytics.findMany();
      res.json(results);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch analytics" });
    }
  });

  return httpServer;
}
