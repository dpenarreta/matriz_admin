import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResumenPage } from "../src/pages/Matriz/ResumenPage";

const STATUS = {
  group: "incumplido",
  label: "Incumplido",
  stage: "en_preparacion",
  is_due_today: false,
  is_late: false,
  days_overdue: 3,
  days_remaining: null,
};

const DASHBOARD = {
  counts: { overdue: 2, in_progress: 13, due_soon: 2, done: 7, done_on_time: 3, done_late: 4, attention: 2 },
  upcoming: [
    {
      id: 10,
      code: "OBL-0010",
      label: "Septiembre 2026",
      obligation_name: "Aportes al IESS (personal y patronal)",
      responsible: { id: 1, full_name: "Priscila Maldonado" },
      due_at: "2026-09-26T22:00:00Z",
      status: STATUS,
    },
  ],
  recent_closures: [],
};

let capabilities = [];

vi.mock("../src/api/matrizService", () => ({
  matrizService: { dashboard: vi.fn(() => Promise.resolve(DASHBOARD)) },
}));

vi.mock("../src/context/CompanyContext", () => ({
  useCompany: () => ({
    company: {
      id: 1,
      short_name: "Laarcourier",
      activity: "Mensajería",
      country: "Ecuador",
      timezone: "America/Guayaquil",
    },
    can: (capability) => capabilities.includes(capability),
    dataVersion: 0,
  }),
}));

vi.mock("../src/components/matriz/AppShell", () => ({
  useShell: () => ({ openPeriod: vi.fn(), openNewObligation: vi.fn() }),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <ResumenPage />
    </MemoryRouter>
  );
}

describe("ResumenPage", () => {
  beforeEach(() => {
    capabilities = [];
  });

  it("muestra los indicadores y los próximos vencimientos", async () => {
    renderPage();
    expect(await screen.findByText("Aportes al IESS (personal y patronal)")).toBeInTheDocument();
    expect(screen.getByText("13")).toBeInTheDocument();
    expect(screen.getByText("3 a tiempo · 4 fuera de plazo")).toBeInTheDocument();
    expect(screen.getByText("Incumplido")).toBeInTheDocument();
  });

  it("oculta 'Nueva obligación' sin la capacidad crear", async () => {
    renderPage();
    await screen.findByText("Aportes al IESS (personal y patronal)");
    expect(screen.queryByText(/Nueva obligación/)).not.toBeInTheDocument();
  });

  it("muestra 'Nueva obligación' con la capacidad crear", async () => {
    capabilities = ["crear"];
    renderPage();
    expect(await screen.findByText(/Nueva obligación/)).toBeInTheDocument();
  });
});
