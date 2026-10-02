import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";

/** Exige sesión iniciada. La matriz no depende de los permisos del catálogo
 * administrativo: el acceso de negocio lo decide la membresía por empresa. */
export function RequireAuth({ children }) {
  const { isAuthenticated, isInitializing } = useAuth();
  const location = useLocation();

  if (isInitializing) {
    return null;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return children;
}
