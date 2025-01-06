import { useNavigate } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SMSVerification } from "@/components/ui/sms-verification";

export default function VerifyPhonePage() {
  const navigate = useNavigate();

  const handleVerificationComplete = (phoneNumber: string) => {
    // After successful verification, redirect to home or dashboard
    navigate("/");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">
            التحقق من رقم الهاتف
          </CardTitle>
        </CardHeader>
        <CardContent>
          <SMSVerification
            onVerificationComplete={handleVerificationComplete}
            action="verify"
          />
        </CardContent>
      </Card>
    </div>
  );
}
