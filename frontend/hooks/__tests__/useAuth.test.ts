import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { onAuthStateChanged, signInWithPopup, signOut, type User } from 'firebase/auth';
import { useAuth } from '../useAuth.ts';

vi.mock('../../firebase.ts', () => ({
  auth: {},
  googleProvider: {},
}));

vi.mock('firebase/auth', () => ({
  onAuthStateChanged: vi.fn(),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
}));

const onAuthStateChangedMock = vi.mocked(onAuthStateChanged);
const signInWithPopupMock = vi.mocked(signInWithPopup);
const signOutMock = vi.mocked(signOut);

beforeEach(() => {
  onAuthStateChangedMock.mockReset();
  signInWithPopupMock.mockReset();
  signOutMock.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useAuth', () => {
  it('starts with no signed-in user', () => {
    onAuthStateChangedMock.mockImplementation(() => vi.fn());

    const { result } = renderHook(() => useAuth());

    expect(result.current.user).toBeNull();
  });

  it('maps a Firebase user onto the UserProfile shape', () => {
    let callback: (user: User | null) => void = () => {};
    onAuthStateChangedMock.mockImplementation((_auth, cb) => {
      callback = cb as (user: User | null) => void;
      return vi.fn();
    });

    const { result } = renderHook(() => useAuth());

    act(() => {
      callback({
        uid: 'u1',
        displayName: 'Jane Doe',
        email: 'jane@example.com',
        photoURL: 'http://example.com/pic.png',
      } as User);
    });

    expect(result.current.user).toEqual({
      uid: 'u1',
      displayName: 'Jane Doe',
      email: 'jane@example.com',
      photoURL: 'http://example.com/pic.png',
    });
  });

  it('clears the user when Firebase reports signed-out', () => {
    let callback: (user: User | null) => void = () => {};
    onAuthStateChangedMock.mockImplementation((_auth, cb) => {
      callback = cb as (user: User | null) => void;
      return vi.fn();
    });

    const { result } = renderHook(() => useAuth());

    act(() => callback({ uid: 'u1', displayName: null, email: null, photoURL: null } as User));
    act(() => callback(null));

    expect(result.current.user).toBeNull();
  });

  it('unsubscribes from auth state changes on unmount', () => {
    const unsubscribe = vi.fn();
    onAuthStateChangedMock.mockImplementation(() => unsubscribe);

    const { unmount } = renderHook(() => useAuth());
    unmount();

    expect(unsubscribe).toHaveBeenCalled();
  });

  it('closes the login modal after a successful Google sign-in', async () => {
    onAuthStateChangedMock.mockImplementation(() => vi.fn());
    signInWithPopupMock.mockResolvedValue({} as Awaited<ReturnType<typeof signInWithPopup>>);

    const { result } = renderHook(() => useAuth());
    act(() => result.current.setIsLoginModalOpen(true));

    await act(async () => {
      await result.current.handleGoogleLogin();
    });

    expect(result.current.isLoginModalOpen).toBe(false);
  });

  it('alerts and leaves the modal open when Google sign-in fails', async () => {
    onAuthStateChangedMock.mockImplementation(() => vi.fn());
    signInWithPopupMock.mockRejectedValue(new Error('popup closed by user'));
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    const { result } = renderHook(() => useAuth());
    act(() => result.current.setIsLoginModalOpen(true));

    await act(async () => {
      await result.current.handleGoogleLogin();
    });

    expect(alertSpy).toHaveBeenCalled();
    expect(result.current.isLoginModalOpen).toBe(true);
  });

  it('signs out via Firebase on logout', async () => {
    onAuthStateChangedMock.mockImplementation(() => vi.fn());
    signOutMock.mockResolvedValue(undefined);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.handleLogout();
    });

    expect(signOutMock).toHaveBeenCalled();
  });
});
