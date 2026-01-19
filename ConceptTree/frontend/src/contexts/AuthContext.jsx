import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi, tokenManager } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // 初始化：检查是否有有效token
  useEffect(() => {
    const token = tokenManager.get();
    if (token) {
      // 有token，假设已登录（可以选择验证token）
      setIsAuthenticated(true);
      // 从token中解析用户信息（简化版，实际应该解析JWT）
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUser({ id: payload.sub });
      } catch (error) {
        console.error('Failed to parse token', error);
        tokenManager.remove();
        setIsAuthenticated(false);
      }
    }
    setIsLoading(false);
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
