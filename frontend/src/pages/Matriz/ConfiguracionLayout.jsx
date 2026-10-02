import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { useCompany } from "../../context/CompanyContext";
import { useConfigTabs } from "./ConfiguracionWindows";

/**
 * Configuración: una sola pantalla con una pestaña por tema (empresas,
 * recordatorios, usuarios, roles, permisos, catálogos, identidad visual y
 * auditoría). Cada pestaña tiene su propia ruta (`/configuracion/<pestaña>`)
 * y es una ventana independiente; se muestra solo con el permiso que la abre.
 */
export function ConfiguracionLayout() {
  const { company } = useCompany();
  const location = useLocation();
  const tabs = useConfigTabs();

  if (location.pathname.replace(/\/$/, "") === "/configuracion") {
    return tabs[0] ? <Navigate to={`/configuracion/${tabs[0].path}`} replace /> : <Navigate to="/403" replace />;
  }

  return (
    <>
      <div className="mz-view-head">
        <div>
          <h2>Configuración</h2>
          <p className="mz-desc">
            {company ? `${company.short_name}: ` : ""}empresas, recordatorios, usuarios, roles, permisos, catálogos,
            identidad visual y auditoría.
          </p>
        </div>
      </div>
      <nav className="mz-tabs mz-config-tabs" aria-label="Secciones de configuración">
        {tabs.map((tab) => (
          <NavLink
            key={tab.path}
            to={`/configuracion/${tab.path}`}
            className={({ isActive }) => (isActive ? "is-active" : "")}
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <div className="mz-config-body">
        <Outlet />
      </div>
    </>
  );
}
