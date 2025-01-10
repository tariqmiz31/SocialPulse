// This page has been deprecated as we now only use email verification
// Please use verify-email.tsx instead
import { useEffect } from "react";
import { useLocation } from "wouter";

export default function VerifyPhonePage() {
  const [, setLocation] = useLocation();

  useEffect(() => {
    // Redirect to email verification page
    setLocation("/verify-email");
  }, [setLocation]);

  return null; // No need to render anything as we're redirecting
}