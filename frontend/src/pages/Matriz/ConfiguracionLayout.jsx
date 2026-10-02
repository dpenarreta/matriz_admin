import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { useCompany } from "../../context/CompanyContext";
import { useAuth } from "../../hooks/useAuth";

/**
 * Configuración: una sola pantalla con una pestaña por módulo. Cada pestaña
 * tiene su propia ruta (`/configuracion/<pestaña>`) y es una ventana
 * independiente. Las de la empresa activa dependen de los permisos `matriz.*`
 * del rol en esa empresa; las del sistema (módulos del template base),
 * de los permisos del catálogo del usuario.
 */
export const COMPANY_TABS = [
  { path: "empresa", label: "Empresa" },
  { path: "recordatorios", label: "Recordatorios" },
  { path: "miembros", label: "Usuarios y roles de la empresa", capability: "gestionar_miembros" },
  { path: "auditoria", label: "Auditoría de la empresa", capability: "ver_auditoria" },
];

export const SYSTEM_TABS = [
  { path: "usuarios", label: "Usuarios", permission: "usuarios.ver" },
  { path: "roles", label: "Roles", permission: "roles.ver" },
  { path: "permisos", label: "Permisos", permission: "permisos.ver" },
  { path: "empresas", label: "Empresas", permission: "empresas.ver" },
  { path: "catalogos", label: "Catálogos", permission: "catalogos.ver" },
  { path: "identidad", label: "Identidad visual", permission: "configuracion.ver" },
  { path: "auditoria-sistema", label: "Auditoría del sistema", permission: "auditoria.ver" },
];

/** Pestañas que el usuario puede abrir, en orden. */
export function visibleConfigTabs(user, company, can) {
  const companyTabs = company ? COMPANY_TABS.filter((tab) => !tab.capability || can(tab.capability)) : [];
  const systemTabs = SYSTEM_TABS.filter((tab) => user?.permissions?.includes(tab.permission));
  return { companyTabs, systemTabs };
}

export function ConfiguracionLayout() {
  const { user } = useAuth();
  const { company, can } = useCompany();
  const location = useLocation();
  const { companyTabs, systemTabs } = visibleConfigTabs(user, company, can);
  const first = companyTabs[0] || systemTabs[0];

  if (location.pathname.replace(/\/$/, "") === "/configuracion") {
    return first ? <Navigate to={`/configuracion/${first.path}`} replace /> : <Navigate to="/403" replace />;
  }

  const tab = (item) => (
    <NavLink
      key={item.path}
      to={`/configuracion/${item.path}`}
      className={({ isActive }) => (isActive ? "is-active" : "")}
    >
      {item.label}
    </NavLink>
  );

  return (
    <>
      <div className="mz-view-head">
        <div>
          <h2>Configuración</h2>
          <p className="mz-desc">
            {company ? `Parámetros de ${company.short_name}, ` : ""}usuarios, roles, permisos, empresas, catálogos,
            identidad visual y trazabilidad.
          </p>
        </div>
      </div>
      <nav className="mz-tabs mz-config-tabs" aria-label="Secciones de configuración">
        {companyTabs.map(tab)}
        {companyTabs.length > 0 && systemTabs.length > 0 && <span className="mz-tabs-sep" aria-hidden="true" />}
        {systemTabs.map(tab)}
      </nav>
      <div className="mz-config-body">
        <Outlet />
      </div>
    </>
  );
}
