import nodemailer from "nodemailer";

const transporter = nodemailer.createTransport({
  host: "smtp.gmail.com",
  port: 587,
  secure: false,
  auth: {
    user: process.env.MAIL_USERNAME,
    pass: process.env.MAIL_PASSWORD,
  },
});

export interface MailOptions {
  to: string;
  subject: string;
  html: string;
}

export async function sendMail(options: MailOptions): Promise<void> {
  try {
    await transporter.sendMail({
      from: process.env.MAIL_USERNAME,
      ...options
    });
  } catch (error) {
    console.error('Error sending email:', error);
    throw new Error('Failed to send email');
  }
}

export async function sendRoleChangeNotification(email: string, newRole: string): Promise<void> {
  const subject = newRole === "admin" 
    ? "تمت ترقيتك إلى مشرف"
    : "تم تغيير صلاحياتك إلى مستخدم عادي";

  const html = `
    <div dir="rtl" style="font-family: Arial, sans-serif; line-height: 1.6;">
      <h2>${subject}</h2>
      <p>مرحباً،</p>
      <p>نود إخبارك أنه تم تغيير صلاحياتك في النظام.</p>
      <p>دورك الجديد: <strong>${newRole === "admin" ? "مشرف" : "مستخدم عادي"}</strong></p>
      <p>إذا لم تكن تتوقع هذا التغيير، يرجى التواصل مع إدارة النظام فوراً.</p>
      <br>
      <p>مع التحية،<br>فريق سيلفاريوم</p>
    </div>
  `;

  await sendMail({ to: email, subject, html });
}