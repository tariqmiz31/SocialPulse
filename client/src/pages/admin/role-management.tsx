import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useQuery, useMutation } from "@tanstack/react-query";
import { VerificationProgress } from "@/components/admin/verification-progress";

interface RoleChangeStep {
  step: number;
  totalSteps: number;
  completed: boolean;
  username: string;
  currentRole: string;
  newRole: string;
}

const VERIFICATION_STEPS = [
  { step: 1, label: "تقديم الطلب" },
  { step: 2, label: "التحقق من البريد الإلكتروني" },
  { step: 3, label: "موافقة المشرف" },
];

export default function RoleManagement() {
  const [verificationCode, setVerificationCode] = useState("");
  const [verificationId, setVerificationId] = useState<string | null>(null);
  const { toast } = useToast();

  // استعلام عن حالة تغيير الصلاحيات
  const { data: roleChangeStatus, refetch } = useQuery<RoleChangeStep>({
    queryKey: ['/api/roles/change-status', verificationId],
    enabled: !!verificationId,
  });

  // طلب تغيير الصلاحيات
  const requestRoleChange = useMutation({
    mutationFn: async (data: { userId: number; newRole: string; adminEmail: string }) => {
      const response = await fetch('/api/roles/change-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const result = await response.json();
      return result;
    },
    onSuccess: (data) => {
      setVerificationId(data.verification_id);
      toast({
        title: "تم إرسال رمز التحقق",
        description: "يرجى التحقق من بريدك الإلكتروني",
      });
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "خطأ",
        description: error.message,
      });
    },
  });

  // التحقق من رمز التأكيد
  const verifyCode = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/roles/verify-change', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verification_id: verificationId, code: verificationCode }),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      return response.json();
    },
    onSuccess: (data) => {
      if (data.completed) {
        toast({
          title: "تم تغيير الصلاحيات بنجاح",
          description: data.message,
        });
        setVerificationId(null);
        setVerificationCode("");
      } else {
        toast({
          title: `تم التحقق من الخطوة ${data.step}`,
          description: `باقي ${data.total_steps - data.step} خطوات`,
        });
        refetch();
      }
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "خطأ في التحقق",
        description: error.message,
      });
    },
  });

  const currentSteps = VERIFICATION_STEPS.map((step) => ({
    ...step,
    completed: roleChangeStatus ? roleChangeStatus.step > step.step : false,
    current: roleChangeStatus ? roleChangeStatus.step === step.step : false,
  }));

  return (
    <div className="container mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>إدارة صلاحيات المستخدمين</CardTitle>
        </CardHeader>
        <CardContent>
          {roleChangeStatus && (
            <>
              <Alert className="mb-4">
                <AlertDescription>
                  تغيير صلاحيات المستخدم {roleChangeStatus.username} 
                  من {roleChangeStatus.currentRole} إلى {roleChangeStatus.newRole}
                </AlertDescription>
              </Alert>

              <VerificationProgress
                steps={currentSteps}
                currentStep={roleChangeStatus.step}
              />
            </>
          )}

          <div className="space-y-4">
            {verificationId && (
              <div className="flex gap-4">
                <Input
                  type="text"
                  placeholder="أدخل رمز التحقق"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  className="max-w-xs"
                />
                <Button 
                  onClick={() => verifyCode.mutate()}
                  disabled={verifyCode.isPending}
                >
                  تحقق
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}