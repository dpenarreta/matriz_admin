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
import { ConfiguracionPage as MatrizConfiguracionPage } from "../pages/Matriz/ConfiguracionPage";
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

/** Inicio: la matriz si tiene empresa; si no, el primer módulo de administración al que tiene acceso. */
function Home() {
  const { user } = useAuth();
  const { company, isLoading } = useCompany();
  if (isLoading) return null;
  return <Navigate to={homePathFor(user, Boolean(company))} replace />;
}

// Las rutas del antiguo panel `/admin` (template base) llevan a su lugar
// dentro de la interfaz única de la matriz.
const LEGACY_ADMIN = {
  users: "/sistema/usuarios",
  roles: "/sistema/roles",
  permissions: "/sistema/permisos",
  empresas: "/sistema/empresas",
  catalogos: "/sistema/catalogos",
  configuracion: "/sistema/identidad/identidad",
};

function LegacyAdminRedirect() {
  const { section, id } = useParams();
  const base = LEGACY_ADMIN[section] || "/";
  if (section === "configuracion" && id) return <Navigate to={`/sistema/identidad/${id}`} replace />;
  if (id) return <Navigate to={`${base}/${id === "new" ? "nuevo" : id}`} replace />;
  return <Navigate to={base} replace />;
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

      <Route path="/admin" element={<Navigate to="/sistema/usuarios" replace />} />
      <Route path="/admin/:section" element={<LegacyAdminRedirect />} />
      <Route path="/admin/:section/:id" element={<LegacyAdminRedirect />} />

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
        <Route path="/configuracion" element={matrix(<MatrizConfiguracionPage />)} />

        {/* Administración (módulos del template base, en la misma interfaz) */}
        <Route path="/sistema/usuarios" element={guarded("usuarios.ver", <UsersList />)} />
        <Route path="/sistema/usuarios/nuevo" element={guarded("usuarios.ver", <UserForm />)} />
        <Route path="/sistema/usuarios/:id" element={guarded("usuarios.ver", <UserForm />)} />
        <Route path="/sistema/roles" element={guarded("roles.ver", <RolesList />)} />
        <Route path="/sistema/roles/nuevo" element={guarded("roles.ver", <RoleForm />)} />
        <Route path="/sistema/roles/:id" element={guarded("roles.ver", <RoleForm />)} />
        <Route path="/sistema/permisos" element={guarded("permisos.ver", <PermissionsPage />)} />
        <Route path="/sistema/empresas" element={guarded("empresas.ver", <CompaniesPage />)} />
        <Route path="/sistema/catalogos" element={guarded("catalogos.ver", <CatalogsPage />)} />
        <Route path="/sistema/auditoria" element={guarded("auditoria.ver", <AuditoriaSistemaPage />)} />
        <Route path="/sistema/identidad" element={<Navigate to="/sistema/identidad/identidad" replace />} />
        <Route path="/sistema/identidad/:tab" element={guarded("configuracion.ver", <IdentidadPage />)} />

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
