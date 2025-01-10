import { Switch, Route } from "wouter";
import { lazy, Suspense } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, Loader2 } from "lucide-react";
import AuthPage from "@/pages/AuthPage";
import { useUser } from "@/hooks/use-user";
import { Navbar } from "@/components/ui/navbar";
import ResetPassword from "@/pages/ResetPassword";
import VerifyEmailPage from "@/pages/verify-email";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Calendar = lazy(() => import("@/pages/Calendar"));
const Analytics = lazy(() => import("@/pages/Analytics"));
const AdminPanel = lazy(() => import("@/pages/AdminPanel"));
const SocialMediaManager = lazy(() => import("@/pages/SocialMediaManager"));

function App() {
  const { user, isLoading } = useUser();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-background" dir="rtl">
      {user && <Navbar />}
      <main className="flex-1 container mx-auto py-8">
        <Suspense fallback={
          <div className="flex items-center justify-center min-h-[60vh]">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        }>
          <Switch>
            {/* المسارات العامة | Public routes */}
            <Route path="/reset-password" component={ResetPassword} />
            <Route path="/verify-email" component={VerifyEmailPage} />

            {/* المسارات المحمية | Protected routes */}
            {!user ? (
              <Route path="*" component={AuthPage} />
            ) : (
              <>
                <Route path="/" component={Dashboard} />
                <Route path="/calendar" component={Calendar} />
                <Route path="/analytics" component={Analytics} />
                <Route path="/social" component={SocialMediaManager} />
                {user.role === "admin" && (
                  <Route path="/admin" component={AdminPanel} />
                )}
                <Route component={NotFound} />
              </>
            )}
          </Switch>
        </Suspense>
      </main>
    </div>
  );
}

function NotFound() {
  return (
    <div className="min-h-[60vh] w-full flex items-center justify-center">
      <Card className="w-full max-w-md mx-4">
        <CardContent className="pt-6">
          <div className="flex mb-4 gap-2">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <h1 className="text-2xl font-bold">الصفحة غير موجودة</h1>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            الصفحة التي تبحث عنها غير موجودة
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export default App;