import { createContext, useCallback, useContext, useMemo, useState } from "react";

import { Icon } from "../components/common/Icon/Icon";

const ToastContext = createContext(null);
const DURATION_MS = 4600;

/** Avisos breves en la esquina inferior derecha (equivalente a `toast()` del mockup). */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const notify = useCallback((title, message = "", kind = "ok") => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((list) => [...list, { id, title, message, kind }]);
    setTimeout(() => setToasts((list) => list.filter((toast) => toast.id !== id)), DURATION_MS);
  }, []);

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="mz-toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`mz-toast mz-toast--${toast.kind}`} role="status">
            <Icon name={toast.kind === "bad" ? "exclamation-triangle" : "check-circle"} />
            <span>
              <b>{toast.title}</b>
              {toast.message}
            </span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast debe usarse dentro de un <ToastProvider>.");
  }
  return context.notify;
}
