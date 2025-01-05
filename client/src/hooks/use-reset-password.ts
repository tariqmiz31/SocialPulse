import { useMutation } from "@tanstack/react-query";
import { toast } from "@/hooks/use-toast";
import { FirebaseError } from "firebase/auth";

type RequestResult = {
  message: {
    ar: string;
    en: string;
  };
};

interface ResetPasswordData {
  username: string;
  password: string;
  verificationId: string;
}

interface VerifyPhoneData {
  phoneNumber: string;
  code: string;
  verificationId: string;
}

async function handleRequest(
  url: string,
  data: ResetPasswordData | VerifyPhoneData
): Promise<RequestResult> {
  const response = await fetch(`/api/auth/${url}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message?.ar || error.message?.en || response.statusText);
  }

  return response.json();
}

export function useResetPassword() {
  const verifyPhoneMutation = useMutation({
    mutationFn: (data: VerifyPhoneData) => handleRequest("verify-phone", data),
    onError: (error) => {
      if (error instanceof FirebaseError) {
        toast({
          variant: "destructive",
          title: "خطأ في التحقق",
          description: error.message,
        });
      } else {
        toast({
          variant: "destructive",
          title: "خطأ",
          description: error.message,
        });
      }
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: (data: ResetPasswordData) => handleRequest("reset-password", data),
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "خطأ في إعادة تعيين كلمة المرور",
        description: error.message,
      });
    },
  });

  return {
    verifyPhone: verifyPhoneMutation.mutateAsync,
    resetPassword: resetPasswordMutation.mutateAsync,
    isVerifying: verifyPhoneMutation.isPending,
    isResetting: resetPasswordMutation.isPending,
  };
}
