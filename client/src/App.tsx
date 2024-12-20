import { Switch, Route } from "wouter";
import Dashboard from "@/pages/Dashboard";
import Calendar from "@/pages/Calendar";
import Analytics from "@/pages/Analytics";
import { Sidebar } from "@/components/layout/Sidebar";

function App() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
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
