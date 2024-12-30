import { Switch, Route } from "wouter";
import { lazy, Suspense } from "react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Calendar = lazy(() => import("@/pages/Calendar"));
const Analytics = lazy(() => import("@/pages/Analytics"));
import { Sidebar } from "@/components/layout/Sidebar";
import { LanguageSelector } from "@/components/LanguageSelector";
import { useLocale } from "@/contexts/LocaleContext";

function App() {
  const { direction } = useLocale();

  return (
    <ErrorBoundary>
      <div className={`flex h-screen bg-background ${direction === 'rtl' ? 'rtl' : 'ltr'}`}>
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 flex justify-end">
            <LanguageSelector />
          </div>
          <ErrorBoundary>
            <Suspense fallback={<div className="p-4">Loading...</div>}>
              <Switch>
                <Route path="/" component={Dashboard} />
                <Route path="/calendar" component={Calendar} />
                <Route path="/analytics" component={Analytics} />
              </Switch>
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </ErrorBoundary>
  );
}

export default App;