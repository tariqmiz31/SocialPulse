import type { Express } from "express";
import { createServer, type Server } from "http";
import { db } from "@db";
import { users, verificationCodes } from "@db/schema";
import { eq, and } from "drizzle-orm";
import express from "express";
import session from "express-session";
import passport from "passport";
import { Strategy as LocalStrategy } from "passport-local";
import { compare } from "bcrypt";
import createMemoryStore from "memorystore";
import nodemailer from "nodemailer";
import { randomBytes } from "crypto";

// إعداد البريد الإلكتروني مع بيانات الاعتماد
const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.MAIL_USERNAME || 'silvariumsa@gmail.com',
    pass: process.env.MAIL_PASSWORD || 'rtbkamqrxsptmbrl'
  }
});

// التحقق من اتصال البريد الإلكتروني
transporter.verify(function(error, success) {
  if (error) {
    console.log('خطأ في إعداد البريد الإلكتروني:', error);
  } else {
    console.log('تم إعداد خادم البريد الإلكتروني بنجاح');
  }
});

async function sendVerificationEmail(email: string, code: string) {
  const mailOptions = {
    from: '"سيلفاريوم سوشيال" <silvariumsa@gmail.com>',
    to: email,
    subject: 'تأكيد البريد الإلكتروني - سيلفاريوم سوشيال',
    html: `
      <div dir="rtl" style="text-align: right; font-family: Arial, sans-serif;">
        <h2>مرحباً بك في سيلفاريوم سوشيال</h2>
        <p>شكراً لتسجيلك معنا. للتحقق من بريدك الإلكتروني، يرجى إدخال الرمز التالي في التطبيق:</p>
        <div style="background-color: #f4f4f4; padding: 15px; margin: 20px 0; font-size: 24px; text-align: center;">
          ${code}
        </div>
        <p>هذا الرمز صالح لمدة 24 ساعة.</p>
        <p>إذا لم تقم بطلب هذا التحقق، يرجى تجاهل هذا البريد الإلكتروني.</p>
        <p>مع تحيات فريق سيلفاريوم سوشيال</p>
      </div>
    `
  };

  try {
    await transporter.sendMail(mailOptions);
    console.log('تم إرسال بريد التحقق إلى:', email);
    return true;
  } catch (error) {
    console.error('خطأ في إرسال البريد الإلكتروني:', error);
    throw error;
  }
}

async function sendRoleChangeNotification(email: string, newRole: string) {
  const mailOptions = {
    from: '"سيلفاريوم سوشيال" <silvariumsa@gmail.com>',
    to: email,
    subject: 'تحديث صلاحيات المستخدم - سيلفاريوم سوشيال',
    html: `
      <div dir="rtl" style="text-align: right; font-family: Arial, sans-serif;">
        <h2>تحديث صلاحيات المستخدم</h2>
        <p>تم تحديث صلاحياتك في نظام سيلفاريوم سوشيال.</p>
        <p>الصلاحية الجديدة: ${newRole === 'admin' ? 'مشرف' : 'مستخدم عادي'}</p>
        <p>إذا لم تكن تتوقع هذا التغيير، يرجى التواصل مع إدارة النظام فوراً.</p>
        <p>مع تحيات فريق سيلفاريوم سوشيال</p>
      </div>
    `
  };

  try {
    await transporter.sendMail(mailOptions);
    console.log('تم إرسال إشعار تغيير الصلاحيات إلى:', email);
    return true;
  } catch (error) {
    console.error('خطأ في إرسال البريد الإلكتروني:', error);
    throw error;
  }
}

async function isAdmin(req: any, res: any, next: any) {
    if (req.isAuthenticated() && req.user.role === "admin") {
      return next();
    }
    res.status(403).send("غير مصرح بالوصول");
  };

export function registerRoutes(app: Express): Server {
  // تكوين الجلسة
  const MemoryStore = createMemoryStore(session);
  const sessionMiddleware = session({
    secret: process.env.SESSION_SECRET || 'your-secret-key',
    resave: false,
    saveUninitialized: false,
    store: new MemoryStore({
      checkPeriod: 86400000 // 24 hours
    }),
    cookie: {
      secure: process.env.NODE_ENV === 'production',
      maxAge: 24 * 60 * 60 * 1000 // 24 hours
    }
  });

  app.use(sessionMiddleware);
  app.use(passport.initialize());
  app.use(passport.session());

  // نقاط نهاية التحقق من البريد الإلكتروني
  app.post("/api/auth/send-verification-code", async (req, res) => {
    const { email, username } = req.body;

    try {
      const [existingUser] = await db
        .select()
        .from(users)
        .where(eq(users.username, username))
        .limit(1);

      if (!existingUser) {
        return res.status(404).send("المستخدم غير موجود");
      }

      // توليد رمز تحقق جديد
      const code = randomBytes(3).toString("hex").toUpperCase();
      const expiresAt = new Date();
      expiresAt.setHours(expiresAt.getHours() + 24);

      await db.insert(verificationCodes).values({
        userId: existingUser.id,
        code,
        type: "email_verification",
        expiresAt,
      });

      // إرسال البريد الإلكتروني
      await sendVerificationEmail(email, code);

      res.json({ message: "تم إرسال رمز التحقق" });
    } catch (error) {
      console.error('Error sending verification email:', error);
      res.status(500).send("حدث خطأ أثناء إرسال رمز التحقق");
    }
  });

  app.post("/api/auth/verify-email", async (req, res) => {
    const { email, code, username } = req.body;

    try {
      const [verificationRecord] = await db
        .select()
        .from(verificationCodes)
        .where(
          and(
            eq(verificationCodes.code, code),
            eq(verificationCodes.type, "email_verification")
          )
        )
        .limit(1);

      if (!verificationRecord) {
        return res.status(400).send("رمز التحقق غير صالح");
      }

      if (new Date() > verificationRecord.expiresAt) {
        return res.status(400).send("رمز التحقق منتهي الصلاحية");
      }

      // تحديث حالة التحقق
      await db.transaction(async (tx) => {
        await tx
          .update(verificationCodes)
          .set({ verified: true })
          .where(eq(verificationCodes.id, verificationRecord.id));

        await tx
          .update(users)
          .set({ 
            email,
            emailVerified: true 
          })
          .where(eq(users.username, username));
      });

      res.json({ message: "تم تأكيد البريد الإلكتروني بنجاح" });
    } catch (error) {
      console.error('Error verifying email:', error);
      res.status(500).send("حدث خطأ أثناء التحقق من البريد الإلكتروني");
    }
  });

  // تحديث نقطة نهاية ترقية/تخفيض المستخدم لإضافة الإشعارات
  app.post("/api/admin/users/:userId/:action", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      const action = req.params.action;

      const [user] = await db
        .select()
        .from(users)
        .where(eq(users.id, userId))
        .limit(1);

      if (!user) {
        return res.status(404).send("المستخدم غير موجود");
      }

      switch (action) {
        case "promote":
          await db
            .update(users)
            .set({ role: "admin" })
            .where(eq(users.id, userId));

          if (user.email) {
            await sendRoleChangeNotification(user.email, "admin");
          }

          res.json({ message: "تمت ترقية المستخدم إلى مشرف بنجاح" });
          break;

        case "demote":
          await db
            .update(users)
            .set({ role: "user" })
            .where(eq(users.id, userId));

          if (user.email) {
            await sendRoleChangeNotification(user.email, "user");
          }

          res.json({ message: "تم إلغاء صلاحيات الإشراف بنجاح" });
          break;
        case "approve":
          await db
            .update(users)
            .set({ isApproved: true, status: "active" })
            .where(eq(users.id, userId));
          res.json({ message: "تمت الموافقة على المستخدم بنجاح" });
          break;
        case "block":
          await db
            .update(users)
            .set({ status: "blocked" })
            .where(eq(users.id, userId));
          res.json({ message: "تم حظر المستخدم بنجاح" });
          break;
        case "unblock":
          await db
            .update(users)
            .set({ status: "active" })
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

  // نقاط النهاية للمصادقة
  app.post("/api/login", passport.authenticate("local"), (req, res) => {
    res.json({ user: req.user });
  });

  app.post("/api/logout", (req, res) => {
    req.logout(() => {
      res.json({ message: "تم تسجيل الخروج بنجاح" });
    });
  });

  app.get("/api/user", (req, res) => {
    if (req.isAuthenticated()) {
      res.json(req.user);
    } else {
      res.status(401).send("غير مسجل الدخول");
    }
  });

  // نقاط نهاية لوحة الإدارة
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


  // نقطة نهاية الحالة الأساسية
  app.get("/api/status", (_req, res) => {
    res.json({
      status: "running",
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV,
      auth_method: "admin_approval_required"
    });
  });

  // Email verification endpoints (already added above)

  const httpServer = createServer(app);
  return httpServer;
}