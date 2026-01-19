import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCMc7ykXvWixIfE6QxkSSBgmqIyneotEaU",
  authDomain: "music-assits.firebaseapp.com",
  projectId: "music-assits",
  storageBucket: "music-assits.firebasestorage.app",
  messagingSenderId: "158647252148",
  appId: "1:158647252148:web:ae8654dec0acbcfa0293e1"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();