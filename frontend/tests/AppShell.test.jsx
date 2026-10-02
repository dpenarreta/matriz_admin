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

describe("AppShell (menú lateral)", () => {
  beforeEach(() => {
    authState = {
      user: { first_name: "Rodrigo", last_name: "Salcedo", email: "r@x.ec", permissions: [] },
      logout: vi.fn(),
    };
    companyState = { companies: [COMPANY], company: COMPANY, setActiveId: vi.fn(), dataVersion: 0, isLoading: false };
  });

  it("muestra solo los módulos de la matriz, sin subitems de administración", () => {
    authState.user.permissions = ["usuarios.ver", "roles.ver", "auditoria.ver", "empresas.ver"];
    renderShell();
    const nav = screen.getByRole("navigation", { name: "Menú principal" });
    for (const label of ["Resumen", "Matriz de obligaciones", "Calendario", "Documentos", "Reportes", "Configuración"]) {
      expect(nav).toHaveTextContent(label);
    }
    expect(nav).not.toHaveTextContent("Usuarios");
    expect(nav).not.toHaveTextContent("Roles");
    expect(nav).not.toHaveTextContent("Empresas");
  });

  it("sin empresa, con permisos del sistema, el menú ofrece solo Configuración", () => {
    authState.user.permissions = ["usuarios.ver"];
    companyState = { ...companyState, companies: [], company: null };
    renderShell("/configuracion/usuarios");
    const nav = screen.getByRole("navigation", { name: "Menú principal" });
    expect(nav).toHaveTextContent("Configuración");
    expect(nav).not.toHaveTextContent("Resumen");
    expect(screen.getByText("Sin rol en empresas")).toBeInTheDocument();
  });
});
