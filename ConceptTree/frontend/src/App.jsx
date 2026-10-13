import React, { Suspense } from 'react';
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

const AdminPage = React.lazy(() => import('./pages/admin/AdminPage'));

const PublicApplication = () => (
  <AppProvider>
    <DataSyncStatusBanner />
    <Routes>
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/" element={<HomePage />} />
      <Route
        path="/graph/:planId"
        element={<ProtectedRoute><GraphPage /></ProtectedRoute>}
      />
      <Route
        path="/my-learning"
        element={<ProtectedRoute><MyLearningPage /></ProtectedRoute>}
      />
      <Route
        path="/deep-learn/:planId/:nodeId"
        element={<ProtectedRoute><DeepLearnPage /></ProtectedRoute>}
      />
      <Route
        path="/deep-learn/:planId/:nodeId/note/:noteId"
        element={<ProtectedRoute><CompletionNotePage /></ProtectedRoute>}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </AppProvider>
);

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <AppErrorBoundary>
              <div className="min-h-screen overflow-hidden bg-[var(--color-canvas)] font-sans text-[var(--color-label)] selection:bg-zinc-200 selection:text-zinc-950 antialiased">
                <Routes>
                  <Route
                    path="/admin/*"
                    element={
                      <ProtectedRoute>
                        <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-sm text-zinc-500">正在加载管理员后台…</div>}>
                          <AdminPage />
                        </Suspense>
                      </ProtectedRoute>
                    }
                  />
                  <Route path="*" element={<PublicApplication />} />
                </Routes>
              </div>
            </AppErrorBoundary>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </LanguageProvider>
  );
}
