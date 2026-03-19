/**
 * Authentication state context — JWT lifecycle, login, register, and logout.
 *
 * `AuthContext` owns the single source of truth for who is logged in.
 * It manages JWT storage/retrieval via `tokenManager` and exposes three
 * async actions (`login`, `register`, `logout`) that components can call
 * without caring about token plumbing.
 *
 * Context value shape:
 * ```js
 * {
 *   isAuthenticated: boolean, // true once a valid token has been confirmed
 *   user: { id: string }|null, // decoded from the JWT payload (sub claim)
 *   isLoading: boolean,         // true during the initial token hydration check
 *   login(email, password): Promise<{ success: boolean, data?: *, error?: string }>,
 *   register(email, password): Promise<{ success: boolean, data?: *, error?: string }>,
 *   logout(): Promise<void>,
 * }
 * ```
 *
 * Token hydration: on mount, the provider checks localStorage for an existing
 * JWT. If found, it decodes the payload (base64) to extract the user ID and
 * sets `isAuthenticated = true` — **without a network round-trip**. If parsing
 * fails the token is discarded and the user is treated as logged out.
 *
 * Consumers that gate rendering on auth state (e.g., `ProtectedRoute`) must
 * wait for `isLoading === false` before making routing decisions, otherwise
 * they may redirect before the token check completes.
 *
 * @module contexts/AuthContext
 */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi, tokenManager } from '../services/api';

const AuthContext = createContext();

/**
 * Accesses the authentication context from any child component.
 *
 * Throws a descriptive error when called outside `AuthProvider` so
 * misconfigured trees fail loudly during development.
 *
 * @returns {{ isAuthenticated: boolean, user: {id: string}|null, isLoading: boolean, login: Function, register: Function, logout: Function }}
 * @throws {Error} When used outside an `<AuthProvider>`.
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

/**
 * Provides JWT-based authentication state and actions to the component tree.
 *
 * This must be the **outermost** provider in `App.jsx` because `AppProvider`
 * reads `isAuthenticated` from this context to decide whether to fetch data.
 *
 * @param {{ children: React.ReactNode }} props
 * @returns {JSX.Element}
 */
export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = tokenManager.get();
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUser({ id: payload.sub });
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Failed to parse token', error);
        tokenManager.remove();
        setIsAuthenticated(false);
      }
    }
    setIsLoading(false);
  }, []);

  /**
   * Creates a new user account, stores the returned token, and marks the
   * session as authenticated.
   *
   * Returns a result object rather than throwing so the calling UI can display
   * form-level validation errors without a try/catch.
   *
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{ success: true, data: * } | { success: false, error: string }>}
   */
  const register = async (email, password) => {
    try {
      const data = await authApi.register(email, password);
      tokenManager.set(data.token);
      setUser(data.user);
      setIsAuthenticated(true);
      return { success: true, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  /**
   * Authenticates an existing user, stores the returned token, and marks the
   * session as authenticated.
   *
   * Returns a result object rather than throwing so the calling UI can display
   * form-level validation errors without a try/catch.
   *
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{ success: true, data: * } | { success: false, error: string }>}
   */
  const login = async (email, password) => {
    try {
      const data = await authApi.login(email, password);
      tokenManager.set(data.token);
      setUser(data.user);
      setIsAuthenticated(true);
      return { success: true, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  /**
   * Ends the user's session.
   *
   * Calls the backend logout endpoint, then **always** clears the local token
   * and resets auth state — even if the network request fails. This ensures
   * the UI is never stuck in an authenticated-but-invalid state.
   *
   * @returns {Promise<void>}
   */
  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      tokenManager.remove();
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const value = {
    isAuthenticated,
    user,
    isLoading,
    register,
    login,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
