import { useCallback, useEffect, useState } from 'react';
import { onAuthStateChanged, signInWithPopup, signOut } from 'firebase/auth';
import { auth, googleProvider } from '../firebase.ts';
import { UserProfile } from '../types.ts';

/** Firebase auth state + sign-in/sign-out actions. Does not know about chat
 * or conversation history - callers react to `user` changing if they need to. */
export function useAuth() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      if (currentUser) {
        setUser({
          displayName: currentUser.displayName,
          email: currentUser.email,
          photoURL: currentUser.photoURL,
          uid: currentUser.uid,
        });
      } else {
        setUser(null);
      }
    });
    return () => unsubscribe();
  }, []);

  const handleGoogleLogin = useCallback(async () => {
    try {
      await signInWithPopup(auth, googleProvider);
      setIsLoginModalOpen(false);
    } catch (error: unknown) {
      console.error("Music-Assist: Login failed", error);
      const message = error instanceof Error ? error.message : 'Unknown error';
      alert(`Authentication failed: ${message}`);
    }
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.error("Logout failed", error);
    }
  }, []);

  return {
    user,
    isLoginModalOpen,
    setIsLoginModalOpen,
    handleGoogleLogin,
    handleLogout,
  };
}
