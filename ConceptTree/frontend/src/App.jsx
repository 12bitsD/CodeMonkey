import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AppProvider } from './contexts/AppContext';
import { ToastProvider } from './contexts/ToastContext';
import { HomePage, GraphPage, MyLearningPage } from './pages';
import AuthPage from './pages/AuthPage';
import DeepLearnPage from './pages/DeepLearnPage';
import CompletionNotePage from './pages/CompletionNotePage';
import ProtectedRoute from './components/common/ProtectedRoute';
import AppErrorBoundary from './components/common/AppErrorBoundary';
import DataSyncStatusBanner from './components/common/DataSyncStatusBanner';
import { LanguageProvider } from './contexts/LanguageContext';

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <ToastProvider>
          <AppProvider>
            <BrowserRouter>
              <AppErrorBoundary>
              <div className="min-h-screen bg-[var(--color-canvas)] text-[var(--color-label)] font-sans selection:bg-blue-200 selection:text-zinc-950 antialiased overflow-hidden">
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
                  <Route
                    path="/deep-learn/:planId/:nodeId"
                    element={
                      <ProtectedRoute>
                        <DeepLearnPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/deep-learn/:planId/:nodeId/note/:noteId"
                    element={
                      <ProtectedRoute>
                        <CompletionNotePage />
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
    </LanguageProvider>
  );
}
