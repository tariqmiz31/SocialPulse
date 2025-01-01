import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Loader2, CheckCircle, XCircle, Ban, RefreshCw } from "lucide-react";

type User = {
  id: number;
  username: string;
  role: string;
  isApproved: boolean;
  status: string;
  createdAt: string;
};

export default function AdminPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: users, isLoading } = useQuery<User[]>({
    queryKey: ["/api/admin/users"],
  });

  const updateUserStatus = useMutation({
    mutationFn: async ({
      userId,
      action,
    }: {
      userId: number;
      action: "approve" | "block" | "unblock";
    }) => {
      const response = await fetch(`/api/admin/users/${userId}/${action}`, {
        method: "POST",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      return response.json();
    },
    onSuccess: (_, { action }) => {
      queryClient.invalidateQueries({ queryKey: ["/api/admin/users"] });
      toast({
        title: "نجاح",
        description:
          action === "approve"
            ? "تمت الموافقة على المستخدم بنجاح"
            : action === "block"
            ? "تم حظر المستخدم بنجاح"
            : "تم إلغاء حظر المستخدم بنجاح",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "خطأ",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      <Card>
        <CardHeader>
          <CardTitle>لوحة إدارة المستخدمين</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>اسم المستخدم</TableHead>
                <TableHead>الدور</TableHead>
                <TableHead>الحالة</TableHead>
                <TableHead>تاريخ التسجيل</TableHead>
                <TableHead>الإجراءات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users?.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>{user.username}</TableCell>
                  <TableCell>
                    {user.role === "admin" ? "مشرف" : "مستخدم"}
                  </TableCell>
                  <TableCell>
                    {user.status === "pending"
                      ? "قيد الانتظار"
                      : user.status === "active"
                      ? "نشط"
                      : "محظور"}
                  </TableCell>
                  <TableCell>
                    {new Date(user.createdAt).toLocaleDateString("ar")}
                  </TableCell>
                  <TableCell className="space-x-2">
                    {!user.isApproved && user.status === "pending" && (
                      <Button
                        size="sm"
                        onClick={() =>
                          updateUserStatus.mutate({
                            userId: user.id,
                            action: "approve",
                          })
                        }
                      >
                        <CheckCircle className="h-4 w-4 ml-2" />
                        موافقة
                      </Button>
                    )}
                    {user.status !== "blocked" && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() =>
                          updateUserStatus.mutate({
                            userId: user.id,
                            action: "block",
                          })
                        }
                      >
                        <Ban className="h-4 w-4 ml-2" />
                        حظر
                      </Button>
                    )}
                    {user.status === "blocked" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          updateUserStatus.mutate({
                            userId: user.id,
                            action: "unblock",
                          })
                        }
                      >
                        <RefreshCw className="h-4 w-4 ml-2" />
                        إلغاء الحظر
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
