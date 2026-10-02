import { useEffect, useState } from "react";

import { matrizService } from "../../api/matrizService";
import { fmtDateTime, toDateInput, toTimeInput } from "../../utils/matrizFormat";
import { Icon } from "../common/Icon/Icon";
import { Overlay } from "./Overlay";

const MIN_REASON = 10;

function Footer({ onClose, onConfirm, confirmLabel, disabled }) {
  return (
    <>
      <button type="button" className="btn btn-outline-secondary" onClick={onClose}>
        Cancelar
      </button>
      <button type="button" className="btn btn-primary" onClick={onConfirm} disabled={disabled}>
        {confirmLabel}
      </button>
    </>
  );
}

/** Cambio de fecha de vencimiento con justificación obligatoria (5.7). */
export function DueDateModal({ period, onClose, onSave }) {
  const tz = period.company.timezone;
  const [date, setDate] = useState(toDateInput(period.due_at, tz));
  const [time, setTime] = useState(toTimeInput(period.due_at, tz));
  const [reason, setReason] = useState("");
  const valid = date && reason.trim().length >= MIN_REASON;

  return (
    <Overlay
      title="Cambiar fecha de vencimiento"
      onClose={onClose}
      footer={
        <Footer
          onClose={onClose}
          confirmLabel="Guardar cambio"
          disabled={!valid}
          onConfirm={() => onSave({ due_date: date, due_time: time, reason: reason.trim() })}
        />
      }
    >
      <div className="mz-alert mz-alert--warn">
        <Icon name="exclamation-triangle" /> Este cambio queda registrado en el historial junto con la fecha anterior
        y no puede eliminarse.
      </div>
      <div className="mz-field">
        <label htmlFor="due-current">Fecha y hora actual de vencimiento</label>
        <input id="due-current" className="form-control" disabled value={fmtDateTime(period.due_at, tz)} />
      </div>
      <div className="mz-field-grid">
        <div className="mz-field">
          <label htmlFor="due-date">Nueva fecha</label>
          <input id="due-date" type="date" className="form-control" value={date} min={period.start_date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="mz-field">
          <label htmlFor="due-time">Nueva hora</label>
          <input id="due-time" type="time" className="form-control" value={time} onChange={(e) => setTime(e.target.value)} />
        </div>
      </div>
      <div className="mz-field">
        <label htmlFor="due-reason">Justificación (obligatoria, mínimo {MIN_REASON} caracteres)</label>
        <textarea
          id="due-reason"
          className="form-control"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Explique el motivo del cambio de fecha…"
        />
      </div>
    </Overlay>
  );
}

/** Motivo obligatorio para devolver un período o rechazar una evidencia. */
export function ReasonModal({ title, description, confirmLabel, onClose, onConfirm }) {
  const [reason, setReason] = useState("");
  return (
    <Overlay
      title={title}
      onClose={onClose}
      footer={
        <Footer
          onClose={onClose}
          confirmLabel={confirmLabel}
          disabled={reason.trim().length < MIN_REASON}
          onConfirm={() => onConfirm(reason.trim())}
        />
      }
    >
      <p className="mz-faint">{description}</p>
      <div className="mz-field">
        <label htmlFor="reason">Motivo (mínimo {MIN_REASON} caracteres)</label>
        <textarea id="reason" className="form-control" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
      </div>
    </Overlay>
  );
}

function PersonSelect({ id, label, people, value, onChange, required = false }) {
  return (
    <div className="mz-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} className="form-select" value={value ?? ""} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
        {!required && <option value="">Por asignar</option>}
        {people.map((person) => (
          <option key={person.id} value={person.id}>
            {person.full_name} · {person.role_label}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Edición de responsables, prioridad, avance y observaciones del período. */
export function PeriodEditModal({ period, onClose, onSave }) {
  const [people, setPeople] = useState([]);
  const [form, setForm] = useState({
    responsible_id: period.responsible?.id,
    backup_id: period.backup?.id ?? null,
    supervisor_id: period.supervisor?.id ?? null,
    approver_id: period.approver?.id ?? null,
    priority: period.priority,
    progress: period.progress,
    notes: period.notes,
  });

  useEffect(() => {
    matrizService.people(period.company.id).then(setPeople);
  }, [period.company.id]);

  const set = (key) => (value) => setForm((current) => ({ ...current, [key]: value }));

  return (
    <Overlay
      title="Editar seguimiento del período"
      wide
      onClose={onClose}
      footer={<Footer onClose={onClose} confirmLabel="Guardar cambios" onConfirm={() => onSave(form)} />}
    >
      <div className="mz-field-grid">
        <PersonSelect id="ed-resp" label="Responsable principal" people={people} value={form.responsible_id} onChange={set("responsible_id")} required />
        <PersonSelect id="ed-backup" label="Suplente" people={people} value={form.backup_id} onChange={set("backup_id")} />
        <PersonSelect id="ed-sup" label="Supervisor" people={people} value={form.supervisor_id} onChange={set("supervisor_id")} />
        <PersonSelect id="ed-apr" label="Aprobador" people={people} value={form.approver_id} onChange={set("approver_id")} />
        <div className="mz-field">
          <label htmlFor="ed-prio">Prioridad</label>
          <select id="ed-prio" className="form-select" value={form.priority} onChange={(e) => set("priority")(e.target.value)}>
            <option value="alta">Alta</option>
            <option value="media">Media</option>
            <option value="baja">Baja</option>
          </select>
        </div>
        <div className="mz-field">
          <label htmlFor="ed-progress">Avance: {form.progress}%</label>
          <input id="ed-progress" type="range" min={0} max={100} step={5} className="form-range" value={form.progress} onChange={(e) => set("progress")(Number(e.target.value))} />
        </div>
        <div className="mz-field mz-field--full">
          <label htmlFor="ed-notes">Observaciones</label>
          <textarea id="ed-notes" className="form-control" rows={3} value={form.notes} onChange={(e) => set("notes")(e.target.value)} />
        </div>
      </div>
    </Overlay>
  );
}

/** Vista previa del correo tal como lo envía el servidor (5.10). */
export function EmailPreviewModal({ periodId, kind, onClose }) {
  const [message, setMessage] = useState(null);

  useEffect(() => {
    matrizService.previewReminder(periodId, kind).then(setMessage);
  }, [periodId, kind]);

  return (
    <Overlay title="Vista previa del correo" wide onClose={onClose}>
      {!message ? (
        <p className="mz-faint">Generando vista previa…</p>
      ) : (
        <>
          <p className="mb-1">
            Para: <b>{message.to}</b>
          </p>
          <p>Asunto: {message.subject}</p>
          <iframe title="Vista previa del correo" className="mz-email-frame" sandbox="" srcDoc={message.html} />
        </>
      )}
    </Overlay>
  );
}
