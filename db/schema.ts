import { pgTable, text, serial, timestamp, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").unique().notNull(),
  password: text("password").notNull(),
  phoneNumber: text("phone_number"),
  role: text("role", { enum: ["admin", "user"] }).notNull().default("user"),
  isApproved: boolean("is_approved").notNull().default(false),
  status: text("status", { enum: ["active", "pending", "blocked"] }).notNull().default("pending"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const verificationCodes = pgTable("verification_codes", {
  id: serial("id").primaryKey(),
  userId: serial("user_id").references(() => users.id),
  code: text("code").notNull(),
  type: text("type", { enum: ["reset_password", "phone_verification"] }).notNull(),
  expiresAt: timestamp("expires_at").notNull(),
  verified: boolean("verified").default(false),
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertUserSchema = createInsertSchema(users, {
  role: z.enum(["admin", "user"]),
  status: z.enum(["active", "pending", "blocked"]),
  phoneNumber: z.string().optional(),
});

export const selectUserSchema = createSelectSchema(users);
export type InsertUser = typeof users.$inferInsert;
export type SelectUser = typeof users.$inferSelect;

export const insertVerificationCodeSchema = createInsertSchema(verificationCodes, {
  type: z.enum(["reset_password", "phone_verification"]),
});

export const selectVerificationCodeSchema = createSelectSchema(verificationCodes);
export type InsertVerificationCode = typeof verificationCodes.$inferInsert;
export type SelectVerificationCode = typeof verificationCodes.$inferSelect;

export const socialPlatforms = pgTable("social_platforms", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  apiKey: text("api_key"),
  apiSecret: text("api_secret"),
  active: boolean("active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const platformConnections = pgTable("platform_connections", {
  id: serial("id").primaryKey(),
  userId: serial("user_id").references(() => users.id),
  platformId: serial("platform_id").references(() => socialPlatforms.id),
  accessToken: text("access_token").notNull(),
  refreshToken: text("refresh_token"),
  expiresAt: timestamp("expires_at"),
  platformUsername: text("platform_username"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const tasks = pgTable("tasks", {
  id: serial("id").primaryKey(),
  title: text("title").notNull(),
  description: text("description"),
  content: text("content").notNull(),
  platformIds: text("platform_ids").array(),
  scheduledTime: timestamp("scheduled_time"),
  status: text("status", {
    enum: ["draft", "scheduled", "published", "failed"]
  }).notNull().default("draft"),
  userId: serial("user_id").references(() => users.id),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const taskAnalytics = pgTable("task_analytics", {
  id: serial("id").primaryKey(),
  taskId: serial("task_id").references(() => tasks.id),
  platformId: serial("platform_id").references(() => socialPlatforms.id),
  engagement: text("engagement").default("0"),
  likes: text("likes").default("0"),
  shares: text("shares").default("0"),
  comments: text("comments").default("0"),
  reach: text("reach").default("0"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

// Export types for TaskAnalytics
export const insertTaskAnalyticsSchema = createInsertSchema(taskAnalytics);
export const selectTaskAnalyticsSchema = createSelectSchema(taskAnalytics);
export type InsertTaskAnalytics = typeof taskAnalytics.$inferInsert;
export type SelectTaskAnalytics = typeof taskAnalytics.$inferSelect;

// Export types for Tasks
export const insertTaskSchema = createInsertSchema(tasks);
export const selectTaskSchema = createSelectSchema(tasks);
export type InsertTask = typeof tasks.$inferInsert;
export type SelectTask = typeof tasks.$inferSelect;

// Export types for SocialPlatforms
export const insertSocialPlatformSchema = createInsertSchema(socialPlatforms);
export const selectSocialPlatformSchema = createSelectSchema(socialPlatforms);
export type InsertSocialPlatform = typeof socialPlatforms.$inferInsert;
export type SelectSocialPlatform = typeof socialPlatforms.$inferSelect;

// Export types for PlatformConnections
export const insertPlatformConnectionSchema = createInsertSchema(platformConnections);
export const selectPlatformConnectionSchema = createSelectSchema(platformConnections);
export type InsertPlatformConnection = typeof platformConnections.$inferInsert;
export type SelectPlatformConnection = typeof platformConnections.$inferSelect;

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