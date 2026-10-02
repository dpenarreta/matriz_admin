import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Overlay } from "../src/components/matriz/Overlay";

describe("Overlay", () => {
  it("Escape cierra solo la ventana superior cuando hay dos abiertas", () => {
    const closeDrawer = vi.fn();
    const closeViewer = vi.fn();
    render(
      <>
        <Overlay variant="drawer" title="Período" onClose={closeDrawer}>
          contenido
        </Overlay>
        <Overlay title="Visor" onClose={closeViewer}>
          pdf
        </Overlay>
      </>
    );

    fireEvent.keyDown(document, { key: "Escape" });

    expect(closeViewer).toHaveBeenCalledTimes(1);
    expect(closeDrawer).not.toHaveBeenCalled();
  });

  it("muestra el título y el botón de cerrar", () => {
    const onClose = vi.fn();
    render(
      <Overlay title="Cargar evidencia" onClose={onClose}>
        x
      </Overlay>
    );
    expect(screen.getByRole("dialog", { name: "Cargar evidencia" })).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Cerrar"));
    expect(onClose).toHaveBeenCalled();
  });
});
