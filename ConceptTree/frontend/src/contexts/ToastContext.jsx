/**
 * Lightweight toast notification system with auto-dismiss.
 *
 * `ToastContext` provides a simple `{ success, error, info }` API that any
 * component can call to show a non-blocking, self-dismissing notification
 * at the bottom-right corner of the screen.
 *
 * Usage — call `useToast()` inside any component that is a child of
 * `<ToastProvider>`:
 * ```js
 * const toast = useToast();
 * toast.success('Plan created!');
 * toast.error('Failed to save changes.');
 * toast.info('Syncing...');
 * ```
 *
 * Implementation details:
 * - Each toast is assigned a unique ID (`Date.now()`) so multiple toasts can
 *   coexist without collisions.
 * - Auto-dismiss fires after `duration` milliseconds (default: 4 000 ms) via
 *   `setTimeout`. The timeout is set at creation time — there is no pause or
 *   cancel mechanism.
 * - `ToastContainer` renders as a `fixed` overlay (`bottom-6 right-6`, `z-50`)
 *   so it floats above all page content without affecting layout.
 *
 * @module contexts/ToastContext
 */
import React, { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext(null);

/**
 * Provides toast notification state and the `addToast` internal dispatcher.
 *
 * Renders `ToastContainer` as a sibling to `children` so toasts appear
 * regardless of which page is active. `ToastProvider` must sit above any
 * provider that calls `toast.error()` (e.g., `AppProvider`) in the tree.
 *
 * @param {{ children: React.ReactNode }} props
 * @returns {JSX.Element}
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  /**
   * Creates a toast notification and schedules its removal.
   *
   * @param {string} message - Human-readable notification text.
   * @param {'success'|'error'|'info'} [type='info'] - Controls the background colour.
   * @param {number} [duration=4000] - Auto-dismiss delay in milliseconds.
   */
  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration);
  }, []);

  /**
   * The context value — three convenience methods that pre-fill `type`.
   * Call these directly: `toast.success('Done!')`.
   */
  const toast = {
    success: (msg) => addToast(msg, 'success'),
    error: (msg) => addToast(msg, 'error'),
    info: (msg) => addToast(msg, 'info'),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toasts} />
    </ToastContext.Provider>
  );
}

/**
 * Renders the stack of active toasts as a fixed overlay.
 *
 * Returns `null` when there are no active toasts to avoid adding a DOM node
 * when not needed. Each toast is colour-coded by type:
 * - `error`   → red (`bg-red-600`)
 * - `success` → teal (`bg-teal-600`)
 * - `info`    → dark (`bg-zinc-800`)
 *
 * @param {{ toasts: Array<{ id: number, message: string, type: string }> }} props
 * @returns {JSX.Element|null}
 */
function ToastContainer({ toasts }) {
  if (!toasts.length) return null;
  return (
    <div className="fixed bottom-6 right-6 flex flex-col gap-2 z-50">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`px-4 py-3 rounded-xl text-sm font-medium shadow-lg transition-all ${
            t.type === 'error' ? 'bg-red-600 text-white' :
            t.type === 'success' ? 'bg-teal-600 text-white' :
            'bg-zinc-800 text-white'
          }`}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}

/**
 * Accesses the toast API from any child component.
 *
 * Returns `{ success, error, info }` — call the appropriate method with a
 * message string to display a notification.
 *
 * @returns {{ success: (msg: string) => void, error: (msg: string) => void, info: (msg: string) => void }}
 * @throws {Error} When used outside a `<ToastProvider>`.
 */
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
