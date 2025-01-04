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
import { useState } from "react";
import { Languages } from "lucide-react";
import { auth } from "@/lib/firebase";
import { RecaptchaVerifier, signInWithPhoneNumber } from "firebase/auth";

const translations = {
  ar: {
    title: "إعادة تعيين كلمة المرور",
    description: "أدخل رقم الهاتف للتحقق ثم أدخل كلمة المرور الجديدة",
    username: "اسم المستخدم",
    usernamePlaceholder: "أدخل اسم المستخدم",
    phoneNumber: "رقم الهاتف",
    phoneNumberPlaceholder: "أدخل رقم الهاتف",
    verificationCode: "رمز التحقق",
    verificationCodePlaceholder: "أدخل رمز التحقق",
    password: "كلمة المرور الجديدة",
    passwordPlaceholder: "أدخل كلمة المرور الجديدة",
    confirmPassword: "تأكيد كلمة المرور",
    confirmPasswordPlaceholder: "أدخل كلمة المرور مرة أخرى",
    sendCode: "إرسال رمز التحقق",
    verify: "تحقق من الرمز",
    resetButton: "إعادة تعيين كلمة المرور",
    resetting: "جاري إعادة التعيين...",
    sending: "جاري إرسال الرمز...",
    verifying: "جاري التحقق...",
    errors: {
      usernameRequired: "اسم المستخدم مطلوب",
      phoneRequired: "رقم الهاتف مطلوب",
      codeRequired: "رمز التحقق مطلوب",
      passwordRequired: "كلمة المرور يجب أن تكون 8 أحرف على الأقل",
      confirmRequired: "تأكيد كلمة المرور مطلوب",
      passwordMismatch: "كلمات المرور غير متطابقة",
      invalidPhone: "رقم الهاتف غير صالح"
    },
    success: "تم إعادة تعيين كلمة المرور بنجاح",
    successDesc: "يمكنك الآن تسجيل الدخول باستخدام كلمة المرور الجديدة",
    error: "خطأ في إعادة تعيين كلمة المرور",
    errorDesc: "يرجى التحقق من البيانات والمحاولة مرة أخرى",
    codeSent: "تم إرسال رمز التحقق",
    codeSentDesc: "يرجى إدخال الرمز المرسل إلى هاتفك",
    verificationSuccess: "تم التحقق بنجاح",
    verificationError: "خطأ في التحقق من الرمز"
  },
  en: {
    title: "Reset Password",
    description: "Enter your phone number to verify then enter your new password",
    username: "Username",
    usernamePlaceholder: "Enter username",
    phoneNumber: "Phone Number",
    phoneNumberPlaceholder: "Enter phone number",
    verificationCode: "Verification Code",
    verificationCodePlaceholder: "Enter verification code",
    password: "New Password",
    passwordPlaceholder: "Enter new password",
    confirmPassword: "Confirm Password",
    confirmPasswordPlaceholder: "Enter password again",
    sendCode: "Send Code",
    verify: "Verify Code",
    resetButton: "Reset Password",
    resetting: "Resetting...",
    sending: "Sending code...",
    verifying: "Verifying...",
    errors: {
      usernameRequired: "Username is required",
      phoneRequired: "Phone number is required",
      codeRequired: "Verification code is required",
      passwordRequired: "Password must be at least 8 characters",
      confirmRequired: "Password confirmation is required",
      passwordMismatch: "Passwords do not match",
      invalidPhone: "Invalid phone number"
    },
    success: "Password Reset Successful",
    successDesc: "You can now login with your new password",
    error: "Password Reset Failed",
    errorDesc: "Please check your information and try again",
    codeSent: "Verification Code Sent",
    codeSentDesc: "Please enter the code sent to your phone",
    verificationSuccess: "Verification Successful",
    verificationError: "Verification Failed"
  }
};

type ResetStep = 'phone' | 'verify' | 'reset';

export default function ResetPassword() {
  const [_, setLocation] = useLocation();
  const { toast } = useToast();
  const [lang, setLang] = useState<'ar' | 'en'>('ar');
  const [step, setStep] = useState<ResetStep>('phone');
  const [verificationId, setVerificationId] = useState<string>("");
  const t = translations[lang];

  const phoneSchema = z.object({
    username: z.string().min(1, t.errors.usernameRequired),
    phoneNumber: z.string().min(1, t.errors.phoneRequired),
  });

  const verifySchema = z.object({
    code: z.string().min(1, t.errors.codeRequired),
  });

  const resetSchema = z.object({
    password: z.string().min(8, t.errors.passwordRequired),
    confirmPassword: z.string().min(8, t.errors.confirmRequired),
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

  async function setupRecaptcha() {
    const recaptchaVerifier = new RecaptchaVerifier(auth, 'send-code-button', {
      'size': 'invisible'
    });
    return recaptchaVerifier;
  }

  const onSendCode = async (data: { username: string, phoneNumber: string }) => {
    try {
      const recaptchaVerifier = await setupRecaptcha();
      const confirmationResult = await signInWithPhoneNumber(
        auth,
        data.phoneNumber,
        recaptchaVerifier
      );
      setVerificationId(confirmationResult.verificationId);
      setStep('verify');
      toast({
        title: t.codeSent,
        description: t.codeSentDesc,
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: t.errors.invalidPhone,
        description: (error as Error).message,
      });
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
        title: t.verificationSuccess,
        description: t.verificationSuccess,
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: t.verificationError,
        description: (error as Error).message,
      });
    }
  };

  const onResetPassword = async (data: { password: string, confirmPassword: string }) => {
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
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      toast({
        title: t.success,
        description: t.successDesc,
      });
      setLocation("/login");
    } catch (error) {
      toast({
        variant: "destructive",
        title: t.error,
        description: (error as Error).message,
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="text-2xl font-bold">{t.title}</CardTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
              className="h-8 w-8"
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
                  id="send-code-button"
                  disabled={phoneForm.formState.isSubmitting}
                >
                  {phoneForm.formState.isSubmitting ? t.sending : t.sendCode}
                </Button>
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