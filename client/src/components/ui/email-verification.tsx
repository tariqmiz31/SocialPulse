import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OTPInput } from "@/components/ui/otp-input";
import { useToast } from "@/hooks/use-toast";

interface EmailVerificationProps {
  onVerificationComplete: (email: string) => void;
  onCancel?: () => void;
  action?: 'verify' | 'reset';
  username?: string;
}

export function EmailVerification({ 
  onVerificationComplete, 
  onCancel, 
  action = 'verify',
  username
}: EmailVerificationProps) {
  const [email, setEmail] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [step, setStep] = useState<"email" | "verify">("email");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateEmail(email)) {
      toast({
        variant: "destructive",
        title: "خطأ في البريد الإلكتروني",
        description: "يرجى إدخال عنوان بريد إلكتروني صحيح",
      });
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/auth/send-verification-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, action, username }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'حدث خطأ');
      }

      toast({
        title: "تم إرسال الرمز",
        description: data.message || "تم إرسال رمز التحقق بنجاح",
      });

      setStep("verify");
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "خطأ",
        description: error.message || "حدث خطأ في إرسال رمز التحقق",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();

    if (verificationCode.length !== 4) {
      toast({
        variant: "destructive",
        title: "خطأ في الرمز",
        description: "يجب إدخال 4 أرقام للتحقق",
      });
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/auth/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email,
          code: verificationCode,
          action,
          username
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'حدث خطأ');
      }

      toast({
        title: "تم التحقق",
        description: data.message || "تم التحقق من البريد الإلكتروني بنجاح",
      });

      onVerificationComplete(email);
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "خطأ",
        description: error.message || "حدث خطأ في التحقق من الرمز",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4" dir="rtl">
      {step === "email" ? (
        <form onSubmit={handleSendCode} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">البريد الإلكتروني</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="example@domain.com"
              required
              dir="ltr"
              className="text-right"
            />
          </div>
          <div className="flex gap-2">
            <Button 
              type="submit" 
              className="flex-1"
              disabled={isLoading || !validateEmail(email)}
            >
              {isLoading ? "جاري الإرسال..." : "إرسال رمز التحقق"}
            </Button>
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={isLoading}
              >
                إلغاء
              </Button>
            )}
          </div>
        </form>
      ) : (
        <form onSubmit={handleVerifyCode} className="space-y-4">
          <div className="space-y-2">
            <Label>رمز التحقق (4 أرقام)</Label>
            <div className="flex justify-center my-4">
              <OTPInput
                value={verificationCode}
                onChange={setVerificationCode}
                valueLength={4}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button 
              type="submit" 
              className="flex-1"
              disabled={isLoading || verificationCode.length !== 4}
            >
              {isLoading ? "جاري التحقق..." : "تحقق من الرمز"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setStep("email")}
              disabled={isLoading}
            >
              تغيير البريد الإلكتروني
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}