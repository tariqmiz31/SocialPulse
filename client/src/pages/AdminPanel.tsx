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
import { Form } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { 
  Loader2, 
  CheckCircle, 
  XCircle, 
  Ban, 
  RefreshCw, 
  UserPlus,
  Trash2,
  Shield
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const newUserSchema = z.object({
  username: z.string().min(3, "اسم المستخدم يجب أن يكون 3 أحرف على الأقل"),
  password: z.string().min(6, "كلمة المرور يجب أن تكون 6 أحرف على الأقل"),
  role: z.enum(["admin", "user"])
});

type User = {
  id: number;
  username: string;
  role: string;
  isApproved: boolean;
  status: string;
  createdAt: string;
};

type NewUser = z.infer<typeof newUserSchema>;

export default function AdminPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);

  const form = useForm<NewUser>({
    resolver: zodResolver(newUserSchema),
    defaultValues: {
      username: "",
      password: "",
      role: "user"
    }
  });

  const { data: users, isLoading } = useQuery<User[]>({
    queryKey: ["/api/admin/users"],
  });

  const updateUserStatus = useMutation({
    mutationFn: async ({
      userId,
      action,
    }: {
      userId: number;
      action: "approve" | "block" | "unblock" | "delete" | "promote" | "demote";
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
            : action === "unblock"
            ? "تم إلغاء حظر المستخدم بنجاح"
            : action === "delete"
            ? "تم حذف المستخدم بنجاح"
            : action === "promote"
            ? "تمت ترقية المستخدم إلى مشرف بنجاح"
            : "تم إلغاء صلاحيات الإشراف بنجاح",
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

  const addUser = useMutation({
    mutationFn: async (userData: NewUser) => {
      const response = await fetch("/api/admin/users", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/admin/users"] });
      setIsAddUserOpen(false);
      form.reset();
      toast({
        title: "نجاح",
        description: "تمت إضافة المستخدم بنجاح",
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

  const onSubmit = (data: NewUser) => {
    addUser.mutate(data);
  };

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
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>لوحة إدارة المستخدمين</CardTitle>
          <Dialog open={isAddUserOpen} onOpenChange={setIsAddUserOpen}>
            <DialogTrigger asChild>
              <Button>
                <UserPlus className="h-4 w-4 ml-2" />
                إضافة مستخدم
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>إضافة مستخدم جديد</DialogTitle>
              </DialogHeader>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <div className="space-y-2">
                    <label>اسم المستخدم</label>
                    <Input {...form.register("username")} />
                    {form.formState.errors.username && (
                      <p className="text-sm text-destructive">
                        {form.formState.errors.username.message}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <label>كلمة المرور</label>
                    <Input type="password" {...form.register("password")} />
                    {form.formState.errors.password && (
                      <p className="text-sm text-destructive">
                        {form.formState.errors.password.message}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <label>الدور</label>
                    <Select
                      onValueChange={(value) => form.setValue("role", value as "admin" | "user")}
                      defaultValue={form.getValues("role")}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="user">مستخدم</SelectItem>
                        <SelectItem value="admin">مشرف</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button type="submit" className="w-full">
                    {addUser.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "إضافة"
                    )}
                  </Button>
                </form>
              </Form>
            </DialogContent>
          </Dialog>
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
                    {user.username !== 'Tariq' && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            updateUserStatus.mutate({
                              userId: user.id,
                              action: user.role === "admin" ? "demote" : "promote",
                            })
                          }
                        >
                          <Shield className="h-4 w-4 ml-2" />
                          {user.role === "admin" ? "إلغاء الإشراف" : "ترقية لمشرف"}
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() =>
                            updateUserStatus.mutate({
                              userId: user.id,
                              action: "delete",
                            })
                          }
                        >
                          <Trash2 className="h-4 w-4 ml-2" />
                          حذف
                        </Button>
                      </>
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