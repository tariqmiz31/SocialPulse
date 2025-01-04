import { initializeApp } from "firebase/app";
import { getAuth, RecaptchaVerifier } from "firebase/auth";

const firebaseConfig = {
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  authDomain: `${import.meta.env.VITE_FIREBASE_PROJECT_ID}.firebaseapp.com`,
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY
};

// تهيئة Firebase
// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// إعداد reCAPTCHA
// Setup reCAPTCHA
export function setupRecaptcha(buttonId: string) {
  const recaptchaVerifier = new RecaptchaVerifier(auth, buttonId, {
    'size': 'invisible',
    'callback': () => {
      // رمز التحقق تم التحقق منه بنجاح
      // Callback after reCAPTCHA verification
    }
  });
  
  return recaptchaVerifier;
}
