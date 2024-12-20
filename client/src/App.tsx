import { Switch, Route } from "wouter";
import Dashboard from "@/pages/Dashboard";
import Calendar from "@/pages/Calendar";
import Analytics from "@/pages/Analytics";
import { Sidebar } from "@/components/layout/Sidebar";
import { LanguageSelector } from "@/components/LanguageSelector";
import { useLocale } from "@/contexts/LocaleContext";

function App() {
  const { direction } = useLocale();

  return (
    <div className={`flex h-screen bg-background ${direction === 'rtl' ? 'rtl' : 'ltr'}`}>
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="p-4 flex justify-end">
          <LanguageSelector />
        </div>
        <Switch>
          <Route path="/" component={Dashboard} />
          <Route path="/calendar" component={Calendar} />
          <Route path="/analytics" component={Analytics} />
        </Switch>
      </main>
    </div>
  );
}

export default App;