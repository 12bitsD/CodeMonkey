import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AppProvider } from './contexts/AppContext';
import { ToastProvider } from './contexts/ToastContext';
import { HomePage, GraphPage, MyLearningPage } from './pages';
import AuthPage from './pages/AuthPage';
import ProtectedRoute from './components/common/ProtectedRoute';
import AppErrorBoundary from './components/common/AppErrorBoundary';
import DataSyncStatusBanner from './components/common/DataSyncStatusBanner';

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppProvider>
          <BrowserRouter>
            <AppErrorBoundary>
              <div className="min-h-screen bg-[#FAFAFA] text-zinc-900 font-sans selection:bg-zinc-200 selection:text-zinc-900 antialiased overflow-hidden">
                <DataSyncStatusBanner />
                <Routes>
                  <Route path="/auth" element={<AuthPage />} />
                  <Route path="/" element={<HomePage />} />
                  <Route 
                    path="/graph/:planId" 
                    element={
                      <ProtectedRoute>
                        <GraphPage />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/my-learning" 
                    element={
                      <ProtectedRoute>
                        <MyLearningPage />
                      </ProtectedRoute>
                    } 
                  />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </div>
            </AppErrorBoundary>
          </BrowserRouter>
        </AppProvider>
      </ToastProvider>
    </AuthProvider>
  );
}
