import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConfiguracionLayout } from "../src/pages/Matriz/ConfiguracionLayout";

let authState;
let companyState;

vi.mock("../src/hooks/useAuth", () => ({ useAuth: () => authState }));
vi.mock("../src/context/CompanyContext", () => ({ useCompany: () => companyState }));

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/configuracion" element={<ConfiguracionLayout />}>
          <Route path="empresa" element={<p>ventana empresa</p>} />
          <Route path="usuarios" element={<p>ventana usuarios</p>} />
        </Route>
        <Route path="/403" element={<p>prohibido</p>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ConfiguracionLayout", () => {
  beforeEach(() => {
    authState = { user: { permissions: [] } };
    companyState = {
      company: { id: 1, short_name: "Laarcourier" },
      can: (capability) => ["configurar", "gestionar_miembros"].includes(capability),
    };
  });

  it("muestra las pestañas de la empresa y del sistema según permisos", () => {
    authState.user.permissions = ["usuarios.ver", "roles.ver", "configuracion.ver"];
    renderAt("/configuracion/empresa");
    const tabs = screen.getByRole("navigation", { name: "Secciones de configuración" });
    for (const label of ["Empresa", "Recordatorios", "Usuarios y roles de la empresa", "Usuarios", "Roles", "Identidad visual"]) {
      expect(tabs).toHaveTextContent(label);
    }
    expect(tabs).not.toHaveTextContent("Auditoría de la empresa");
    expect(tabs).not.toHaveTextContent("Empresas");
    expect(screen.getByText("ventana empresa")).toBeInTheDocument();
  });

  it("cada pestaña es una ventana con su propia ruta", () => {
    authState.user.permissions = ["usuarios.ver"];
    renderAt("/configuracion/usuarios");
    expect(screen.getByText("ventana usuarios")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Usuarios" })).toHaveAttribute("href", "/configuracion/usuarios");
  });

  it("sin empresa abre la primera pestaña del sistema", () => {
    authState.user.permissions = ["usuarios.ver"];
    companyState = { company: null, can: () => false };
    renderAt("/configuracion");
    expect(screen.getByText("ventana usuarios")).toBeInTheDocument();
  });
});
