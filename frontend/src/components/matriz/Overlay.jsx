import { useEffect, useId, useRef } from "react";

import { useModalA11y } from "../../hooks/useModalA11y";
import { Icon } from "../common/Icon/Icon";

/**
 * Ventana modal centrada (`variant="modal"`) o panel lateral derecho
 * (`variant="drawer"`), con la accesibilidad del template base: foco
 * atrapado, Escape y clic fuera para cerrar.
 */
// Pila de ventanas abiertas: Escape cierra solo la de arriba (p. ej. el
// visor PDF abierto sobre el panel del período), no todas a la vez.
const openStack = [];

export function Overlay({ title, subtitle, onClose, variant = "modal", wide = false, footer, children, header }) {
  const id = useId();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const { panelRef, handleBackdropClick, requestClose } = useModalA11y({
    isOpen: true,
    onRequestClose: onClose,
    closeOnEscape: false,
  });

  useEffect(() => {
    openStack.push(id);
    function handleKeyDown(event) {
      if (event.key === "Escape" && openStack[openStack.length - 1] === id) {
        event.stopPropagation();
        onCloseRef.current();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      openStack.splice(openStack.indexOf(id), 1);
    };
  }, [id]);

  return (
    <div className={`mz-overlay ${variant === "modal" ? "mz-overlay--center" : ""}`}>
      <div className="mz-backdrop" onClick={handleBackdropClick} aria-hidden="true" />
      <div
        ref={panelRef}
        className={`mz-${variant} ${wide ? "mz-modal--wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        tabIndex={-1}
      >
        <div className="mz-panel-head">
          <div>
            {subtitle && <div className="mz-code">{subtitle}</div>}
            <h3>{title}</h3>
            {header}
          </div>
          <button type="button" className="mz-close" onClick={() => requestClose()} aria-label="Cerrar">
            <Icon name="x-lg" />
          </button>
        </div>
        <div className="mz-panel-body">{children}</div>
        {footer && <div className="mz-panel-foot">{footer}</div>}
      </div>
    </div>
  );
}
