import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";

import { RequirePermission } from "../components/common/RequirePermission/RequirePermission";
import { AppShell, homePathFor, RequireCompany } from "../components/matriz/AppShell";
import { RequireAuth } from "../components/matriz/RequireAuth";
import { useCompany } from "../context/CompanyContext";
import { useAuth } from "../hooks/useAuth";
import { CatalogsPage } from "../pages/Admin/Catalogos/CatalogsPage";
import { ConfiguracionPage as IdentidadPage } from "../pages/Admin/Configuracion/ConfiguracionPage";
import { CompaniesPage } from "../pages/Admin/Empresas/CompaniesPage";
import { PermissionsPage } from "../pages/Admin/Permissions/PermissionsPage";
import { RoleForm } from "../pages/Admin/Roles/RoleForm";
import { RolesList } from "../pages/Admin/Roles/RolesList";
import { UserForm } from "../pages/Admin/Users/UserForm";
import { UsersList } from "../pages/Admin/Users/UsersList";
import { Forbidden } from "../pages/Errors/Forbidden";
import { NotFound } from "../pages/Errors/NotFound";
import { Login } from "../pages/Login/Login";
import { CalendarioPage } from "../pages/Matriz/CalendarioPage";
import {
  AuditTab,
  CompanyTab,
  MembersTab,
  RemindersConfigTab,
} from "../pages/Matriz/ConfiguracionEmpresaTabs";
import { ConfiguracionLayout } from "../pages/Matriz/ConfiguracionLayout";
import { DocumentosPage } from "../pages/Matriz/DocumentosPage";
import { MatrizPage } from "../pages/Matriz/MatrizPage";
import { ReportesPage } from "../pages/Matriz/ReportesPage";
import { ResumenPage } from "../pages/Matriz/ResumenPage";
import { ChangePasswordRequired } from "../pages/PasswordReset/ChangePasswordRequired";
import { ForgotPassword } from "../pages/PasswordReset/ForgotPassword";
import { ResetPassword } from "../pages/PasswordReset/ResetPassword";
import { Register } from "../pages/Register/Register";
import { AuditoriaSistemaPage } from "../pages/Sistema/AuditoriaSistemaPage";

const CHANGE_PASSWORD_REQUIRED_PATH = "/change-password-required";

function guarded(permission, element) {
  return <RequirePermission permission={permission}>{element}</RequirePermission>;
}

function matrix(element) {
  return <RequireCompany>{element}</RequireCompany>;
}

/** Inicio: la matriz si tiene empresa; si no, Configuración (módulos del sistema). */
function Home() {
  const { user } = useAuth();
  const { company, isLoading } = useCompany();
  if (isLoading) return null;
  return <Navigate to={homePathFor(user, Boolean(company))} replace />;
}

// Las rutas anteriores (`/admin/...` del template base y `/sistema/...`)
// llevan a su pestaña dentro de Configuración.
const LEGACY_SECTIONS = {
  users: "usuarios",
  usuarios: "usuarios",
  roles: "roles",
  permissions: "permisos",
  permisos: "permisos",
  empresas: "empresas",
  catalogos: "catalogos",
  configuracion: "identidad/identidad",
  identidad: "identidad/identidad",
  auditoria: "auditoria-sistema",
};

function LegacyRedirect() {
  const { section, id } = useParams();
  const target = LEGACY_SECTIONS[section];
  if (!target) return <Navigate to="/configuracion" replace />;
  if (id && (section === "configuracion" || section === "identidad")) {
    return <Navigate to={`/configuracion/identidad/${id}`} replace />;
  }
  if (id) return <Navigate to={`/configuracion/${target}/${id === "new" ? "nuevo" : id}`} replace />;
  return <Navigate to={`/configuracion/${target}`} replace />;
}

export function AppRoutes() {
  const { user } = useAuth();
  const location = useLocation();

  // Único punto de gateo (no un componente por-ruta como RequirePermission,
  // que es por-permiso, no por-estado-global): mientras haya un cambio de
  // contraseña obligatorio pendiente, cualquier otra ruta redirige aquí. El
  // backend ya lo exige de verdad (SessionAuthentication.authenticate) —
  // esto es solo para que la navegación no quede varada en un 403.
  if (user?.must_change_password && location.pathname !== CHANGE_PASSWORD_REQUIRED_PATH) {
    return <Navigate to={CHANGE_PASSWORD_REQUIRED_PATH} replace />;
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path={CHANGE_PASSWORD_REQUIRED_PATH} element={<ChangePasswordRequired />} />

      <Route path="/admin" element={<Navigate to="/configuracion" replace />} />
      <Route path="/admin/:section" element={<LegacyRedirect />} />
      <Route path="/admin/:section/:id" element={<LegacyRedirect />} />
      <Route path="/sistema/:section" element={<LegacyRedirect />} />
      <Route path="/sistema/:section/:id" element={<LegacyRedirect />} />

      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Home />} />
        <Route path="/403" element={<Forbidden />} />

        {/* Matriz de obligaciones */}
        <Route path="/resumen" element={matrix(<ResumenPage />)} />
        <Route path="/matriz" element={matrix(<MatrizPage />)} />
        <Route path="/calendario" element={matrix(<CalendarioPage />)} />
        <Route path="/documentos" element={matrix(<DocumentosPage />)} />
        <Route path="/reportes" element={matrix(<ReportesPage />)} />

        {/* Configuración: cada pestaña es una ventana independiente con su ruta */}
        <Route path="/configuracion" element={<ConfiguracionLayout />}>
          <Route path="empresa" element={matrix(<CompanyTab />)} />
          <Route path="recordatorios" element={matrix(<RemindersConfigTab />)} />
          <Route path="miembros" element={matrix(<MembersTab />)} />
          <Route path="auditoria" element={matrix(<AuditTab />)} />
          <Route path="usuarios" element={guarded("usuarios.ver", <UsersList />)} />
          <Route path="usuarios/nuevo" element={guarded("usuarios.ver", <UserForm />)} />
          <Route path="usuarios/:id" element={guarded("usuarios.ver", <UserForm />)} />
          <Route path="roles" element={guarded("roles.ver", <RolesList />)} />
          <Route path="roles/nuevo" element={guarded("roles.ver", <RoleForm />)} />
          <Route path="roles/:id" element={guarded("roles.ver", <RoleForm />)} />
          <Route path="permisos" element={guarded("permisos.ver", <PermissionsPage />)} />
          <Route path="empresas" element={guarded("empresas.ver", <CompaniesPage />)} />
          <Route path="catalogos" element={guarded("catalogos.ver", <CatalogsPage />)} />
          <Route path="identidad" element={<Navigate to="/configuracion/identidad/identidad" replace />} />
          <Route path="identidad/:tab" element={guarded("configuracion.ver", <IdentidadPage />)} />
          <Route path="auditoria-sistema" element={guarded("auditoria.ver", <AuditoriaSistemaPage />)} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
