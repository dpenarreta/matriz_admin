const MONTHS = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

/** Partes de fecha y hora en la zona horaria indicada (la de la empresa). */
function parts(value, timeZone) {
  const date = value instanceof Date ? value : new Date(value);
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const map = Object.fromEntries(formatter.formatToParts(date).map((p) => [p.type, p.value]));
  return {
    year: Number(map.year),
    month: Number(map.month),
    day: Number(map.day),
    hour: Number(map.hour) % 24,
    minute: Number(map.minute),
  };
}

/** "2 oct. 2026" */
export function fmtDate(value, timeZone) {
  if (!value) return "—";
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return `${day} ${MONTHS[month - 1].slice(0, 3)}. ${year}`;
  }
  const p = parts(value, timeZone);
  return `${p.day} ${MONTHS[p.month - 1].slice(0, 3)}. ${p.year}`;
}

/** "5:00 p. m." */
export function fmtTime(value, timeZone) {
  if (!value) return "";
  const p = parts(value, timeZone);
  const suffix = p.hour >= 12 ? "p. m." : "a. m.";
  const h12 = p.hour % 12 || 12;
  return `${h12}:${String(p.minute).padStart(2, "0")} ${suffix}`;
}

export function fmtDateTime(value, timeZone) {
  if (!value) return "—";
  return `${fmtDate(value, timeZone)} · ${fmtTime(value, timeZone)}`;
}

/** "AAAA-MM-DD" y "HH:MM" en la zona indicada, para inputs. */
export function toDateInput(value, timeZone) {
  const p = parts(value, timeZone);
  return `${p.year}-${String(p.month).padStart(2, "0")}-${String(p.day).padStart(2, "0")}`;
}

export function toTimeInput(value, timeZone) {
  const p = parts(value, timeZone);
  return `${String(p.hour).padStart(2, "0")}:${String(p.minute).padStart(2, "0")}`;
}

export function monthName(index) {
  return MONTHS[index];
}

export function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

export function fileSize(bytes) {
  if (bytes == null) return "";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Texto de la columna "Días" de la matriz. */
export function daysText(status) {
  if (!status) return "";
  if (status.group === "incumplido") return `+${status.days_overdue} d atraso`;
  if (status.group === "finalizado") {
    return status.is_late ? `${status.days_overdue} d atraso (cerrado)` : "—";
  }
  if (status.is_due_today) return "Vence hoy";
  return `${status.days_remaining} d restantes`;
}

export const STATUS_TONE = {
  incumplido: "bad",
  en_progreso: "warn",
  finalizado: "ok",
};
