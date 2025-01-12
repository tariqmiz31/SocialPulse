import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { VerificationProgress } from "@/components/admin/verification-progress";
import { useAdminPermissions } from "@/hooks/use-admin-permissions";
import type { RoleChangeRequest, VerificationStatus } from "@/types/admin";

const VERIFICATION_STEPS = [
  { step: 1, label: "تقديم الطلب" },
  { step: 2, label: "التحقق من البريد الإلكتروني" },
  { step: 3, label: "موافقة المشرف" },
];

export default function RoleManagement() {
  const [verificationCode, setVerificationCode] = useState("");
  const [currentVerification, setCurrentVerification] = useState<VerificationStatus | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: permissions, isLoading } = useAdminPermissions();

  // طلب تغيير الصلاحيات
  const requestRoleChange = useMutation({
    mutationFn: async (data: RoleChangeRequest) => {
      const response = await fetch('/api/roles/change-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      return response.json() as Promise<VerificationStatus>;
    },
    onSuccess: (data) => {
      setCurrentVerification(data);
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
        body: JSON.stringify({ 
          verification_id: currentVerification?.verificationCode,
          code: verificationCode 
        }),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      return response.json() as Promise<VerificationStatus>;
    },
    onSuccess: (data) => {
      setCurrentVerification(data);
      if (data.step === data.totalSteps) {
        toast({
          title: "تم تغيير الصلاحيات بنجاح",
          description: data.message,
        });
        setCurrentVerification(null);
        setVerificationCode("");
        queryClient.invalidateQueries({ queryKey: ['/api/admin/check-permissions'] });
      } else {
        toast({
          title: `تم التحقق من الخطوة ${data.step}`,
          description: `باقي ${data.totalSteps - data.step} خطوات`,
        });
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

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!permissions?.isAdmin) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          عذراً، لا تملك صلاحيات الوصول إلى هذه الصفحة
        </AlertDescription>
      </Alert>
    );
  }

  const currentSteps = VERIFICATION_STEPS.map((step) => ({
    ...step,
    completed: currentVerification ? currentVerification.step > step.step : false,
    current: currentVerification ? currentVerification.step === step.step : false,
  }));

  return (
    <div className="container mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>إدارة صلاحيات المستخدمين</CardTitle>
        </CardHeader>
        <CardContent>
          {currentVerification && (
            <VerificationProgress
              steps={currentSteps}
              currentStep={currentVerification.step}
            />
          )}

          <div className="space-y-4">
            {currentVerification && (
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