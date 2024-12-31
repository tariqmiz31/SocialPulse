import { Switch, Route } from "wouter";
import { lazy, Suspense } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, Loader2 } from "lucide-react";
import AuthPage from "@/pages/AuthPage";
import { useUser } from "@/hooks/use-user";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Calendar = lazy(() => import("@/pages/Calendar"));
const Analytics = lazy(() => import("@/pages/Analytics"));

function App() {
  const { user, isLoading } = useUser();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-border" />
      </div>
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  return (
    <div className="flex min-h-screen bg-background" dir="rtl">
      <main className="flex-1">
        <Suspense fallback={
          <div className="flex items-center justify-center min-h-screen">
            <Loader2 className="h-8 w-8 animate-spin text-border" />
          </div>
        }>
          <Switch>
            <Route path="/" component={Dashboard} />
            <Route path="/calendar" component={Calendar} />
            <Route path="/analytics" component={Analytics} />
            <Route component={NotFound} />
          </Switch>
        </Suspense>
      </main>
    </div>
  );
}

// fallback 404 not found page
function NotFound() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background">
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