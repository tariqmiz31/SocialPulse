import type { Express, Request, Response, NextFunction } from "express";
import { createServer, type Server } from "http";
import { db } from "@db";
import { users, verificationCodes, adminPermissionsSchema, roleChangeHistory } from "@db/schema";
import { eq, and } from "drizzle-orm";
import { sendRoleChangeNotification } from "./mail";
import passport from "passport";
import logger from "./logConfig";

// التحقق من صلاحيات المشرف
async function isAdmin(req: Request, res: Response, next: NextFunction) {
  try {
    logger.debug("التحقق من صلاحيات المشرف للمستخدم:", req.user?.username);

    if (!req.isAuthenticated()) {
      logger.warn("محاولة وصول غير مصرح به: المستخدم غير مسجل الدخول");
      return res.status(401).json({ message: "يجب تسجيل الدخول للوصول إلى هذه الصفحة" });
    }

    const [user] = await db
      .select()
      .from(users)
      .where(eq(users.id, req.user.id))
      .limit(1);

    if (!user) {
      logger.warn(`المستخدم غير موجود: ${req.user.id}`);
      return res.status(404).json({ message: "المستخدم غير موجود" });
    }

    const isAdminUser = user.role === "admin" && user.isApproved && user.status === "active";
    if (!isAdminUser) {
      logger.warn(`محاولة وصول غير مصرح به لصفحة المشرف: ${user.username}`);
      return res.status(403).json({ message: "غير مصرح لك بالوصول إلى هذه الصفحة" });
    }

    logger.info(`تم التحقق من صلاحيات المشرف بنجاح: ${user.username}`);
    res.locals.admin = user;
    next();
  } catch (error) {
    logger.error("خطأ في التحقق من صلاحيات المشرف:", error);
    return res.status(500).json({ message: "حدث خطأ أثناء التحقق من الصلاحيات" });
  }
}

export function registerRoutes(app: Express): Server {
  // إعداد المصادقة
  app.use(passport.initialize());
  app.use(passport.session());

  // نقطة نهاية التحقق من صحة الخادم مع سجلات مفصلة
  app.get("/api/health", (_req, res) => {
    try {
      logger.info("تم استلام طلب التحقق من صحة الخادم");
      res.json({
        status: "healthy",
        timestamp: new Date().toISOString(),
        environment: process.env.NODE_ENV || "development",
        version: process.env.npm_package_version || "1.0.0"
      });
      logger.info("تم إرسال رد صحة الخادم بنجاح");
    } catch (error) {
      logger.error("خطأ في نقطة نهاية الصحة:", error);
      res.status(500).json({ 
        status: "error", 
        message: "خطأ داخلي في الخادم",
        timestamp: new Date().toISOString()
      });
    }
  });

  // التحقق من صلاحيات المشرف
  app.get("/api/admin/check-permissions", async (req, res) => {
    try {
      logger.debug("طلب التحقق من صلاحيات المشرف:", req.user?.username);

      if (!req.isAuthenticated()) {
        return res.json({ 
          isAdmin: false,
          role: "user",
          isApproved: false,
          status: "pending"
        });
      }

      const [user] = await db
        .select()
        .from(users)
        .where(eq(users.id, req.user.id))
        .limit(1);

      if (!user) {
        logger.warn(`المستخدم غير موجود في التحقق من الصلاحيات: ${req.user.id}`);
        return res.json({ 
          isAdmin: false,
          role: "user",
          isApproved: false,
          status: "pending"
        });
      }

      const isAdminUser = user.role === "admin" && user.isApproved && user.status === "active";
      const permissions = {
        isAdmin: isAdminUser,
        role: user.role,
        isApproved: user.isApproved,
        status: user.status
      };

      const validatedPermissions = adminPermissionsSchema.parse(permissions);
      logger.info(`تم إرجاع صلاحيات المستخدم: ${user.username}, isAdmin: ${isAdminUser}`);
      res.json(validatedPermissions);

    } catch (error) {
      logger.error('خطأ في التحقق من الصلاحيات:', error);
      res.status(500).json({ message: "خطأ في التحقق من الصلاحيات" });
    }
  });

  // إدارة صلاحيات المستخدمين
  app.post("/api/admin/users/:userId/:action", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      const action = req.params.action;
      const { verificationStep = 'initial', verificationCode } = req.body;

      logger.info(`طلب تحديث صلاحيات المستخدم: ${userId}, الإجراء: ${action}`);

      const [targetUser] = await db
        .select()
        .from(users)
        .where(eq(users.id, userId))
        .limit(1);

      if (!targetUser) {
        logger.warn(`المستخدم المستهدف غير موجود: ${userId}`);
        return res.status(404).json({ message: "المستخدم غير موجود" });
      }

      // تغيير الصلاحيات
      if (action === "promote" || action === "demote") {
        const newRole = action === "promote" ? "admin" : "user";

        switch (verificationStep) {
          case 'initial':
            // إنشاء سجل تغيير الصلاحيات
            const [roleChangeRecord] = await db
              .insert(roleChangeHistory)
              .values({
                userId: targetUser.id,
                adminId: res.locals.admin.id,
                oldRole: targetUser.role,
                newRole,
                changeReason: req.body.reason || "تغيير الصلاحيات من قبل المشرف",
                clientIp: req.ip,
                userAgent: req.headers['user-agent']
              })
              .returning();

            // إنشاء رمز تحقق جديد
            const newVerificationCode = Math.random().toString(36).substring(2, 8).toUpperCase();
            const [verificationRecord] = await db
              .insert(verificationCodes)
              .values({
                userId: res.locals.admin.id,
                code: newVerificationCode,
                type: "role_change",
                expiresAt: new Date(Date.now() + 30 * 60 * 1000),
                totalSteps: 3,
                adminEmail: res.locals.admin.email,
                ipAddress: req.ip,
                userAgent: req.headers['user-agent']
              })
              .returning();

            // تحديث سجل تغيير الصلاحيات
            await db
              .update(roleChangeHistory)
              .set({
                verificationId: verificationRecord.id
              })
              .where(eq(roleChangeHistory.id, roleChangeRecord.id));

            logger.info(`تم إنشاء رمز تحقق جديد للمستخدم: ${targetUser.username}`);
            return res.json({
              message: "تم إرسال رمز التحقق",
              step: 1,
              totalSteps: 3,
              verificationCode: newVerificationCode
            });

          case 'verify_code':
            // التحقق من الرمز
            const [verification] = await db
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

            if (!verification || verification.code !== verificationCode) {
              logger.warn(`رمز تحقق غير صالح للمستخدم: ${targetUser.username}`);
              return res.status(400).json({ message: "رمز التحقق غير صحيح" });
            }

            if (new Date() > verification.expiresAt) {
              logger.warn(`رمز تحقق منتهي الصلاحية للمستخدم: ${targetUser.username}`);
              return res.status(400).json({ message: "انتهت صلاحية رمز التحقق" });
            }

            // تحديث حالة التحقق
            await db
              .update(verificationCodes)
              .set({
                verified: true,
                verifiedAt: new Date(),
                verificationStep: verification.verificationStep + 1
              })
              .where(eq(verificationCodes.id, verification.id));

            // تحديث سجل تغيير الصلاحيات
            await db
              .update(roleChangeHistory)
              .set({
                step2CompletedAt: new Date()
              })
              .where(eq(roleChangeHistory.verificationId, verification.id));

            logger.info(`تم التحقق من الرمز بنجاح للمستخدم: ${targetUser.username}`);
            return res.json({
              message: "تم التحقق من الرمز بنجاح",
              step: 2,
              totalSteps: 3
            });

          case 'confirm':
            // تنفيذ تغيير الصلاحية
            await db
              .update(users)
              .set({
                role: newRole,
                roleChangeApproved: true,
                roleChangeApproverId: res.locals.admin.id,
                updatedAt: new Date()
              })
              .where(eq(users.id, userId));

            // تحديث سجل تغيير الصلاحيات
            await db
              .update(roleChangeHistory)
              .set({
                approvalStatus: "approved",
                approverId: res.locals.admin.id,
                approvedAt: new Date(),
                step3CompletedAt: new Date()
              })
              .where(
                and(
                  eq(roleChangeHistory.userId, userId),
                  eq(roleChangeHistory.approvalStatus, "pending")
                )
              );

            // إرسال إشعار
            if (targetUser.email) {
              await sendRoleChangeNotification(targetUser.email, newRole);
            }

            logger.info(`تم تغيير صلاحيات المستخدم بنجاح: ${targetUser.username} إلى ${newRole}`);
            return res.json({
              message: action === "promote"
                ? "تمت ترقية المستخدم إلى مشرف بنجاح"
                : "تم إلغاء صلاحيات الإشراف بنجاح",
              step: 3,
              totalSteps: 3
            });

          default:
            logger.warn(`خطوة تحقق غير صالحة: ${verificationStep}`);
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
          logger.info(`تمت الموافقة على المستخدم: ${targetUser.username}`);
          res.json({ message: "تمت الموافقة على المستخدم بنجاح" });
          break;

        case "block":
          await db
            .update(users)
            .set({ status: "blocked", updatedAt: new Date() })
            .where(eq(users.id, userId));
          logger.info(`تم حظر المستخدم: ${targetUser.username}`);
          res.json({ message: "تم حظر المستخدم بنجاح" });
          break;

        case "unblock":
          await db
            .update(users)
            .set({ status: "active", updatedAt: new Date() })
            .where(eq(users.id, userId));
          logger.info(`تم إلغاء حظر المستخدم: ${targetUser.username}`);
          res.json({ message: "تم إلغاء حظر المستخدم بنجاح" });
          break;

        default:
          logger.warn(`إجراء غير صالح: ${action}`);
          res.status(400).json({ message: "إجراء غير صالح" });
      }
    } catch (error) {
      logger.error('خطأ في تحديث حالة المستخدم:', error);
      res.status(500).json({ message: "خطأ في تحديث حالة المستخدم" });
    }
  });

  // نقطة نهاية اختبار لتغيير الصلاحيات
  app.post("/api/admin/test-role-change", isAdmin, async (req, res) => {
    try {
      const { userId, action, verificationStep, verificationCode } = req.body;
      logger.info(`بدء اختبار تغيير الصلاحيات:
        المستخدم: ${userId}
        الإجراء: ${action}
        الخطوة: ${verificationStep}
        الرمز: ${verificationCode ? '****' : 'غير متوفر'}`
      );

      // التحقق من البيانات المطلوبة
      if (!userId || !action) {
        logger.warn("بيانات غير مكتملة في طلب اختبار تغيير الصلاحيات");
        return res.status(400).json({ message: "يجب توفير معرف المستخدم والإجراء المطلوب" });
      }

      // محاكاة عملية تغيير الصلاحيات
      const requestUrl = `http://localhost:5000/api/admin/users/${userId}/${action}`;
      logger.info(`إرسال طلب إلى: ${requestUrl}`);

      const response = await fetch(requestUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          verificationStep,
          verificationCode,
          reason: "اختبار نظام تغيير الصلاحيات"
        })
      });

      const result = await response.json();
      logger.info(`تم استلام الرد من نظام تغيير الصلاحيات: ${JSON.stringify(result)}`);
      res.json(result);

    } catch (error) {
      logger.error('خطأ في اختبار تغيير الصلاحيات:', error);
      res.status(500).json({ message: "خطأ في اختبار تغيير الصلاحيات" });
    }
  });

  // إنشاء وإرجاع الخادم
  const httpServer = createServer(app);
  return httpServer;
}