import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const recentToastRef = useRef({ key: null, time: 0 });

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const key = `${type}:${message}`;
    const now = Date.now();

    // Prevent the same failing request from flooding the UI with identical toasts.
    if (
      recentToastRef.current.key === key &&
      now - recentToastRef.current.time < 1500
    ) {
      return;
    }

    recentToastRef.current = { key, time: now };
    const id = `${now}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration);
  }, []);

  const toast = useMemo(
    () => ({
      success: (msg) => addToast(msg, 'success'),
      error: (msg) => addToast(msg, 'error'),
      info: (msg) => addToast(msg, 'info'),
    }),
    [addToast],
  );

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toasts} />
    </ToastContext.Provider>
  );
}

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

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
