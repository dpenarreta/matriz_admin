import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { UserAccessSections } from "../src/pages/Admin/Users/UserAccessSections";

const ROLES = [
  { id: 1, name: "Administrador", permission_codenames: ["matriz.ver_todas", "matriz.configurar"] },
  { id: 2, name: "Responsable", permission_codenames: ["matriz.cargar"] },
];

vi.mock("../src/hooks/usePermission", () => ({
  usePermission: () => true,
}));

vi.mock("../src/hooks/usePermissionsCatalog", () => ({
  usePermissionsCatalog: () => ({ catalog: null, isLoading: false, error: null }),
}));

vi.mock("../src/api/rolesService", () => ({
  rolesService: { list: vi.fn(() => Promise.resolve(ROLES)) },
}));

vi.mock("../src/api/adminUsersService", () => ({
  adminUsersService: {
    get: vi.fn(() =>
      Promise.resolve({ id: 7, is_superuser: false, roles: [{ id: 1, name: "Administrador" }], direct_permissions: [] })
    ),
    assignRoles: vi.fn(() => Promise.resolve()),
    assignPermissions: vi.fn(() => Promise.resolve()),
  },
}));

vi.mock("../src/api/adminMatrizService", () => ({
  adminMatrizService: {
    companies: vi.fn(() =>
      Promise.resolve([
        { id: 10, short_name: "Laarcourier", is_active: true },
        { id: 11, short_name: "Virtual Create", is_active: true },
      ])
    ),
    matrixRoles: vi.fn(() => Promise.resolve(ROLES)),
    catalog: vi.fn(() => Promise.resolve([{ id: 3, code: "TH", name: "Talento Humano" }])),
    userMemberships: vi.fn(() =>
      Promise.resolve([{ company: { id: 10 }, role: { id: 2, name: "Responsable" }, areas: [] }])
    ),
    replaceUserMemberships: vi.fn(() => Promise.resolve([])),
  },
}));

import { adminMatrizService } from "../src/api/adminMatrizService";
import { adminUsersService } from "../src/api/adminUsersService";

describe("UserAccessSections", () => {
  it("muestra y guarda los roles del sistema", async () => {
    render(<UserAccessSections userId="7" />);
    const checkbox = await screen.findByLabelText(/Responsable/, { selector: "#sys-role-2" });
    fireEvent.click(checkbox);
    fireEvent.click(screen.getByText("Guardar roles del sistema"));
    await waitFor(() => expect(adminUsersService.assignRoles).toHaveBeenCalledWith("7", [1, 2]));
  });

  it("muestra el rol por empresa y permite agregar otra empresa", async () => {
    render(<UserAccessSections userId="7" />);
    expect(await screen.findByText("Laarcourier")).toBeInTheDocument();
    // Responsable no tiene matriz.ver_todas: aparece el selector de áreas.
    expect(screen.getByLabelText(/Áreas donde puede crear/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Agregar empresa"), { target: { value: "11" } });
    fireEvent.click(screen.getByText("Guardar roles por empresa"));
    await waitFor(() =>
      expect(adminMatrizService.replaceUserMemberships).toHaveBeenCalledWith("7", [
        { company_id: 10, role_id: 2, area_ids: [] },
        { company_id: 11, role_id: 1, area_ids: [] },
      ])
    );
  });
});
