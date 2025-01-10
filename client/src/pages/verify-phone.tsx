import { useLocation } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmailVerification } from "@/components/ui/email-verification";

export default function VerifyEmailPage() {
  const [, setLocation] = useLocation();

  const handleVerificationComplete = (email: string) => {
    // بعد نجاح التحقق، انتقل إلى الصفحة الرئيسية أو لوحة التحكم
    setLocation("/");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">
            التحقق من البريد الإلكتروني
          </CardTitle>
        </CardHeader>
        <CardContent>
          <EmailVerification
            onVerificationComplete={handleVerificationComplete}
            action="verify"
          />
        </CardContent>
      </Card>
    </div>
  );
}