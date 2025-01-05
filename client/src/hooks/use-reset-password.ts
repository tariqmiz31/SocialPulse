import { useMutation } from "@tanstack/react-query";
import { toast } from "@/hooks/use-toast";
import { FirebaseError } from "firebase/auth";
import { auth, setupRecaptcha, sendVerificationCode, verifyCode } from "@/lib/firebase";

type RequestResult = {
  message: {
    ar: string;
    en: string;
  };
};

interface SendCodeData {
  phoneNumber: string;
}

interface VerifyPhoneData {
  phoneNumber: string;
  code: string;
  verificationId: string;
}

interface ResetPasswordData {
  username: string;
  password: string;
  verificationId: string;
}

async function handleRequest(
  url: string,
  data: SendCodeData | VerifyPhoneData | ResetPasswordData
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
  const sendCodeMutation = useMutation({
    mutationFn: async (data: SendCodeData) => {
      const recaptchaVerifier = await setupRecaptcha('send-code-button');
      await sendVerificationCode(data.phoneNumber, recaptchaVerifier);
      return handleRequest("send-verification-code", { phoneNumber: data.phoneNumber });
    },
    onError: (error: Error) => {
      if (error instanceof FirebaseError) {
        let errorMessage = {
          ar: "خطأ في إرسال الرمز",
          en: "Error sending code"
        };

        // Handle specific Firebase errors with bilingual messages
        switch (error.code) {
          case 'auth/too-many-requests':
            errorMessage = {
              ar: "عدد محاولات كثيرة، يرجى المحاولة لاحقاً",
              en: "Too many attempts, please try again later"
            };
            break;
          case 'auth/invalid-phone-number':
            errorMessage = {
              ar: "رقم الهاتف غير صالح",
              en: "Invalid phone number"
            };
            break;
          case 'auth/quota-exceeded':
            errorMessage = {
              ar: "تم تجاوز الحد المسموح من المحاولات، يرجى المحاولة لاحقاً",
              en: "SMS quota exceeded, please try again later"
            };
            break;
        }

        toast({
          variant: "destructive",
          title: errorMessage.ar,
          description: errorMessage.en,
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

  const verifyPhoneMutation = useMutation({
    mutationFn: async (data: VerifyPhoneData) => {
      const result = await verifyCode(data.code);
      if (!result) {
        throw new Error("فشل في التحقق من الرمز");
      }
      const idToken = await result.user.getIdToken();
      return handleRequest("verify-phone", {
        ...data,
        verificationId: idToken
      });
    },
    onError: (error: Error) => {
      if (error instanceof FirebaseError) {
        let errorMessage = {
          ar: "خطأ في التحقق",
          en: "Verification error"
        };

        // Handle specific Firebase errors with bilingual messages
        switch (error.code) {
          case 'auth/code-expired':
            errorMessage = {
              ar: "انتهت صلاحية الرمز",
              en: "Code expired"
            };
            break;
          case 'auth/invalid-verification-code':
            errorMessage = {
              ar: "رمز التحقق غير صحيح",
              en: "Invalid verification code"
            };
            break;
          case 'auth/too-many-requests':
            errorMessage = {
              ar: "عدد محاولات كثيرة، يرجى المحاولة لاحقاً",
              en: "Too many attempts, please try again later"
            };
            break;
        }

        toast({
          variant: "destructive",
          title: errorMessage.ar,
          description: errorMessage.en,
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
    mutationFn: async (data: ResetPasswordData) => {
      const idToken = await auth.currentUser?.getIdToken();
      if (!idToken) {
        throw new Error("يجب التحقق من رقم الهاتف أولاً");
      }
      return handleRequest("reset-password", {
        ...data,
        verificationId: idToken
      });
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "خطأ في إعادة تعيين كلمة المرور",
        description: error.message,
      });
    },
  });

  return {
    sendCode: sendCodeMutation.mutateAsync,
    verifyPhone: verifyPhoneMutation.mutateAsync,
    resetPassword: resetPasswordMutation.mutateAsync,
    isSending: sendCodeMutation.isPending,
    isVerifying: verifyPhoneMutation.isPending,
    isResetting: resetPasswordMutation.isPending,
  };
}