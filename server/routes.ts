import type { Express } from "express";
import { createServer, type Server } from "http";
import { db } from "@db";
import { users } from "@db/schema";
import { eq } from "drizzle-orm";
import helmet from "helmet";
import cors from "cors";
import compression from "compression";
import rateLimit from "express-rate-limit";

// وظيفة مساعدة للتحقق من صلاحيات المشرف
const isAdmin = (req: any, res: any, next: any) => {
  if (req.isAuthenticated() && req.user.role === "admin") {
    return next();
  }
  res.status(403).send("غير مصرح بالوصول");
};

export function registerRoutes(app: Express): Server {
  // تكوين الأمان المحسّن
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        connectSrc: ["'self'", process.env.APP_URL || ""],
        scriptSrc: ["'self'", "'unsafe-inline'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        fontSrc: ["'self'"],
        imgSrc: ["'self'", "data:", "blob:"],
        frameSrc: ["'self'"],
        objectSrc: ["'none'"],
        upgradeInsecureRequests: []
      }
    }
  }));

  // تكوين CORS
  app.use(cors({
    origin: process.env.APP_URL,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
  }));

  // تمكين ضغط الاستجابة
  app.use(compression());

  // تكوين تحديد معدل الطلبات
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
    message: "تم تجاوز عدد الطلبات المسموح به. يرجى المحاولة مرة أخرى لاحقاً."
  });

  app.use("/api", limiter);

  // نقاط نهاية لوحة الإشراف
  app.get("/api/admin/users", isAdmin, async (_req, res) => {
    try {
      const usersList = await db
        .select({
          id: users.id,
          username: users.username,
          role: users.role,
          isApproved: users.isApproved,
          status: users.status,
          createdAt: users.createdAt,
        })
        .from(users);
      res.json(usersList);
    } catch (error) {
      res.status(500).send("خطأ في استرجاع قائمة المستخدمين");
    }
  });

  app.post("/api/admin/users/:userId/approve", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      await db
        .update(users)
        .set({ isApproved: true, status: "active" })
        .where(eq(users.id, userId));
      res.json({ message: "تمت الموافقة على المستخدم بنجاح" });
    } catch (error) {
      res.status(500).send("خطأ في تحديث حالة المستخدم");
    }
  });

  app.post("/api/admin/users/:userId/block", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      await db
        .update(users)
        .set({ status: "blocked" })
        .where(eq(users.id, userId));
      res.json({ message: "تم حظر المستخدم بنجاح" });
    } catch (error) {
      res.status(500).send("خطأ في تحديث حالة المستخدم");
    }
  });

  app.post("/api/admin/users/:userId/unblock", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      await db
        .update(users)
        .set({ status: "active" })
        .where(eq(users.id, userId));
      res.json({ message: "تم إلغاء حظر المستخدم بنجاح" });
    } catch (error) {
      res.status(500).send("خطأ في تحديث حالة المستخدم");
    }
  });

  app.post("/api/admin/users/:userId/promote", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      await db
        .update(users)
        .set({ role: "admin" })
        .where(eq(users.id, userId));
      res.json({ message: "تمت ترقية المستخدم إلى مشرف بنجاح" });
    } catch (error) {
      res.status(500).send("خطأ في ترقية المستخدم");
    }
  });

  app.post("/api/admin/users/:userId/demote", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      await db
        .update(users)
        .set({ role: "user" })
        .where(eq(users.id, userId));
      res.json({ message: "تم إلغاء صلاحيات الإشراف بنجاح" });
    } catch (error) {
      res.status(500).send("خطأ في إلغاء صلاحيات الإشراف");
    }
  });

  app.delete("/api/admin/users/:userId", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      await db
        .delete(users)
        .where(eq(users.id, userId));
      res.json({ message: "تم حذف المستخدم بنجاح" });
    } catch (error) {
      res.status(500).send("خطأ في حذف المستخدم");
    }
  });

  // تحديث نقطة نهاية التسجيل لتعيين المستخدمين الجدد كمعلقين
  app.post("/api/register", async (req, res) => {
    try {
      const { username, password } = req.body;

      // التحقق من وجود المستخدم
      const existingUser = await db
        .select()
        .from(users)
        .where(eq(users.username, username))
        .limit(1);

      if (existingUser.length > 0) {
        return res.status(400).send("اسم المستخدم موجود بالفعل");
      }

      // إنشاء مستخدم جديد
      const [newUser] = await db
        .insert(users)
        .values({
          username,
          password,
          role: "user",
          status: "pending",
          isApproved: false
        })
        .returning();

      res.json({ 
        message: "تم إنشاء الحساب بنجاح وبانتظار موافقة المشرف",
        user: {
          id: newUser.id,
          username: newUser.username,
          status: newUser.status
        }
      });
    } catch (error) {
      res.status(500).send("خطأ في إنشاء المستخدم");
    }
  });

  // نقطة نهاية الحالة الأساسية
  app.get("/api/status", (_req, res) => {
    res.json({
      status: "running",
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV,
      auth_method: "admin_approval_required"
    });
  });

  const httpServer = createServer(app);
  return httpServer;
}