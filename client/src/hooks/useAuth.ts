import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { InsertUser, SelectUser } from "@db/schema";
import { useToast } from '@/hooks/use-toast';

type AuthResponse = {
  ok: boolean;
  message?: string;
  user?: SelectUser;
};

async function handleAuthRequest(
  url: string,
  method: string,
  body?: InsertUser
): Promise<AuthResponse> {
  try {
    const response = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      credentials: "include",
    });

    const data = await response.json();

    if (!response.ok) {
      return { 
        ok: false, 
        message: data.message || response.statusText 
      };
    }

    return { 
      ok: true, 
      message: data.message,
      user: data.user
    };
  } catch (error) {
    return { 
      ok: false, 
      message: error instanceof Error ? error.message : 'حدث خطأ غير معروف' 
    };
  }
}

export function useAuth() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: user, isLoading } = useQuery<SelectUser>({
    queryKey: ['user'],
    queryFn: () => fetch('/api/user', { credentials: 'include' }).then(res => {
      if (!res.ok) {
        if (res.status === 401) return null;
        throw new Error(res.statusText);
      }
      return res.json();
    }),
    retry: false
  });

  const login = useMutation({
    mutationFn: (credentials: InsertUser) => 
      handleAuthRequest('/api/login', 'POST', credentials),
    onSuccess: (data) => {
      if (data.ok) {
        queryClient.invalidateQueries({ queryKey: ['user'] });
        toast({
          title: "تم تسجيل الدخول بنجاح",
          description: data.message
        });
      } else {
        toast({
          variant: "destructive",
          title: "فشل تسجيل الدخول",
          description: data.message
        });
      }
    }
  });

  const register = useMutation({
    mutationFn: (userData: InsertUser) => 
      handleAuthRequest('/api/register', 'POST', userData),
    onSuccess: (data) => {
      if (data.ok) {
        queryClient.invalidateQueries({ queryKey: ['user'] });
        toast({
          title: "تم التسجيل بنجاح",
          description: data.message
        });
      } else {
        toast({
          variant: "destructive",
          title: "فشل التسجيل",
          description: data.message
        });
      }
    }
  });

  const logout = useMutation({
    mutationFn: () => handleAuthRequest('/api/logout', 'POST'),
    onSuccess: (data) => {
      if (data.ok) {
        queryClient.invalidateQueries({ queryKey: ['user'] });
        toast({
          title: "تم تسجيل الخروج",
          description: data.message
        });
      }
    }
  });

  return {
    user,
    isLoading,
    login: login.mutate,
    logout: logout.mutate,
    register: register.mutate,
    isAuthenticating: login.isPending || register.isPending
  };
}
