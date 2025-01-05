import { initializeApp } from "firebase/app";
import { getAuth, RecaptchaVerifier, type Persistence, browserLocalPersistence } from "firebase/auth";

declare global {
  interface Window {
    recaptchaVerifier: RecaptchaVerifier | null;
  }
}

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  authDomain: `${import.meta.env.VITE_FIREBASE_PROJECT_ID}.firebaseapp.com`,
  storageBucket: `${import.meta.env.VITE_FIREBASE_PROJECT_ID}.appspot.com`
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Enable local persistence with proper type
auth.setPersistence(browserLocalPersistence);

// Default language to Arabic
auth.languageCode = 'ar';

export async function setupRecaptcha(buttonId: string) {
  try {
    // Clear any existing reCAPTCHA instances
    if (window.recaptchaVerifier) {
      window.recaptchaVerifier.clear();
      window.recaptchaVerifier = null;
    }

    // Create new reCAPTCHA verifier
    const recaptchaVerifier = new RecaptchaVerifier(auth, buttonId, {
      'size': 'invisible',
      'callback': () => {
        console.log('reCAPTCHA verified');
      },
      'expired-callback': () => {
        console.log('reCAPTCHA expired');
        window.recaptchaVerifier = null;
      }
    });

    window.recaptchaVerifier = recaptchaVerifier;
    return recaptchaVerifier;
  } catch (error) {
    console.error('Error setting up reCAPTCHA:', error);
    throw error;
  }
}