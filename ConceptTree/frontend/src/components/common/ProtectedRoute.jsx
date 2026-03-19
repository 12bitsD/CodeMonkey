/**
 * ProtectedRoute — guards a route behind authentication, redirecting unauthenticated
 * users to the /auth page while preserving their intended destination.
 *
 * Wrap any `<Route>` element whose children require login:
 *
 * @example
 * // In your router definition
 * <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
 *
 * Behaviour by auth state:
 *  - Loading  → full-screen "加载中..." spinner (prevents a flash of the login page)
 *  - Not authenticated → redirect to /auth?redirect=<current-path> (URL-encoded)
 *  - Authenticated → renders `children` directly
 *
 * The redirect query param lets the /auth page bounce the user back to where
 * they were after a successful login — encode it with encodeURIComponent so
 * paths with slashes survive the URL round-trip.
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

/**
 * Route wrapper that blocks unauthenticated access and shows a loading screen
 * while the auth state is being determined.
 *
 * @param {Object}          props
 * @param {React.ReactNode} props.children - The protected page/component to render when authenticated
 */
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Show a full-screen loading indicator while the auth context resolves its initial state.
  // Without this, unauthenticated users would briefly see the redirect flash.
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-zinc-600">加载中...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Encode the current pathname so the /auth page can redirect back after login.
    // encodeURIComponent handles paths with slashes that would otherwise break query string parsing.
    return <Navigate to={`/auth?redirect=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return children;
}
