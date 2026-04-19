import React, { createContext, useContext, useEffect, useState } from "react";
import {
  AUTH_EXPIRED_EVENT,
  authApi,
  tokenManager,
} from "../services/api";

const AuthContext = createContext();

const clearAuthState = (setIsAuthenticated, setUser) => {
  tokenManager.remove();
  setUser(null);
  setIsAuthenticated(false);
};

const decodeBase64Url = (value) => {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const paddingLength = (4 - (normalized.length % 4)) % 4;
  return atob(`${normalized}${"=".repeat(paddingLength)}`);
};

const parseTokenPayload = (token) => {
  const [, payloadPart] = token.split(".");
  if (!payloadPart) {
    throw new Error("Missing JWT payload");
  }

  const payload = JSON.parse(decodeBase64Url(payloadPart));
  if (!payload?.sub) {
    throw new Error("Missing JWT subject");
  }

  if (payload.exp && Date.now() >= payload.exp * 1000) {
    throw new Error("JWT expired");
  }

  return payload;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = tokenManager.get();
    if (token) {
      try {
        const payload = parseTokenPayload(token);
        setUser({ id: payload.sub });
        setIsAuthenticated(true);
      } catch (error) {
        console.error("Failed to restore token", error);
        clearAuthState(setIsAuthenticated, setUser);
      }
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    const handleAuthExpired = () => {
      clearAuthState(setIsAuthenticated, setUser);
    };

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    };
  }, []);

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

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      clearAuthState(setIsAuthenticated, setUser);
    }
  };

  const value = {
    isAuthenticated,
    user,
    isLoading,
    register,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
