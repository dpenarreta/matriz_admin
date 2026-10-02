import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../src/components/matriz/AppShell";

let authState;
let companyState;

vi.mock("../src/hooks/useAuth", () => ({ useAuth: () => authState }));
vi.mock("../src/context/CompanyContext", () => ({ useCompany: () => companyState }));
vi.mock("../src/api/matrizService", () => ({
  matrizService: { dashboard: vi.fn(() => Promise.resolve({ counts: { attention: 0 } })) },
}));

const COMPANY = { id: 1, short_name: "Laarcourier", color: "#164b86", role_label: "Administrador" };

function renderShell(path = "/resumen") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell />
    </MemoryRouter>
  );
}

describe("AppShell (interfaz única)", () => {
  beforeEach(() => {
    authState = {
      user: { first_name: "Rodrigo", last_name: "Salcedo", email: "r@x.ec", permissions: [] },
      logout: vi.fn(),
    };
    companyState = { companies: [COMPANY], company: COMPANY, setActiveId: vi.fn(), dataVersion: 0, isLoading: false };
  });

  it("muestra la matriz y oculta la administración sin permisos del sistema", () => {
    renderShell();
    expect(screen.getByText("Matriz de obligaciones")).toBeInTheDocument();
    expect(screen.queryByText("Administración")).not.toBeInTheDocument();
    expect(screen.queryByText("Usuarios")).not.toBeInTheDocument();
  });

  it("agrega solo los módulos de administración que el usuario puede ver", () => {
    authState.user.permissions = ["usuarios.ver", "roles.ver", "auditoria.ver"];
    renderShell();
    expect(screen.getByText("Administración")).toBeInTheDocument();
    expect(screen.getByText("Usuarios")).toBeInTheDocument();
    expect(screen.getByText("Roles")).toBeInTheDocument();
    expect(screen.getByText("Auditoría del sistema")).toBeInTheDocument();
    expect(screen.queryByText("Empresas")).not.toBeInTheDocument();
    expect(screen.queryByText("Identidad visual")).not.toBeInTheDocument();
  });

  it("sin empresa asignada muestra solo la administración, en la misma interfaz", () => {
    authState.user.permissions = ["usuarios.ver"];
    companyState = { ...companyState, companies: [], company: null };
    renderShell("/sistema/usuarios");
    expect(screen.queryByText("Resumen")).not.toBeInTheDocument();
    expect(screen.getAllByText("Usuarios").length).toBeGreaterThan(0);
    expect(screen.getByText("Sin rol en empresas")).toBeInTheDocument();
  });
});
