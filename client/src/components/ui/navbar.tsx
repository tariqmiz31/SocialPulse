import { Link } from "wouter";
import { useUser } from "@/hooks/use-user";
import { Button } from "@/components/ui/button";

export function Navbar() {
  const { user, logout } = useUser();

  return (
    <nav className="border-b bg-background" dir="rtl">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/">
              <a className="text-xl font-bold">سيلفاريوم</a>
            </Link>
            <div className="space-x-4">
              <Link href="/calendar">
                <a className="text-sm text-muted-foreground hover:text-foreground mr-4">التقويم</a>
              </Link>
              <Link href="/analytics">
                <a className="text-sm text-muted-foreground hover:text-foreground mr-4">التحليلات</a>
              </Link>
              {user?.role === 'admin' && (
                <Link href="/admin">
                  <a className="text-sm text-muted-foreground hover:text-foreground mr-4">لوحة الإشراف</a>
                </Link>
              )}
            </div>
          </div>
          <Button variant="outline" onClick={() => logout()}>
            تسجيل الخروج
          </Button>
        </div>
      </div>
    </nav>
  );
}