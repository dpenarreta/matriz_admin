import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusPill } from "../src/components/matriz/StatusPill";

describe("StatusPill", () => {
  it.each([
    ["incumplido", "Incumplido", "mz-pill--bad"],
    ["en_progreso", "Vence hoy", "mz-pill--warn"],
    ["finalizado", "Finalizada fuera de plazo", "mz-pill--ok"],
  ])("estado %s se muestra con su color", (group, label, className) => {
    render(<StatusPill status={{ group, label }} />);
    expect(screen.getByText(label)).toHaveClass(className);
  });
});
