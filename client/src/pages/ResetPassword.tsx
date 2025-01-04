import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocation } from "wouter";
import { 
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle 
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useState, useEffect } from "react";
import { Languages } from "lucide-react";
import { auth } from "@/lib/firebase";
import { RecaptchaVerifier, signInWithPhoneNumber } from "firebase/auth";
import { Alert, AlertDescription } from "@/components/ui/alert";

const translations = {
  ar: {
    title: "إعادة تعيين كلمة المرور",
    description: "أدخل رقم الهاتف للتحقق ثم أدخل كلمة المرور الجديدة",
    username: "اسم المستخدم",
    usernamePlaceholder: "أدخل اسم المستخدم",
    phoneNumber: "رقم الهاتف",
    phoneNumberPlaceholder: "أدخل رقم الهاتف (مثال: +966123456789)",
    verificationCode: "رمز التحقق",
    verificationCodePlaceholder: "أدخل رمز التحقق المرسل",
    password: "كلمة المرور الجديدة",
    passwordPlaceholder: "أدخل كلمة المرور الجديدة",
    confirmPassword: "تأكيد كلمة المرور",
    confirmPasswordPlaceholder: "أدخل كلمة المرور مرة أخرى",
    sendCode: "إرسال رمز التحقق",
    verify: "تحقق من الرمز",
    resetButton: "إعادة تعيين كلمة المرور",
    backToLogin: "العودة لتسجيل الدخول",
    resetting: "جاري إعادة التعيين...",
    sending: "جاري إرسال الرمز...",
    verifying: "جاري التحقق...",
    restrictedUser: "عذراً، هذه الوظيفة متاحة فقط للمستخدم Tariq",
    errors: {
      usernameRequired: "اسم المستخدم مطلوب",
      phoneRequired: "رقم الهاتف مطلوب",
      codeRequired: "رمز التحقق مطلوب",
      passwordRequired: "كلمة المرور يجب أن تكون 8 أحرف على الأقل",
      confirmRequired: "تأكيد كلمة المرور مطلوب",
      passwordMismatch: "كلمات المرور غير متطابقة",
      invalidPhone: "رقم الهاتف غير صالح",
      userNotFound: "المستخدم غير موجود"
    },
    success: {
      title: "تم إعادة تعيين كلمة المرور بنجاح",
      description: "يمكنك الآن تسجيل الدخول باستخدام كلمة المرور الجديدة"
    },
    error: {
      title: "حدث خطأ",
      description: "يرجى التحقق من البيانات والمحاولة مرة أخرى"
    },
    verification: {
      codeSent: "تم إرسال رمز التحقق",
      codeSentDesc: "يرجى إدخال الرمز المرسل إلى هاتفك",
      success: "تم التحقق بنجاح",
      error: "خطأ في التحقق من الرمز"
    }
  }
};

type ResetStep = 'phone' | 'verify' | 'reset';

export default function ResetPassword() {
  const [_, setLocation] = useLocation();
  const { toast } = useToast();
  const [step, setStep] = useState<ResetStep>('phone');
  const [verificationId, setVerificationId] = useState<string>("");
  const t = translations.ar;

  // Reset Password form schemas
  const phoneSchema = z.object({
    username: z.string().min(1, t.errors.usernameRequired),
    phoneNumber: z.string().min(1, t.errors.phoneRequired),
  });

  const verifySchema = z.object({
    code: z.string().min(1, t.errors.codeRequired),
  });

  const resetSchema = z.object({
    password: z.string().min(8, t.errors.passwordRequired),
    confirmPassword: z.string().min(1, t.errors.confirmRequired),
  }).refine((data) => data.password === data.confirmPassword, {
    message: t.errors.passwordMismatch,
    path: ["confirmPassword"],
  });

  // Form instances
  const phoneForm = useForm({
    resolver: zodResolver(phoneSchema),
    defaultValues: {
      username: "",
      phoneNumber: "",
    },
  });

  const verifyForm = useForm({
    resolver: zodResolver(verifySchema),
    defaultValues: {
      code: "",
    },
  });

  const resetForm = useForm({
    resolver: zodResolver(resetSchema),
    defaultValues: {
      password: "",
      confirmPassword: "",
    },
  });

  // Firebase reCAPTCHA setup
  useEffect(() => {
    if (step === 'phone') {
      const setupRecaptcha = async () => {
        try {
          window.recaptchaVerifier = new RecaptchaVerifier(auth, 'send-code-button', {
            'size': 'invisible'
          });
        } catch (error) {
          console.error('Error setting up reCAPTCHA:', error);
        }
      };
      setupRecaptcha();
    }
  }, [step]);

  // Form submission handlers
  const onSendCode = async (data: { username: string; phoneNumber: string }) => {
    try {
      // Check if user is Tariq
      if (data.username.toLowerCase() !== 'tariq') {
        toast({
          variant: "destructive",
          title: t.error.title,
          description: t.restrictedUser,
        });
        return;
      }

      const phoneNumber = data.phoneNumber;
      const appVerifier = window.recaptchaVerifier;

      const confirmationResult = await signInWithPhoneNumber(auth, phoneNumber, appVerifier);
      setVerificationId(confirmationResult.verificationId);
      setStep('verify');

      toast({
        title: t.verification.codeSent,
        description: t.verification.codeSentDesc,
      });
    } catch (error) {
      console.error('Error sending code:', error);
      toast({
        variant: "destructive",
        title: t.error.title,
        description: (error as Error).message,
      });

      // Reset reCAPTCHA on error
      if (window.recaptchaVerifier) {
        window.recaptchaVerifier.clear();
        window.recaptchaVerifier = null;
      }
    }
  };

  const onVerifyCode = async (data: { code: string }) => {
    try {
      const response = await fetch('/api/auth/verify-phone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phoneNumber: phoneForm.getValues('phoneNumber'),
          code: data.code,
          verificationId
        }),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      setStep('reset');
      toast({
        title: t.verification.success,
        description: t.verification.success,
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: t.error.title,
        description: (error as Error).message,
      });
    }
  };

  const onResetPassword = async (data: { password: string; confirmPassword: string }) => {
    try {
      const response = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: phoneForm.getValues('username'),
          password: data.password,
          verificationId
        }),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      toast({
        title: t.success.title,
        description: t.success.description,
      });

      setLocation("/");
    } catch (error) {
      toast({
        variant: "destructive",
        title: t.error.title,
        description: (error as Error).message,
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4" dir="rtl">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl font-bold">{t.title}</CardTitle>
          <CardDescription>
            {t.description}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {step === 'phone' && (
            <Form {...phoneForm}>
              <form onSubmit={phoneForm.handleSubmit(onSendCode)} className="space-y-6">
                <FormField
                  control={phoneForm.control}
                  name="username"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t.username}</FormLabel>
                      <FormControl>
                        <Input 
                          placeholder={t.usernamePlaceholder}
                          {...field} 
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={phoneForm.control}
                  name="phoneNumber"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t.phoneNumber}</FormLabel>
                      <FormControl>
                        <Input 
                          placeholder={t.phoneNumberPlaceholder}
                          type="tel"
                          {...field} 
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="space-y-2">
                  <Button 
                    type="submit" 
                    className="w-full"
                    id="send-code-button"
                    disabled={phoneForm.formState.isSubmitting}
                  >
                    {phoneForm.formState.isSubmitting ? t.sending : t.sendCode}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() => setLocation("/")}
                  >
                    {t.backToLogin}
                  </Button>
                </div>
              </form>
            </Form>
          )}

          {step === 'verify' && (
            <Form {...verifyForm}>
              <form onSubmit={verifyForm.handleSubmit(onVerifyCode)} className="space-y-6">
                <FormField
                  control={verifyForm.control}
                  name="code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t.verificationCode}</FormLabel>
                      <FormControl>
                        <Input 
                          placeholder={t.verificationCodePlaceholder}
                          {...field} 
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button 
                  type="submit" 
                  className="w-full"
                  disabled={verifyForm.formState.isSubmitting}
                >
                  {verifyForm.formState.isSubmitting ? t.verifying : t.verify}
                </Button>
              </form>
            </Form>
          )}

          {step === 'reset' && (
            <Form {...resetForm}>
              <form onSubmit={resetForm.handleSubmit(onResetPassword)} className="space-y-6">
                <FormField
                  control={resetForm.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t.password}</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder={t.passwordPlaceholder}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={resetForm.control}
                  name="confirmPassword"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t.confirmPassword}</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder={t.confirmPasswordPlaceholder}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button 
                  type="submit" 
                  className="w-full"
                  disabled={resetForm.formState.isSubmitting}
                >
                  {resetForm.formState.isSubmitting ? t.resetting : t.resetButton}
                </Button>
              </form>
            </Form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}