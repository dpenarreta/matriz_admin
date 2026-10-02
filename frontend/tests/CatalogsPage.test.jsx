import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CatalogsPage } from "../src/pages/Admin/Catalogos/CatalogsPage";

const AREAS = [{ id: 1, code: "CONT", name: "Contabilidad y Tributario" }];
let permissions = [];

vi.mock("../src/api/adminMatrizService", () => ({
  adminMatrizService: {
    catalog: vi.fn(() => Promise.resolve(AREAS)),
    createCatalogItem: vi.fn(() => Promise.resolve({ id: 2, code: "CAL", name: "Calidad" })),
    updateCatalogItem: vi.fn(),
    deleteCatalogItem: vi.fn(),
  },
}));

vi.mock("../src/hooks/usePermission", () => ({
  usePermission: (codename) => permissions.includes(codename),
}));

import { adminMatrizService } from "../src/api/adminMatrizService";

function renderPage() {
  return render(
    <MemoryRouter>
      <CatalogsPage />
    </MemoryRouter>
  );
}

describe("CatalogsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    permissions = [];
  });

  it("lista las áreas en solo lectura sin catalogos.editar", async () => {
    renderPage();
    expect(await screen.findByText("Contabilidad y Tributario")).toBeInTheDocument();
    expect(screen.queryByText("Agregar")).not.toBeInTheDocument();
    expect(screen.queryByText("Eliminar")).not.toBeInTheDocument();
  });

  it("permite agregar con catalogos.editar", async () => {
    permissions = ["catalogos.editar"];
    renderPage();
    await screen.findByText("Contabilidad y Tributario");
    fireEvent.change(screen.getAllByLabelText("Código")[0], { target: { value: "cal" } });
    fireEvent.change(screen.getAllByLabelText("Nombre")[0], { target: { value: "Calidad" } });
    fireEvent.click(screen.getByText("Agregar"));
    await waitFor(() =>
      expect(adminMatrizService.createCatalogItem).toHaveBeenCalledWith("areas", { code: "cal", name: "Calidad" })
    );
  });

  it("cambia a entidades de control", async () => {
    renderPage();
    await screen.findByText("Contabilidad y Tributario");
    fireEvent.click(screen.getByRole("button", { name: "Entidades de control" }));
    await waitFor(() => expect(adminMatrizService.catalog).toHaveBeenCalledWith("control-entities"));
  });
});
