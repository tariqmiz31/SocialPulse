import { useQuery } from "@tanstack/react-query";
import { adminPermissionsSchema, type AdminPermissions } from "@/types/admin";

export function useAdminPermissions() {
  return useQuery<AdminPermissions>({
    queryKey: ["/api/admin/check-permissions"],
    queryFn: async () => {
      const response = await fetch("/api/admin/check-permissions", {
        credentials: "include"
      });

      if (!response.ok) {
        if (response.status === 401) {
          return {
            isAdmin: false,
            role: "user",
            isApproved: false,
            status: "pending"
          } as const;
        }

        throw new Error(await response.text());
      }

      const data = await response.json();
      return adminPermissionsSchema.parse(data);
    },
    staleTime: 5 * 60 * 1000, // تحديث كل 5 دقائق
    retry: false
  });
}
