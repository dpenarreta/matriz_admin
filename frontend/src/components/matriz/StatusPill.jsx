import { STATUS_TONE } from "../../utils/matrizFormat";
import { Icon } from "../common/Icon/Icon";

const ICONS = { bad: "exclamation-triangle-fill", warn: "clock-fill", ok: "check-circle-fill" };

/** Etiqueta de estado con su color: rojo incumplido, tomate en progreso, verde finalizado. */
export function StatusPill({ status }) {
  if (!status) return null;
  const tone = STATUS_TONE[status.group] || "neutral";
  return (
    <span className={`mz-pill mz-pill--${tone}`}>
      <Icon name={ICONS[tone]} />
      {status.label}
    </span>
  );
}

export function NeutralPill({ children }) {
  return <span className="mz-pill mz-pill--neutral">{children}</span>;
}
