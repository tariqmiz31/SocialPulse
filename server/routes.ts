import type { Express } from "express";
import { createServer, type Server } from "http";
import { db } from "@db";
import { users, verificationCodes } from "@db/schema";
import { eq } from "drizzle-orm";
import express from "express";
import session from "express-session";
import passport from "passport";
import { Strategy as LocalStrategy } from "passport-local";
import { compare } from "bcrypt";
import createMemoryStore from "memorystore";
import helmet from "helmet";
import cors from "cors";
import compression from "compression";
import rateLimit from "express-rate-limit";
import { randomBytes } from "crypto";
import nodemailer from "nodemailer";

// إعداد البريد الإلكتروني
const transporter = nodemailer.createTransport({
  host: process.env.MAIL_SERVER || 'smtp.gmail.com',
  port: parseInt(process.env.MAIL_PORT || '587'),
  secure: false,
  auth: {
    user: process.env.MAIL_USERNAME,
    pass: process.env.MAIL_PASSWORD
  }
});

async function sendVerificationEmail(email: string, code: string) {
  const mailOptions = {
    from: process.env.MAIL_DEFAULT_SENDER || 'no-reply@silvariumsocial.com',
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

  await transporter.sendMail(mailOptions);
}

// إعداد المصادقة
const MemoryStore = createMemoryStore(session);

export function registerRoutes(app: Express): Server {
  // تكوين الجلسة
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

  // استراتيجية المصادقة المحلية
  passport.use(new LocalStrategy(async (username, password, done) => {
    try {
      const [user] = await db
        .select()
        .from(users)
        .where(eq(users.username, username))
        .limit(1);

      if (!user) {
        return done(null, false, { message: "اسم المستخدم غير صحيح" });
      }

      if (user.status === "blocked") {
        return done(null, false, { message: "هذا الحساب محظور" });
      }

      const isValidPassword = await compare(password, user.password);
      if (!isValidPassword) {
        return done(null, false, { message: "كلمة المرور غير صحيحة" });
      }

      return done(null, user);
    } catch (err) {
      return done(err);
    }
  }));

  passport.serializeUser((user: any, done) => {
    done(null, user.id);
  });

  passport.deserializeUser(async (id: number, done) => {
    try {
      const [user] = await db
        .select()
        .from(users)
        .where(eq(users.id, id))
        .limit(1);
      done(null, user);
    } catch (err) {
      done(err);
    }
  });

  // التحقق من صلاحيات المشرف
  const isAdmin = (req: any, res: any, next: any) => {
    if (req.isAuthenticated() && req.user.role === "admin") {
      return next();
    }
    res.status(403).send("غير مصرح بالوصول");
  };

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

  app.post("/api/admin/users/:userId/:action", isAdmin, async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      const action = req.params.action;

      switch (action) {
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
        case "promote":
          await db
            .update(users)
            .set({ role: "admin" })
            .where(eq(users.id, userId));
          res.json({ message: "تمت ترقية المستخدم إلى مشرف بنجاح" });
          break;
        case "demote":
          await db
            .update(users)
            .set({ role: "user" })
            .where(eq(users.id, userId));
          res.json({ message: "تم إلغاء صلاحيات الإشراف بنجاح" });
          break;
        default:
          res.status(400).send("إجراء غير صالح");
      }
    } catch (error) {
      res.status(500).send("خطأ في تحديث حالة المستخدم");
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

  // Email verification endpoints
  app.post("/api/verify-email", async (req, res) => {
    try {
      const { code } = req.body;

      const [verificationRecord] = await db
        .select()
        .from(verificationCodes)
        .where(eq(verificationCodes.code, code))
        .where(eq(verificationCodes.type, "email_verification"))
        .where(eq(verificationCodes.verified, false))
        .limit(1);

      if (!verificationRecord) {
        return res.status(400).send("رمز التحقق غير صالح");
      }

      if (new Date() > verificationRecord.expiresAt) {
        return res.status(400).send("رمز التحقق منتهي الصلاحية");
      }

      // Update verification status
      await db.transaction(async (tx) => {
        await tx
          .update(verificationCodes)
          .set({ verified: true })
          .where(eq(verificationCodes.id, verificationRecord.id));

        await tx
          .update(users)
          .set({ emailVerified: true })
          .where(eq(users.id, verificationRecord.userId));
      });

      res.json({ message: "تم تأكيد البريد الإلكتروني بنجاح" });
    } catch (error) {
      res.status(500).send("حدث خطأ أثناء التحقق من البريد الإلكتروني");
    }
  });

  app.post("/api/resend-verification", async (req, res) => {
    try {
      if (!req.isAuthenticated()) {
        return res.status(401).send("غير مصرح");
      }

      const user = req.user as any;
      if (!user.email) {
        return res.status(400).send("لم يتم تعيين البريد الإلكتروني");
      }

      if (user.emailVerified) {
        return res.status(400).send("البريد الإلكتروني مؤكد بالفعل");
      }

      // توليد رمز تحقق جديد
      const code = randomBytes(32).toString("hex").slice(0, 6);
      const expiresAt = new Date();
      expiresAt.setHours(expiresAt.getHours() + 24);

      await db.insert(verificationCodes).values({
        userId: user.id,
        code,
        type: "email_verification",
        expiresAt,
      });

      // إرسال البريد الإلكتروني
      await sendVerificationEmail(user.email, code);

      res.json({ message: "تم إرسال رمز التحقق الجديد" });
    } catch (error) {
      console.error('Error sending verification email:', error);
      res.status(500).send("حدث خطأ أثناء إعادة إرسال رمز التحقق");
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}