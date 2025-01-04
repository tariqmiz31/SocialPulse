import { initializeApp } from "firebase/app";
import { getAuth, RecaptchaVerifier } from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  projectId: "silva-11e9d",
  authDomain: "silva-11e9d.firebaseapp.com",
  storageBucket: "silva-11e9d.appspot.com"
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Setup reCAPTCHA
export function setupRecaptcha(buttonId: string) {
  const recaptchaVerifier = new RecaptchaVerifier(auth, buttonId, {
    'size': 'invisible',
    'callback': () => {
      // Callback after reCAPTCHA verification
    }
  });

  return recaptchaVerifier;
}