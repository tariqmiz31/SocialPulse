import { pgTable, text, serial, timestamp, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").unique().notNull(),
  password: text("password").notNull(),
  role: text("role", { enum: ["admin", "user"] }).notNull().default("user"),
  isApproved: boolean("is_approved").notNull().default(false),
  status: text("status", { enum: ["active", "pending", "blocked"] }).notNull().default("pending"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users, {
  role: z.enum(["admin", "user"]),
  status: z.enum(["active", "pending", "blocked"]),
});

export const selectUserSchema = createSelectSchema(users);
export type InsertUser = typeof users.$inferInsert;
export type SelectUser = typeof users.$inferSelect;

export const posts = pgTable("posts", {
  id: serial("id").primaryKey(),
  content: text("content").notNull(),
  platforms: text("platforms").notNull(), // Changed from jsonb
  scheduledFor: timestamp("scheduled_for").notNull(),
  status: text("status").notNull(),
  userId: serial("user_id").references(() => users.id),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const platformConnections = pgTable("platform_connections", {
  id: serial("id").primaryKey(),
  userId: serial("user_id").references(() => users.id),
  platform: text("platform").notNull(),
  accessToken: text("access_token").notNull(),
  refreshToken: text("refresh_token"),
  expiresAt: timestamp("expires_at"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const analytics = pgTable("analytics", {
  id: serial("id").primaryKey(),
  postId: serial("post_id").references(() => posts.id),
  platform: text("platform").notNull(),
  likes: text("likes").default("0"), // Changed from integer
  shares: text("shares").default("0"), // Changed from integer
  comments: text("comments").default("0"), // Changed from integer
  reach: text("reach").default("0"),     // Changed from integer
  engagementRate: text("engagement_rate"), // Changed from decimal
  createdAt: timestamp("created_at").defaultNow(),
});

export type InsertPost = typeof posts.$inferInsert;
export type SelectPost = typeof posts.$inferSelect;
export type InsertAnalytics = typeof analytics.$inferInsert;
export type SelectAnalytics = typeof analytics.$inferSelect;