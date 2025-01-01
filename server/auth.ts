import passport from "passport";
import { IVerifyOptions, Strategy as LocalStrategy } from "passport-local";
import { type Express } from "express";
import session from "express-session";
import createMemoryStore from "memorystore";
import { scrypt, randomBytes, timingSafeEqual } from "crypto";
import { promisify } from "util";
import { users, insertUserSchema } from "@db/schema";
import { db } from "@db";
import { eq } from "drizzle-orm";

const scryptAsync = promisify(scrypt);
const crypto = {
  hash: async (password: string) => {
    const salt = randomBytes(16).toString("hex");
    const buf = (await scryptAsync(password, salt, 64)) as Buffer;
    return `${buf.toString("hex")}.${salt}`;
  },
  compare: async (suppliedPassword: string, storedPassword: string) => {
    const [hashedPassword, salt] = storedPassword.split(".");
    const hashedPasswordBuf = Buffer.from(hashedPassword, "hex");
    const suppliedPasswordBuf = (await scryptAsync(
      suppliedPassword,
      salt,
      64
    )) as Buffer;
    return timingSafeEqual(hashedPasswordBuf, suppliedPasswordBuf);
  },
};

// تعريف نوع المستخدم
type User = {
  id: number;
  username: string;
  role: string;
  isApproved: boolean;
  status: string;
};

// تمديد كائن المستخدم في Express
declare global {
  namespace Express {
    interface User extends User {}
  }
}

// التحقق من صلاحيات المشرف
const isAdmin = (req: Express.Request, res: Express.Response, next: Express.NextFunction) => {
  if (req.isAuthenticated() && req.user.role === "admin") {
    return next();
  }
  res.status(403).send("غير مصرح بالوصول");
};

export function setupAuth(app: Express) {
  const MemoryStore = createMemoryStore(session);
  const sessionSettings: session.SessionOptions = {
    secret: process.env.SECRET_KEY || "silvarium-social-secret",
    resave: false,
    saveUninitialized: false,
    cookie: {},
    store: new MemoryStore({
      checkPeriod: 86400000, // تنظيف الجلسات المنتهية كل 24 ساعة
    }),
  };

  if (app.get("env") === "production") {
    app.set("trust proxy", 1);
    sessionSettings.cookie = {
      secure: true,
    };
  }

  app.use(session(sessionSettings));
  app.use(passport.initialize());
  app.use(passport.session());

  passport.use(
    new LocalStrategy(async (username, password, done) => {
      try {
        const [user] = await db
          .select()
          .from(users)
          .where(eq(users.username, username))
          .limit(1);

        if (!user) {
          return done(null, false, { message: "اسم المستخدم غير صحيح" });
        }

        // التحقق من حالة الحساب
        if (user.status === "blocked") {
          return done(null, false, { message: "تم حظر الحساب" });
        }

        if (!user.isApproved) {
          return done(null, false, { message: "الحساب في انتظار الموافقة" });
        }

        const isMatch = await crypto.compare(password, user.password);
        if (!isMatch) {
          return done(null, false, { message: "كلمة المرور غير صحيحة" });
        }
        return done(null, user);
      } catch (err) {
        return done(err);
      }
    })
  );

  passport.serializeUser((user, done) => {
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

  // التسجيل العادي للمستخدمين
  app.post("/api/register", async (req, res, next) => {
    try {
      const result = insertUserSchema.safeParse(req.body);
      if (!result.success) {
        return res
          .status(400)
          .send("بيانات غير صحيحة: " + result.error.issues.map(i => i.message).join(", "));
      }

      const { username, password } = result.data;

      // التحقق من وجود المستخدم
      const [existingUser] = await db
        .select()
        .from(users)
        .where(eq(users.username, username))
        .limit(1);

      if (existingUser) {
        return res.status(400).send("اسم المستخدم موجود بالفعل");
      }

      // تشفير كلمة المرور
      const hashedPassword = await crypto.hash(password);

      // إنشاء المستخدم الجديد
      const [newUser] = await db
        .insert(users)
        .values({
          username,
          password: hashedPassword,
          role: "user",
          isApproved: false,
          status: "pending"
        })
        .returning();

      return res.json({
        message: "تم التسجيل بنجاح. في انتظار موافقة المشرف",
        user: { id: newUser.id, username: newUser.username, status: newUser.status },
      });
    } catch (error) {
      next(error);
    }
  });

  // واجهات برمجة تطبيقات المشرف
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

  // تسجيل الدخول
  app.post("/api/login", (req, res, next) => {
    const result = insertUserSchema.safeParse(req.body);
    if (!result.success) {
      return res
        .status(400)
        .send("بيانات غير صحيحة: " + result.error.issues.map(i => i.message).join(", "));
    }

    const cb = (err: any, user: Express.User, info: IVerifyOptions) => {
      if (err) {
        return next(err);
      }

      if (!user) {
        return res.status(400).send(info.message ?? "فشل تسجيل الدخول");
      }

      req.logIn(user, (err) => {
        if (err) {
          return next(err);
        }

        return res.json({
          message: "تم تسجيل الدخول بنجاح",
          user: { id: user.id, username: user.username },
        });
      });
    };
    passport.authenticate("local", cb)(req, res, next);
  });

  app.post("/api/logout", (req, res) => {
    req.logout((err) => {
      if (err) {
        return res.status(500).send("فشل تسجيل الخروج");
      }

      res.json({ message: "تم تسجيل الخروج بنجاح" });
    });
  });

  app.get("/api/user", (req, res) => {
    if (req.isAuthenticated()) {
      return res.json(req.user);
    }

    res.status(401).send("لم يتم تسجيل الدخول");
  });
}