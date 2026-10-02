import { useEffect, useState } from "react";

import { errorMessage, matrizService } from "../../api/matrizService";
import { useCompany } from "../../context/CompanyContext";
import { useAuth } from "../../hooks/useAuth";
import { useToast } from "../../context/ToastContext";
import { Overlay } from "./Overlay";

const EMPTY = {
  name: "",
  description: "",
  branch_id: "",
  area_id: "",
  control_entity_id: "",
  type: "regulatoria",
  legal_basis: "",
  legal_basis_url: "",
  expected_evidence: "",
  periodicity: "anual",
  due_day: "",
  due_month: "",
  label: "",
  start_date: "",
  preparation_date: "",
  due_date: "",
  due_time: "17:00",
  responsible_id: "",
  backup_id: "",
  supervisor_id: "",
  approver_id: "",
  priority: "media",
  notes: "",
};

function toPayload(form) {
  const payload = {};
  Object.entries(form).forEach(([key, value]) => {
    if (value === "" || value === null) {
      if (["legal_basis", "legal_basis_url", "description", "notes"].includes(key)) payload[key] = "";
      return;
    }
    payload[key] = /_id$|^due_day$|^due_month$/.test(key) ? Number(value) : value;
  });
  return payload;
}

/** Alta de una obligación y su primer período (sección 5.6). */
export function ObligationFormModal({ onClose, onCreated }) {
  const { company, refreshData } = useCompany();
  const { user } = useAuth();
  const notify = useToast();
  const [catalogs, setCatalogs] = useState(null);
  const [people, setPeople] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([matrizService.catalogs(company.id), matrizService.people(company.id)]).then(([cat, list]) => {
      setCatalogs(cat);
      setPeople(list);
      setForm((current) => ({
        ...current,
        area_id: cat.areas[0]?.id ?? "",
        control_entity_id: cat.control_entities[0]?.id ?? "",
        branch_id: cat.branches[0]?.id ?? "",
        responsible_id: list.some((p) => p.id === user?.id) ? user.id : "",
      }));
    });
  }, [company.id, user]);

  const set = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  async function save() {
    setSaving(true);
    setErrors({});
    try {
      const period = await matrizService.createObligation(company.id, toPayload(form));
      notify("Obligación creada", `${form.name} — ${period.label}`);
      refreshData();
      onCreated(period);
    } catch (err) {
      setErrors(err.response?.data?.error?.details || {});
      notify("Faltan datos", errorMessage(err), "bad");
    } finally {
      setSaving(false);
    }
  }

  const fieldError = (key) => {
    const value = errors[key];
    return value ? <div className="mz-field-error">{Array.isArray(value) ? value[0] : String(value)}</div> : null;
  };

  const input = (key, label, { full = false, ...props } = {}) => (
    <div className={`mz-field ${full ? "mz-field--full" : ""}`}>
      <label htmlFor={`ob-${key}`}>{label}</label>
      <input id={`ob-${key}`} className="form-control" value={form[key]} onChange={set(key)} {...props} />
      {fieldError(key)}
    </div>
  );

  const select = (key, label, options, { optional = false, full = false } = {}) => (
    <div className={`mz-field ${full ? "mz-field--full" : ""}`}>
      <label htmlFor={`ob-${key}`}>{label}</label>
      <select id={`ob-${key}`} className="form-select" value={form[key]} onChange={set(key)}>
        {optional && <option value="">Por asignar</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {fieldError(key)}
    </div>
  );

  const personOptions = people.map((person) => ({ value: person.id, label: `${person.full_name} · ${person.role_label}` }));
  const recurring = ["mensual", "trimestral", "semestral", "anual"].includes(form.periodicity);

  return (
    <Overlay
      title="Nueva obligación"
      wide
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-outline-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button type="button" className="btn btn-primary" onClick={save} disabled={saving || !catalogs}>
            {saving ? "Guardando…" : "Crear obligación"}
          </button>
        </>
      }
    >
      {!catalogs ? (
        <p className="mz-faint">Cargando catálogos…</p>
      ) : (
        <div className="mz-field-grid">
          {input("name", "Nombre de la obligación", { full: true, placeholder: "Ej. Declaración de IVA", required: true })}
          {input("description", "Descripción", { full: true, placeholder: "Describa brevemente en qué consiste" })}
          {select("branch_id", "Sucursal", catalogs.branches.map((b) => ({ value: b.id, label: b.name })), { optional: true })}
          {select("area_id", "Área responsable", catalogs.areas.map((a) => ({ value: a.id, label: a.name })))}
          {select("control_entity_id", "Entidad de control", catalogs.control_entities.map((e) => ({ value: e.id, label: e.name })))}
          {select("type", "Tipo", catalogs.types)}
          {input("legal_basis", "Fuente / fundamento", { full: true, placeholder: "Norma o contrato" })}
          {input("legal_basis_url", "Enlace de referencia", { type: "url", placeholder: "https://…" })}
          {input("expected_evidence", "Evidencia esperada", { placeholder: "Ej. Formulario 104 y comprobante" })}
          {select("periodicity", "Periodicidad", catalogs.periodicities)}
          {recurring && input("due_day", "Día de vencimiento (siguientes períodos)", { type: "number", min: 1, max: 31 })}
          {form.periodicity === "anual" && input("due_month", "Mes de vencimiento (1–12)", { type: "number", min: 1, max: 12 })}
          {input("label", "Período que corresponde", { placeholder: "Se calcula de la fecha si se deja vacío" })}
          {input("start_date", "Fecha de inicio", { type: "date" })}
          {input("preparation_date", "Fecha interna de preparación", { type: "date" })}
          {input("due_date", "Fecha de vencimiento", { type: "date", required: true })}
          {input("due_time", "Hora de vencimiento", { type: "time" })}
          {select("responsible_id", "Responsable principal", personOptions, { optional: true })}
          {select("backup_id", "Suplente", personOptions, { optional: true })}
          {select("supervisor_id", "Supervisor", personOptions, { optional: true })}
          {select("approver_id", "Aprobador (por defecto, el gerente general)", personOptions, { optional: true })}
          {select("priority", "Prioridad", catalogs.priorities)}
          {input("notes", "Observaciones", { full: true })}
        </div>
      )}
    </Overlay>
  );
}
