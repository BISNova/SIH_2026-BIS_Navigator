import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  registerUser,
  loginUser,
  fetchCurrentUser,
  fetchStagedChanges,
  reviewStagedChange,
  AuthAPIError,
} from './auth';

const TOKEN_KEY = 'bisnova_auth_token';
const USER_KEY = 'bisnova_auth_user';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    const cached = localStorage.getItem(USER_KEY);
    return cached ? JSON.parse(cached) : null;
  });
  // True until the initial /auth/me check (if a token exists) resolves -
  // lets App.jsx avoid a flash of "logged out" UI on refresh.
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  // Flips true whenever any protected call gets a 401 (expired/invalid
  // token, per backend: 60 min expiry, no refresh token). App.jsx watches
  // this to redirect to the login page, then calls clearSessionExpired().
  const [sessionExpired, setSessionExpired] = useState(false);

  const persistSession = useCallback((newToken, newUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
  }, []);

  const clearSession = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  // On first load: if a token was saved from a previous session, verify
  // it's still good via /auth/me rather than trusting the cached user
  // blindly (it may have expired since the last visit - 60 min tokens,
  // no refresh, so this is the normal case, not an edge case).
  useEffect(() => {
    let cancelled = false;

    async function verify() {
      const savedToken = localStorage.getItem(TOKEN_KEY);
      if (!savedToken) {
        setIsLoadingAuth(false);
        return;
      }
      try {
        const current = await fetchCurrentUser(savedToken);
        if (!cancelled) {
          setToken(savedToken);
          setUser(current);
          localStorage.setItem(USER_KEY, JSON.stringify(current));
        }
      } catch {
        if (!cancelled) clearSession();
      } finally {
        if (!cancelled) setIsLoadingAuth(false);
      }
    }

    verify();
    return () => { cancelled = true; };
  }, [clearSession]);

  async function login(email, password) {
    const result = await loginUser({ email, password });
    persistSession(result.access_token, result.user);
    return result.user;
  }

  // Deliberately does NOT auto-login after registering, for any role -
  // this is what makes "lab registers -> pending -> login blocked" work
  // correctly without special-casing: the user always goes through the
  // login page next, where a pending account gets a clear 403 message
  // instead of silently succeeding into the app.
  function register({ name, email, password, role }) {
    return registerUser({ name, email, password, role });
  }

  function logout() {
    clearSession();
  }

  function clearSessionExpired() {
    setSessionExpired(false);
  }

  // Wrapper for calling protected endpoints (admin dashboard, mainly).
  // Centralizes "attach the token, and on 401 clear the session and flag
  // it for App.jsx to redirect" so no component has to remember to do
  // this itself.
  const authRequest = useCallback(
    async (fn, ...args) => {
      try {
        return await fn(token, ...args);
      } catch (err) {
        if (err instanceof AuthAPIError && err.status === 401) {
          clearSession();
          setSessionExpired(true);
        }
        throw err;
      }
    },
    [token, clearSession]
  );

  const getStagedChanges = useCallback(
    () => authRequest(fetchStagedChanges),
    [authRequest]
  );

  const submitReview = useCallback(
    (decision) => authRequest(reviewStagedChange, decision),
    [authRequest]
  );

  const value = {
    user,
    token,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    isLoadingAuth,
    sessionExpired,
    login,
    register,
    logout,
    clearSessionExpired,
    getStagedChanges,
    submitReview,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside an <AuthProvider>');
  }
  return ctx;
}