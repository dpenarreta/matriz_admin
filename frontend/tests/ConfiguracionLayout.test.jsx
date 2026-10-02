import { render, screen, within } from "@testing-library/react";
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
          <Route path="empresas" element={<p>ventana empresas</p>} />
          <Route path="usuarios" element={<p>ventana usuarios</p>} />
        </Route>
        <Route path="/403" element={<p>prohibido</p>} />
      </Routes>
    </MemoryRouter>
  );
}

function tabLabels() {
  const nav = screen.getByRole("navigation", { name: "Secciones de configuración" });
  return within(nav)
    .getAllByRole("link")
    .map((link) => link.textContent);
}

const ALL_SYSTEM = [
  "empresas.ver",
  "usuarios.ver",
  "roles.ver",
  "permisos.ver",
  "catalogos.ver",
  "configuracion.ver",
  "auditoria.ver",
];

describe("ConfiguracionLayout", () => {
  beforeEach(() => {
    authState = { user: { permissions: [] } };
    companyState = {
      company: { id: 1, short_name: "Laarcourier" },
      can: () => true,
    };
  });

  it("con todos los permisos muestra una sola pestaña por tema, sin repetidos", () => {
    authState.user.permissions = ALL_SYSTEM;
    renderAt("/configuracion/empresas");
    expect(tabLabels()).toEqual([
      "Empresas",
      "Recordatorios",
      "Usuarios",
      "Roles",
      "Permisos",
      "Catálogos",
      "Identidad visual",
      "Auditoría",
    ]);
  });

  it("el administrador de una empresa (sin permisos del sistema) ve las mismas pestañas unificadas", () => {
    renderAt("/configuracion/empresas");
    expect(tabLabels()).toEqual(["Empresas", "Recordatorios", "Usuarios", "Auditoría"]);
  });

  it("un responsable solo ve Recordatorios", () => {
    companyState.can = () => false;
    renderAt("/configuracion/usuarios");
    expect(tabLabels()).toEqual(["Recordatorios"]);
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
