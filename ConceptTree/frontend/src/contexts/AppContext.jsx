import React, { createContext, useContext, useState, useEffect } from 'react';
import { userProfileApi, plansApi, notesApi, tokenManager } from '../services/api';
import { createEmptyUserProfile } from '../types';
import { useAuth } from './AuthContext';

const AppContext = createContext();

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }) => {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  
  // 全局状态
  const [userProfile, setUserProfile] = useState(createEmptyUserProfile());
  const [plans, setPlans] = useState([]);
  const [allNotes, setAllNotes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // 初始化加载数据（仅在已登录时）
  useEffect(() => {
    const loadInitialData = async () => {
      // 等待认证状态加载完成
      if (authLoading) return;
      
      setIsLoading(true);
      try {
        if (isAuthenticated) {
          // 已登录，从后端加载数据
          const [profile, plansList, notesList] = await Promise.all([
            userProfileApi.get(),
            plansApi.list(),
            notesApi.list()
          ]);
          
          if (profile) setUserProfile(profile);
          if (plansList) setPlans(plansList);
          if (notesList) setAllNotes(notesList);
        } else {
          // 未登录，使用默认数据
          setUserProfile(createEmptyUserProfile());
          setPlans([]);
          setAllNotes([]);
        }
      } catch (error) {
        console.error('初始化加载数据失败', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadInitialData();
  }, [isAuthenticated, authLoading]);

  // 业务逻辑 - 计划相关
  const createPlan = async (input, graphResult) => {
    try {
      const newPlan = await plansApi.create({
        title: graphResult.interpretation || input,
        nodes: graphResult.nodes,
        edges: graphResult.edges
      });
      setPlans(prev => [newPlan, ...prev]);
      return newPlan;
    } catch (error) {
      console.error('创建计划失败', error);
      throw error;
    }
  };

  const updatePlan = async (id, data) => {
    try {
      const updated = await plansApi.update(id, data);
      setPlans(prev => prev.map(p => p.id === id ? { ...p, ...updated } : p));
      return updated;
    } catch (error) {
      console.error('更新计划失败', error);
    }
  };
  
  const archivePlan = async (id) => {
    try {
      await plansApi.archive(id);
      setPlans(prev => prev.map(p => p.id === id ? { ...p, status: 'archived' } : p));
    } catch (error) {
      console.error('归档计划失败', error);
    }
  };

  const deletePlan = async (id) => {
    try {
      await plansApi.delete(id);
      setPlans(prev => prev.filter(p => p.id !== id));
    } catch (error) {
      console.error('删除计划失败', error);
    }
  };

  // 业务逻辑 - 笔记相关
  const addNote = async (planId, nodeId, content) => {
    try {
      const newNote = await notesApi.create(planId, nodeId, content);
      setAllNotes(prev => [newNote, ...prev]);
      return newNote;
    } catch (error) {
      console.error('添加笔记失败', error);
    }
  };

  // 业务逻辑 - 用户相关
  const updateUserProfile = async (newProfile) => {
    try {
      const updated = await userProfileApi.update(newProfile);
      setUserProfile(updated);
    } catch (error) {
      console.error('更新用户画像失败', error);
    }
  };

  const value = {
    userProfile,
    plans,
    allNotes,
    isLoading,
    actions: {
      setUserProfile: updateUserProfile,
      setPlans, // 暴露原始 setter 以备不时之需
      createPlan,
      updatePlan,
      archivePlan,
      deletePlan,
      addNote
    }
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};
