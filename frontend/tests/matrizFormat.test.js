import { describe, expect, it } from "vitest";

import { daysText, fmtDate, fmtDateTime, toDateInput } from "../src/utils/matrizFormat";

const GYE = "America/Guayaquil";

describe("matrizFormat", () => {
  it("formatea en la zona horaria de la empresa, no en la del navegador", () => {
    // 2 oct. 2026 22:00 UTC = 2 oct. 2026 17:00 en Guayaquil (UTC-5)
    expect(fmtDateTime("2026-10-02T22:00:00Z", GYE)).toBe("2 oct. 2026 · 5:00 p. m.");
    // 3 oct. 2026 03:00 UTC sigue siendo 2 oct. en Guayaquil
    expect(toDateInput("2026-10-03T03:00:00Z", GYE)).toBe("2026-10-02");
  });

  it("formatea fechas sin hora tal cual", () => {
    expect(fmtDate("2026-09-11")).toBe("11 sep. 2026");
  });

  it("texto de la columna Días según el estado", () => {
    expect(daysText({ group: "incumplido", days_overdue: 6 })).toBe("+6 d atraso");
    expect(daysText({ group: "en_progreso", is_due_today: true })).toBe("Vence hoy");
    expect(daysText({ group: "en_progreso", is_due_today: false, days_remaining: 4 })).toBe("4 d restantes");
    expect(daysText({ group: "finalizado", is_late: true, days_overdue: 2 })).toBe("2 d atraso (cerrado)");
    expect(daysText({ group: "finalizado", is_late: false })).toBe("—");
  });
});
