import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OTPInputGroup, OTPInputSlot, OTPInputSeparator } from "@/components/ui/otp-input";
import { useToast } from "@/hooks/use-toast";

interface SMSVerificationProps {
  onVerificationComplete: (phoneNumber: string) => void;
  onCancel?: () => void;
  action?: 'verify' | 'reset';
}

export function SMSVerification({ onVerificationComplete, onCancel, action = 'verify' }: SMSVerificationProps) {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [step, setStep] = useState<"phone" | "verify">("phone");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const validateSaudiPhoneNumber = (number: string): boolean => {
    // Remove spaces and dashes
    const cleanNumber = number.replace(/[\s-]/g, '');
    // Check if it starts with +966 and followed by 9 digits
    const saudiRegex = /^\+966[0-9]{9}$/;
    return saudiRegex.test(cleanNumber);
  };

  const formatPhoneNumber = (input: string): string => {
    // Remove all non-digit characters except +
    let cleaned = input.replace(/[^\d+]/g, '');

    // Ensure it starts with +966
    if (!cleaned.startsWith('+')) {
      cleaned = '+' + cleaned;
    }
    if (!cleaned.startsWith('+966') && cleaned.length > 1) {
      cleaned = '+966' + cleaned.substring(cleaned.startsWith('+') ? 1 : 0);
    }

    return cleaned;
  };

  const handlePhoneNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value);
    setPhoneNumber(formatted);
  };

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateSaudiPhoneNumber(phoneNumber)) {
      toast({
        variant: "destructive",
        title: "خطأ في رقم الهاتف",
        description: "يرجى إدخال رقم هاتف سعودي صحيح يبدأ بـ +966",
      });
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/auth/send-verification-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phoneNumber, action }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message?.ar || 'حدث خطأ');
      }

      toast({
        title: "تم إرسال الرمز",
        description: data.message?.ar || "تم إرسال رمز التحقق بنجاح",
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
      const response = await fetch('/api/auth/verify-phone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          phoneNumber,
          code: verificationCode,
          action,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message?.ar || 'حدث خطأ');
      }

      toast({
        title: "تم التحقق",
        description: data.message?.ar || "تم التحقق من رقم الهاتف بنجاح",
      });

      onVerificationComplete(phoneNumber);
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
      {step === "phone" && (
        <form onSubmit={handleSendCode} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="phone">رقم الهاتف</Label>
            <Input
              id="phone"
              type="tel"
              value={phoneNumber}
              onChange={handlePhoneNumberChange}
              placeholder="+966501234567"
              required
              dir="ltr"
              className="text-right"
            />
            <p className="text-sm text-muted-foreground">
              يجب أن يبدأ الرقم بـ +966
            </p>
          </div>
          <div className="flex gap-2">
            <Button 
              type="submit" 
              className="flex-1"
              disabled={isLoading || !validateSaudiPhoneNumber(phoneNumber)}
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
      )}

      {step === "verify" && (
        <form onSubmit={handleVerifyCode} className="space-y-4">
          <div className="space-y-2">
            <Label>رمز التحقق (4 أرقام)</Label>
            <div className="flex justify-center my-4">
              <OTPInputGroup
                maxLength={4}
                value={verificationCode}
                onChange={setVerificationCode}
                dir="ltr"
              >
                <OTPInputSlot index={0} />
                <OTPInputSeparator />
                <OTPInputSlot index={1} />
                <OTPInputSeparator />
                <OTPInputSlot index={2} />
                <OTPInputSeparator />
                <OTPInputSlot index={3} />
              </OTPInputGroup>
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
              onClick={() => setStep("phone")}
              disabled={isLoading}
            >
              تغيير رقم الهاتف
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}