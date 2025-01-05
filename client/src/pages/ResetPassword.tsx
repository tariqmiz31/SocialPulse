import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocation } from "wouter";
import { useEffect, useState } from "react"; 
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
import { Languages, Loader2 } from "lucide-react";
import { setupRecaptcha, sendVerificationCode, verifyCode } from "@/lib/firebase";
import type { ConfirmationResult } from "firebase/auth";

// Translations | الترجمات
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
    switchLanguage: "Switch to English",
    errors: {
      usernameRequired: "اسم المستخدم مطلوب",
      phoneRequired: "رقم الهاتف مطلوب",
      codeRequired: "رمز التحقق مطلوب",
      passwordRequired: "كلمة المرور يجب أن تكون 8 أحرف على الأقل",
      confirmRequired: "تأكيد كلمة المرور مطلوب",
      passwordMismatch: "كلمات المرور غير متطابقة",
      invalidPhone: "رقم الهاتف غير صالح",
      userNotFound: "المستخدم غير موجود",
      recaptchaError: "خطأ في تهيئة reCAPTCHA",
      unknownError: "حدث خطأ غير معروف"
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
  },
  en: {
    title: "Reset Password",
    description: "Enter your phone number for verification, then set your new password",
    username: "Username",
    usernamePlaceholder: "Enter your username",
    phoneNumber: "Phone Number",
    phoneNumberPlaceholder: "Enter phone number (e.g. +966123456789)",
    verificationCode: "Verification Code",
    verificationCodePlaceholder: "Enter the verification code sent",
    password: "New Password",
    passwordPlaceholder: "Enter new password",
    confirmPassword: "Confirm Password",
    confirmPasswordPlaceholder: "Enter password again",
    sendCode: "Send Verification Code",
    verify: "Verify Code",
    resetButton: "Reset Password",
    backToLogin: "Back to Login",
    resetting: "Resetting...",
    sending: "Sending code...",
    verifying: "Verifying...",
    switchLanguage: "التحول للعربية",
    errors: {
      usernameRequired: "Username is required",
      phoneRequired: "Phone number is required",
      codeRequired: "Verification code is required",
      passwordRequired: "Password must be at least 8 characters",
      confirmRequired: "Password confirmation is required",
      passwordMismatch: "Passwords do not match",
      invalidPhone: "Invalid phone number",
      userNotFound: "User not found",
      recaptchaError: "Error initializing reCAPTCHA",
      unknownError: "An unknown error occurred"
    },
    success: {
      title: "Password Reset Successful",
      description: "You can now login with your new password"
    },
    error: {
      title: "Error Occurred",
      description: "Please check your information and try again"
    },
    verification: {
      codeSent: "Verification Code Sent",
      codeSentDesc: "Please enter the code sent to your phone",
      success: "Verification Successful",
      error: "Verification Failed"
    }
  }
};

type ResetStep = 'phone' | 'verify' | 'reset';

export default function ResetPassword() {
  const [_, setLocation] = useLocation();
  const { toast } = useToast();
  const [step, setStep] = useState<ResetStep>('phone');
  const [language, setLanguage] = useState<'ar' | 'en'>('ar');
  const [isLoading, setIsLoading] = useState(false);
  const t = translations[language];

  const phoneSchema = z.object({
    username: z.string().min(1, t.errors.usernameRequired),
    phoneNumber: z.string()
      .min(1, t.errors.phoneRequired)
      .regex(/^\+[1-9]\d{1,14}$/, t.errors.invalidPhone),
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

  const handleBilingualMessage = (response: any) => {
    if (response.message && typeof response.message === 'object') {
      return language === 'ar' ? response.message.ar : response.message.en;
    }
    return response.message || t.errors.unknownError;
  };

  const onSendCode = async (data: { username: string; phoneNumber: string }) => {
    try {
      setIsLoading(true);
      const phoneNumber = data.phoneNumber;

      const recaptchaVerifier = await setupRecaptcha('send-code-button');

      await sendVerificationCode(phoneNumber, recaptchaVerifier);

      setStep('verify');
      toast({
        title: t.verification.codeSent,
        description: t.verification.codeSentDesc,
      });
    } catch (error: any) {
      console.error('Error sending code:', error);
      toast({
        variant: "destructive",
        title: t.error.title,
        description: error.message || t.errors.unknownError,
      });

      if (window.recaptchaVerifier) {
        await window.recaptchaVerifier.clear();
        window.recaptchaVerifier = null;
      }
    } finally {
      setIsLoading(false);
    }
  };

  const onVerifyCode = async (data: { code: string }) => {
    try {
      setIsLoading(true);

      const result = await verifyCode(data.code);
      const idToken = await result.user.getIdToken();

      const response = await fetch('/api/auth/verify-phone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phoneNumber: phoneForm.getValues('phoneNumber'),
          verificationId: idToken
        }),
      });

      const apiResult = await response.json();

      if (!response.ok) {
        throw new Error(apiResult.message?.[language] || apiResult.message);
      }

      setStep('reset');
      toast({
        title: t.verification.success,
        description: apiResult.message?.[language] || apiResult.message,
      });
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: t.error.title,
        description: error.message || t.errors.unknownError,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const onResetPassword = async (data: { password: string; confirmPassword: string }) => {
    try {
      setIsLoading(true);
      const response = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: phoneForm.getValues('username'),
          password: data.password,
          verificationId: await auth.currentUser?.getIdToken() // Added this line
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(handleBilingualMessage(result));
      }

      toast({
        title: t.success.title,
        description: handleBilingualMessage(result),
      });

      setTimeout(() => setLocation("/"), 2000);
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: t.error.title,
        description: error.message || t.errors.unknownError,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4" dir={language === 'ar' ? 'rtl' : 'ltr'}>
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="text-2xl font-bold">{t.title}</CardTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setLanguage(language === 'ar' ? 'en' : 'ar')}
              className="h-8 w-8"
              title={t.switchLanguage}
            >
              <Languages className="h-4 w-4" />
            </Button>
          </div>
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
                    disabled={isLoading || phoneForm.formState.isSubmitting}
                  >
                    {isLoading || phoneForm.formState.isSubmitting ? (
                      <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t.sending}</>
                    ) : (
                      t.sendCode
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() => setLocation("/")}
                    disabled={isLoading}
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
                  disabled={isLoading || verifyForm.formState.isSubmitting}
                >
                  {isLoading || verifyForm.formState.isSubmitting ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t.verifying}</>
                  ) : (
                    t.verify
                  )}
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
                  disabled={isLoading || resetForm.formState.isSubmitting}
                >
                  {isLoading || resetForm.formState.isSubmitting ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t.resetting}</>
                  ) : (
                    t.resetButton
                  )}
                </Button>
              </form>
            </Form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}