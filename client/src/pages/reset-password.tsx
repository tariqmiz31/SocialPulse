import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useResetPassword } from "@/hooks/use-reset-password";
import { OTPInputGroup, OTPInputSlot, OTPInputSeparator } from "@/components/ui/otp-input";

export default function ResetPasswordPage() {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<"phone" | "verify" | "reset">("phone");
  
  const { sendCode, verifyPhone, resetPassword, isSending, isVerifying, isResetting } = useResetPassword();

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await sendCode({ phoneNumber });
      setStep("verify");
    } catch (error) {
      // Error handling is done in the hook
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (verificationCode.length !== 4) return;
    
    try {
      await verifyPhone({
        phoneNumber,
        code: verificationCode,
        verificationId: "", // Will be handled by Firebase
      });
      setStep("reset");
    } catch (error) {
      // Error handling is done in the hook
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await resetPassword({
        username: phoneNumber,
        password,
        verificationId: "", // Will be handled by Firebase
      });
    } catch (error) {
      // Error handling is done in the hook
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">
            {step === "phone" && "إعادة تعيين كلمة المرور"}
            {step === "verify" && "التحقق من رقم الهاتف"}
            {step === "reset" && "تعيين كلمة المرور الجديدة"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {step === "phone" && (
            <form onSubmit={handleSendCode} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="phone">رقم الهاتف</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+966501234567"
                  required
                  dir="ltr"
                />
              </div>
              <Button 
                type="submit" 
                className="w-full" 
                disabled={isSending}
                id="send-code-button"
              >
                {isSending ? "جاري الإرسال..." : "إرسال رمز التحقق"}
              </Button>
            </form>
          )}

          {step === "verify" && (
            <form onSubmit={handleVerifyCode} className="space-y-4">
              <div className="space-y-2">
                <Label>رمز التحقق</Label>
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
              <Button 
                type="submit" 
                className="w-full" 
                disabled={isVerifying || verificationCode.length !== 4}
              >
                {isVerifying ? "جاري التحقق..." : "تحقق من الرمز"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => setStep("phone")}
              >
                تغيير رقم الهاتف
              </Button>
            </form>
          )}

          {step === "reset" && (
            <form onSubmit={handleResetPassword} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="password">كلمة المرور الجديدة</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </div>
              <Button 
                type="submit" 
                className="w-full"
                disabled={isResetting}
              >
                {isResetting ? "جاري التحديث..." : "تحديث كلمة المرور"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
