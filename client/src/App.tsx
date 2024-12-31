import { Switch, Route } from "wouter";
import { lazy, Suspense } from "react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { LocaleProvider } from "@/contexts/LocaleContext";
import LoginPage from "@/pages/LoginPage";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Calendar = lazy(() => import("@/pages/Calendar"));
const Analytics = lazy(() => import("@/pages/Analytics"));

import { Sidebar } from "@/components/layout/Sidebar";
import { LanguageSelector } from "@/components/LanguageSelector";
import { useLocale } from "@/contexts/LocaleContext";

function App() {
  return (
    <LocaleProvider>
      <AppContent />
    </LocaleProvider>
  );
}

function AppContent() {
  const { direction } = useLocale();

  return (
    <ErrorBoundary>
      <Switch>
        <Route path="/login" component={LoginPage} />
        <Route>
          <ProtectedLayout direction={direction}>
            <Suspense fallback={<div className="p-4">Loading...</div>}>
              <Switch>
                <Route path="/" component={Dashboard} />
                <Route path="/calendar" component={Calendar} />
                <Route path="/analytics" component={Analytics} />
              </Switch>
            </Suspense>
          </ProtectedLayout>
        </Route>
      </Switch>
    </ErrorBoundary>
  );
}

function ProtectedLayout({ children, direction }: { children: React.ReactNode; direction: 'ltr' | 'rtl' }) {
  return (
    <div className={`flex h-screen bg-background ${direction === 'rtl' ? 'rtl' : 'ltr'}`} dir={direction}>
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="p-4 flex justify-end">
          <LanguageSelector />
        </div>
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
      </main>
    </div>
  );
}

export default App;