// Previous imports remain unchanged
import { db } from "@db";
import { users, verificationCodes } from "@db/schema";
import { eq, and } from "drizzle-orm";

export function registerRoutes(app: Express): Server {
  // Previous middleware and setup remain unchanged

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
        return res.status(404).send("المستخدم غير موجود");
      }

      // التحقق من مراحل تغيير الصلاحيات
      if (action === "promote" || action === "demote") {
        switch (verificationStep) {
          case 'initial':
            // التحقق من وجود البريد الإلكتروني
            if (!user.email) {
              return res.status(400).send("يجب إضافة بريد إلكتروني للمستخدم أولاً");
            }
            break;

          case 'email_sent':
            // التحقق من صحة الرمز
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
              return res.status(400).send("لم يتم العثور على رمز تحقق صالح");
            }

            if (verificationRecord.code !== verificationCode) {
              return res.status(400).send("رمز التحقق غير صحيح");
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
            return res.status(400).send("خطوة تحقق غير صالحة");
        }
      }

      // باقي الإجراءات تبقى كما هي
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
          res.status(400).send("إجراء غير صالح");
      }
    } catch (error) {
      console.error('Error updating user role:', error);
      res.status(500).send("خطأ في تحديث حالة المستخدم");
    }
  });

  // باقي نقاط النهاية تبقى كما هي

  const httpServer = createServer(app);
  return httpServer;
}
