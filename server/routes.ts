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
    if (!req.isAuthenticated()) {
      return res.status(401).json({ message: "يجب تسجيل الدخول للوصول إلى هذه الصفحة" });
    }

    const [user] = await db
      .select()
      .from(users)
      .where(eq(users.id, req.user.id))
      .limit(1);

    if (!user || user.role !== "admin") {
      return res.status(403).json({ message: "غير مصرح لك بالوصول إلى هذه الصفحة" });
    }

    next();
  } catch (error) {
    console.error("Error in isAdmin middleware:", error);
    return res.status(500).json({ message: "حدث خطأ أثناء التحقق من الصلاحيات" });
  }
}

export function registerRoutes(app: Express): Server {
  // إعداد Passport
  app.use(passport.initialize());
  app.use(passport.session());

  // تحديث نقطة نهاية تغيير الصلاحيات مع التحقق متعدد المراحل
  app.post("/api/admin/users/:userId/:action", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      const action = req.params.action;
      const { verificationStep = 'initial', verificationCode } = req.body;

      const [user] = await db
        .select()
        .from(users)
        .where(eq(users.id, userId))
        .limit(1);

      if (!user) {
        return res.status(404).json({ message: "المستخدم غير موجود" });
      }

      // التحقق من مراحل تغيير الصلاحيات
      if (action === "promote" || action === "demote") {
        switch (verificationStep) {
          case 'initial':
            if (!user.email) {
              return res.status(400).json({ message: "يجب إضافة بريد إلكتروني للمستخدم أولاً" });
            }
            break;

          case 'email_sent':
            const [verificationRecord] = await db
              .select()
              .from(verificationCodes)
              .where(
                and(
                  eq(verificationCodes.userId, req.user.id),
                  eq(verificationCodes.type, "role_change"),
                  eq(verificationCodes.verified, false)
                )
              )
              .limit(1);

            if (!verificationRecord) {
              return res.status(400).json({ message: "لم يتم العثور على رمز تحقق صالح" });
            }

            if (verificationRecord.code !== verificationCode) {
              return res.status(400).json({ message: "رمز التحقق غير صحيح" });
            }

            // تحديث حالة رمز التحقق
            await db
              .update(verificationCodes)
              .set({ verified: true })
              .where(eq(verificationCodes.id, verificationRecord.id));

            // تنفيذ تغيير الصلاحية
            await db
              .update(users)
              .set({ 
                role: action === "promote" ? "admin" : "user",
                updatedAt: new Date()
              })
              .where(eq(users.id, userId));

            // إرسال إشعار بالبريد الإلكتروني
            if (user.email) {
              await sendRoleChangeNotification(user.email, action === "promote" ? "admin" : "user");
            }

            return res.json({
              message: action === "promote" 
                ? "تمت ترقية المستخدم إلى مشرف بنجاح" 
                : "تم إلغاء صلاحيات الإشراف بنجاح"
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
      console.error('Error updating user role:', error);
      res.status(500).json({ message: "خطأ في تحديث حالة المستخدم" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}