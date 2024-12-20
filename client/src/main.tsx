import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { Toaster } from "@/components/ui/toaster";
import { LocaleProvider } from "@/contexts/LocaleContext";
import App from './App';
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LocaleProvider>
      <QueryClientProvider client={queryClient}>
        <App />
        <Toaster />
      </QueryClientProvider>
    </LocaleProvider>
  </StrictMode>,
);