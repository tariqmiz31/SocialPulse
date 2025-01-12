import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { SelectUser } from "@db/schema";

interface RoleChangeRequestProps {
  user: SelectUser;
  onRequest: (data: { userId: number; newRole: string; adminEmail: string }) => void;
}

export function RoleChangeRequest({ user, onRequest }: RoleChangeRequestProps) {
  const [adminEmail, setAdminEmail] = useState("");
  const [newRole, setNewRole] = useState(user.role === "admin" ? "user" : "admin");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onRequest({
      userId: user.id,
      newRole,
      adminEmail,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>طلب تغيير صلاحيات المستخدم {user.username}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="role">الدور الجديد</Label>
            <Select value={newRole} onValueChange={setNewRole}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">مشرف</SelectItem>
                <SelectItem value="user">مستخدم عادي</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="adminEmail">البريد الإلكتروني للمشرف</Label>
            <Input
              id="adminEmail"
              type="email"
              value={adminEmail}
              onChange={(e) => setAdminEmail(e.target.value)}
              placeholder="أدخل بريدك الإلكتروني للتحقق"
              required
            />
          </div>

          <Button type="submit" className="w-full">
            تأكيد طلب تغيير الصلاحيات
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
