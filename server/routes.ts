import type { Express, Request, Response, NextFunction } from "express";
import { createServer, type Server } from "http";
import { db } from "@db";
import { users, verificationCodes, type SelectUser } from "@db/schema";
import { eq, and } from "drizzle-orm";
import { sendRoleChangeNotification } from "./mail";
import passport from "passport";

// Extend Express.User
declare global {
  namespace Express {
    interface User extends SelectUser {}
  }
}

// التحقق من صلاحيات المشرف
async function isAdmin(req: Request, res: Response, next: NextFunction) {
  try {
    // التحقق من تسجيل الدخول
    if (!req.isAuthenticated()) {
      return res.status(401).json({ message: "يجب تسجيل الدخول للوصول إلى هذه الصفحة" });
    }

    // التحقق من وجود المستخدم وصلاحياته
    const [user] = await db
      .select()
      .from(users)
      .where(eq(users.id, req.user.id))
      .limit(1);

    if (!user) {
      return res.status(404).json({ message: "المستخدم غير موجود" });
    }

    if (user.role !== "admin" || !user.isApproved || user.status !== "active") {
      return res.status(403).json({ message: "غير مصرح لك بالوصول إلى هذه الصفحة" });
    }

    // تخزين معلومات المستخدم للاستخدام لاحقًا
    res.locals.admin = user;
    next();
  } catch (error) {
    console.error("خطأ في التحقق من صلاحيات المشرف:", error);
    return res.status(500).json({ message: "حدث خطأ أثناء التحقق من الصلاحيات" });
  }
}

export function registerRoutes(app: Express): Server {
  // إعداد Passport
  app.use(passport.initialize());
  app.use(passport.session());

  // نقطة نهاية التحقق من صحة الخادم
  app.get("/api/health", (_req, res) => {
    try {
      res.json({
        status: "healthy",
        timestamp: new Date().toISOString(),
        environment: process.env.NODE_ENV || "development",
        version: process.env.npm_package_version || "1.0.0"
      });
    } catch (error) {
      console.error("خطأ في نقطة نهاية الصحة:", error);
      res.status(500).json({ 
        status: "error", 
        message: "خطأ داخلي في الخادم",
        timestamp: new Date().toISOString()
      });
    }
  });

  // تحديث نقطة نهاية تغيير الصلاحيات مع التحقق متعدد المراحل
  app.post("/api/admin/users/:userId/:action", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      const action = req.params.action;
      const { verificationStep = 'initial', verificationCode } = req.body;

      const [targetUser] = await db
        .select()
        .from(users)
        .where(eq(users.id, userId))
        .limit(1);

      if (!targetUser) {
        return res.status(404).json({ message: "المستخدم غير موجود" });
      }

      // التحقق من مراحل تغيير الصلاحيات
      if (action === "promote" || action === "demote") {
        switch (verificationStep) {
          case 'initial':
            if (!targetUser.email) {
              return res.status(400).json({ message: "يجب إضافة بريد إلكتروني للمستخدم أولاً" });
            }

            // إنشاء رمز تحقق جديد
            const newVerificationCode = Math.random().toString(36).substring(2, 8).toUpperCase();
            await db.insert(verificationCodes).values({
              userId: res.locals.admin.id,
              code: newVerificationCode,
              type: "role_change",
              expiresAt: new Date(Date.now() + 30 * 60 * 1000), // 30 دقيقة
              totalSteps: 3,
              adminEmail: res.locals.admin.email,
              ipAddress: req.ip,
              userAgent: req.headers['user-agent']
            });

            return res.json({
              message: "تم إرسال رمز التحقق إلى بريدك الإلكتروني",
              step: 1,
              totalSteps: 3,
              verificationCode: newVerificationCode
            });

          case 'verify_code':
            const [verificationRecord] = await db
              .select()
              .from(verificationCodes)
              .where(
                and(
                  eq(verificationCodes.userId, res.locals.admin.id),
                  eq(verificationCodes.type, "role_change"),
                  eq(verificationCodes.verified, false)
                )
              )
              .limit(1);

            if (!verificationRecord || verificationRecord.code !== verificationCode) {
              return res.status(400).json({ message: "رمز التحقق غير صحيح" });
            }

            if (new Date() > verificationRecord.expiresAt) {
              return res.status(400).json({ message: "انتهت صلاحية رمز التحقق" });
            }

            // تحديث حالة رمز التحقق
            await db
              .update(verificationCodes)
              .set({
                verified: true,
                verifiedAt: new Date(),
                verificationStep: verificationRecord.verificationStep + 1
              })
              .where(eq(verificationCodes.id, verificationRecord.id));

            return res.json({
              message: "تم التحقق من الرمز بنجاح",
              step: 2,
              totalSteps: 3
            });

          case 'confirm':
            // تنفيذ تغيير الصلاحية
            const newRole = action === "promote" ? "admin" : "user";
            await db
              .update(users)
              .set({
                role: newRole,
                roleChangeApproved: true,
                roleChangeApproverId: res.locals.admin.id,
                updatedAt: new Date()
              })
              .where(eq(users.id, userId));

            // إرسال إشعار بالبريد الإلكتروني
            if (targetUser.email) {
              await sendRoleChangeNotification(targetUser.email, newRole);
            }

            return res.json({
              message: action === "promote"
                ? "تمت ترقية المستخدم إلى مشرف بنجاح"
                : "تم إلغاء صلاحيات الإشراف بنجاح",
              step: 3,
              totalSteps: 3
            });

          default:
            return res.status(400).json({ message: "خطوة تحقق غير صالحة" });
        }
      }

      // باقي الإجراءات
      switch (action) {
        case "approve":
          await db
            .update(users)
            .set({ isApproved: true, status: "active", updatedAt: new Date() })
            .where(eq(users.id, userId));
          res.json({ message: "تمت الموافقة على المستخدم بنجاح" });
          break;

        case "block":
          await db
            .update(users)
            .set({ status: "blocked", updatedAt: new Date() })
            .where(eq(users.id, userId));
          res.json({ message: "تم حظر المستخدم بنجاح" });
          break;

        case "unblock":
          await db
            .update(users)
            .set({ status: "active", updatedAt: new Date() })
            .where(eq(users.id, userId));
          res.json({ message: "تم إلغاء حظر المستخدم بنجاح" });
          break;

        default:
          res.status(400).json({ message: "إجراء غير صالح" });
      }
    } catch (error) {
      console.error('خطأ في تحديث حالة المستخدم:', error);
      res.status(500).json({ message: "خطأ في تحديث حالة المستخدم" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}