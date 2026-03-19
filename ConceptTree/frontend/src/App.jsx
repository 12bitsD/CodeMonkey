/**
 * Root application component — defines the global provider stack and all client-side routes.
 *
 * The provider nesting order is intentional and must be preserved:
 *   AuthProvider (outermost) → ToastProvider → AppProvider → BrowserRouter
 *
 * Why this order?
 * - `AppProvider` reads `isAuthenticated` from `AuthContext`, so `AuthProvider`
 *   must wrap it.
 * - `AppProvider` calls `toast.error()` on data-load failures, so `ToastProvider`
 *   must also be above `AppProvider`.
 * - `BrowserRouter` is innermost so that page components can navigate freely.
 *
 * Routes:
 * - `/`             → HomePage (public)
 * - `/auth`         → AuthPage (public — login / register)
 * - `/graph/:planId`→ GraphPage (protected — requires login)
 * - `/my-learning`  → MyLearningPage (protected — requires login)
 * - `*`             → redirects to `/`
 *
 * @module App
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AppProvider } from './contexts/AppContext';
import { ToastProvider } from './contexts/ToastContext';
import { HomePage, GraphPage, MyLearningPage } from './pages';
import AuthPage from './pages/AuthPage';
import ProtectedRoute from './components/common/ProtectedRoute';

/**
 * App is the single root React component rendered into `#root`.
 *
 * It is stateless — all state lives in the providers above.
 * To add a new route, import the page component and add a `<Route>` inside
 * the existing `<Routes>`. Wrap it in `<ProtectedRoute>` if it requires auth.
 *
 * @returns {JSX.Element} The full provider and routing tree.
 */
export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppProvider>
          <BrowserRouter>
          <div className="min-h-screen bg-[#FAFAFA] text-zinc-900 font-sans selection:bg-zinc-200 selection:text-zinc-900 antialiased overflow-hidden">
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
          </BrowserRouter>
        </AppProvider>
      </ToastProvider>
    </AuthProvider>
  );
}
