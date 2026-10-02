import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AdminLayout } from "../components/admin/AdminLayout/AdminLayout";
import { AppShell } from "../components/matriz/AppShell";
import { RequireAuth } from "../components/matriz/RequireAuth";
import { RequirePermission } from "../components/common/RequirePermission/RequirePermission";
import { useAuth } from "../hooks/useAuth";
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
import { CatalogsPage } from "../pages/Admin/Catalogos/CatalogsPage";
import { ConfiguracionPage } from "../pages/Admin/Configuracion/ConfiguracionPage";
import { CompaniesPage } from "../pages/Admin/Empresas/CompaniesPage";
import { PermissionsPage } from "../pages/Admin/Permissions/PermissionsPage";
import { Register } from "../pages/Register/Register";
import { RoleForm } from "../pages/Admin/Roles/RoleForm";
import { RolesList } from "../pages/Admin/Roles/RolesList";
import { UserForm } from "../pages/Admin/Users/UserForm";
import { UsersList } from "../pages/Admin/Users/UsersList";

const USUARIOS_VER = "usuarios.ver";
const ROLES_VER = "roles.ver";
const PERMISOS_VER = "permisos.ver";
const CONFIGURACION_VER = "configuracion.ver";
const CHANGE_PASSWORD_REQUIRED_PATH = "/change-password-required";

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
      <Route path="/" element={<Navigate to="/resumen" replace />} />
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/resumen" element={<ResumenPage />} />
        <Route path="/matriz" element={<MatrizPage />} />
        <Route path="/calendario" element={<CalendarioPage />} />
        <Route path="/documentos" element={<DocumentosPage />} />
        <Route path="/reportes" element={<ReportesPage />} />
        <Route path="/configuracion" element={<MatrizConfiguracionPage />} />
      </Route>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path={CHANGE_PASSWORD_REQUIRED_PATH} element={<ChangePasswordRequired />} />
      <Route path="/403" element={<Forbidden />} />

      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<Navigate to="/admin/users" replace />} />
        <Route
          path="users"
          element={
            <RequirePermission permission={USUARIOS_VER}>
              <UsersList />
            </RequirePermission>
          }
        />
        <Route
          path="users/new"
          element={
            <RequirePermission permission={USUARIOS_VER}>
              <UserForm />
            </RequirePermission>
          }
        />
        <Route
          path="users/:id"
          element={
            <RequirePermission permission={USUARIOS_VER}>
              <UserForm />
            </RequirePermission>
          }
        />
        <Route
          path="roles"
          element={
            <RequirePermission permission={ROLES_VER}>
              <RolesList />
            </RequirePermission>
          }
        />
        <Route
          path="roles/new"
          element={
            <RequirePermission permission={ROLES_VER}>
              <RoleForm />
            </RequirePermission>
          }
        />
        <Route
          path="roles/:id"
          element={
            <RequirePermission permission={ROLES_VER}>
              <RoleForm />
            </RequirePermission>
          }
        />
        <Route
          path="permissions"
          element={
            <RequirePermission permission={PERMISOS_VER}>
              <PermissionsPage />
            </RequirePermission>
          }
        />
        <Route
          path="empresas"
          element={
            <RequirePermission permission="empresas.ver">
              <CompaniesPage />
            </RequirePermission>
          }
        />
        <Route
          path="catalogos"
          element={
            <RequirePermission permission="catalogos.ver">
              <CatalogsPage />
            </RequirePermission>
          }
        />
        <Route path="configuracion" element={<Navigate to="/admin/configuracion/identidad" replace />} />
        <Route
          path="configuracion/identidad"
          element={
            <RequirePermission permission={CONFIGURACION_VER}>
              <ConfiguracionPage />
            </RequirePermission>
          }
        />
        <Route
          path="configuracion/colores-tipografia"
          element={
            <RequirePermission permission={CONFIGURACION_VER}>
              <ConfiguracionPage />
            </RequirePermission>
          }
        />
        <Route
          path="configuracion/apariencia"
          element={
            <RequirePermission permission={CONFIGURACION_VER}>
              <ConfiguracionPage />
            </RequirePermission>
          }
        />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
