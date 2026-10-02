import { useState } from "react";
import { Navigate } from "react-router-dom";

import { useCompany } from "../../context/CompanyContext";
import { useAuth } from "../../hooks/useAuth";
import { CompaniesPage } from "../Admin/Empresas/CompaniesPage";
import { UsersList } from "../Admin/Users/UsersList";
import { AuditoriaSistemaPage } from "../Sistema/AuditoriaSistemaPage";
import { AuditTab, CompanyTab, MembersTab } from "./ConfiguracionEmpresaTabs";

/**
 * Ventanas de Configuración que unen lo de la empresa activa con lo del
 * sistema, para que no haya dos pestañas que hagan lo mismo. Cada una
 * muestra la versión completa a quien tiene el permiso del catálogo y la
 * versión de su empresa a quien solo tiene el permiso `matriz.*` en ella.
 */

function useAccess() {
  const { user } = useAuth();
  const { company, can } = useCompany();
  const has = (permission) => Boolean(user?.permissions?.includes(permission));
  return { company, can: (capability) => Boolean(company) && can(capability), has };
}

/** Empresas: todas (empresas.ver) o solo la empresa activa (matriz.configurar). */
export function EmpresasWindow() {
  const { has, can } = useAccess();
  if (has("empresas.ver")) return <CompaniesPage />;
  return can("configurar") ? <CompanyTab /> : <Navigate to="/403" replace />;
}

/** Usuarios: todo el sistema (usuarios.ver) o las personas de la empresa activa (matriz.gestionar_miembros). */
export function UsuariosWindow() {
  const { has, can } = useAccess();
  if (has("usuarios.ver")) return <UsersList />;
  return can("gestionar_miembros") ? <MembersTab /> : <Navigate to="/403" replace />;
}

/** Auditoría: de la empresa (matriz.ver_auditoria) y del sistema (auditoria.ver), en una sola ventana. */
export function AuditoriaWindow() {
  const { can, has } = useAccess();
  const views = [
    can("ver_auditoria") && ["empresa", "Obligaciones de la empresa"],
    has("auditoria.ver") && ["sistema", "Sistema"],
  ].filter(Boolean);
  const [view, setView] = useState(views[0]?.[0]);

  if (views.length === 0) return <Navigate to="/403" replace />;
  return (
    <>
      {views.length > 1 && (
        <div className="mz-chips mb-3" role="group" aria-label="Qué auditoría ver">
          {views.map(([key, label]) => (
            <button key={key} type="button" className={view === key ? "is-on" : ""} onClick={() => setView(key)}>
              {label}
            </button>
          ))}
        </div>
      )}
      {view === "empresa" ? <AuditTab /> : <AuditoriaSistemaPage />}
    </>
  );
}

/** Pestañas de Configuración: una por tema, sin repetidos. */
export const CONFIG_TABS = [
  {
    path: "empresas",
    label: "Empresas",
    visible: ({ has, can }) => has("empresas.ver") || can("configurar"),
  },
  { path: "recordatorios", label: "Recordatorios", visible: ({ company }) => Boolean(company) },
  {
    path: "usuarios",
    label: "Usuarios",
    visible: ({ has, can }) => has("usuarios.ver") || can("gestionar_miembros"),
  },
  { path: "roles", label: "Roles", visible: ({ has }) => has("roles.ver") },
  { path: "permisos", label: "Permisos", visible: ({ has }) => has("permisos.ver") },
  { path: "catalogos", label: "Catálogos", visible: ({ has }) => has("catalogos.ver") },
  { path: "identidad", label: "Identidad visual", visible: ({ has }) => has("configuracion.ver") },
  {
    path: "auditoria",
    label: "Auditoría",
    visible: ({ has, can }) => has("auditoria.ver") || can("ver_auditoria"),
  },
];

export function useConfigTabs() {
  const access = useAccess();
  return CONFIG_TABS.filter((tab) => tab.visible(access));
}

/** Permisos del catálogo que abren alguna pestaña sin necesitar empresa. */
export const SYSTEM_PERMISSIONS = [
  "empresas.ver",
  "usuarios.ver",
  "roles.ver",
  "permisos.ver",
  "catalogos.ver",
  "configuracion.ver",
  "auditoria.ver",
];
