import { z } from "zod";

// نوع لنتيجة التحقق من صلاحيات المشرف
export const adminPermissionsSchema = z.object({
  isAdmin: z.boolean(),
  role: z.enum(["admin", "user"]),
  isApproved: z.boolean(),
  status: z.enum(["active", "pending", "blocked"])
});

export type AdminPermissions = z.infer<typeof adminPermissionsSchema>;

// نوع لطلب تغيير الصلاحيات
export const roleChangeRequestSchema = z.object({
  userId: z.number(),
  newRole: z.enum(["admin", "user"]),
  adminEmail: z.string().email(),
  verificationCode: z.string().optional()
});

export type RoleChangeRequest = z.infer<typeof roleChangeRequestSchema>;

// نوع لحالة التحقق من تغيير الصلاحيات
export const verificationStatusSchema = z.object({
  step: z.number(),
  totalSteps: z.number(),
  message: z.string(),
  verificationCode: z.string().optional()
});

export type VerificationStatus = z.infer<typeof verificationStatusSchema>;
