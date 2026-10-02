import { BrowserRouter } from "react-router-dom";

import { AppearanceProvider } from "./context/AppearanceContext";
import { AuthProvider } from "./context/AuthContext";
import { CompanyProvider } from "./context/CompanyContext";
import { ThemeProvider } from "./context/ThemeContext";
import { ToastProvider } from "./context/ToastContext";
import { AppRoutes } from "./routes/AppRoutes";

export function App() {
  return (
    <AppearanceProvider>
      <ThemeProvider>
        <AuthProvider>
          <CompanyProvider>
            <ToastProvider>
              <BrowserRouter>
                <AppRoutes />
              </BrowserRouter>
            </ToastProvider>
          </CompanyProvider>
        </AuthProvider>
      </ThemeProvider>
    </AppearanceProvider>
  );
}
