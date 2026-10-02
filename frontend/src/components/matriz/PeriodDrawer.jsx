import { useCallback, useEffect, useState } from "react";

import { errorMessage, matrizService, saveBlob } from "../../api/matrizService";
import { useCompany } from "../../context/CompanyContext";
import { useToast } from "../../context/ToastContext";
import { fileSize, fmtDate, fmtDateTime } from "../../utils/matrizFormat";
import { Icon } from "../common/Icon/Icon";
import { DueDateModal, EmailPreviewModal, PeriodEditModal, ReasonModal } from "./PeriodModals";
import { Overlay } from "./Overlay";
import { PdfViewerModal } from "./PdfViewerModal";
import { NeutralPill, StatusPill } from "./StatusPill";
import { UploadModal } from "./UploadModal";

const TABS = [
  ["general", "General"],
  ["documentos", "Documentos"],
  ["recordatorios", "Recordatorios"],
  ["historial", "Historial"],
];

function Field({ label, children, full = false }) {
  return (
    <div className={`mz-kv ${full ? "mz-kv--full" : ""}`}>
      <label>{label}</label>
      <div>{children || <span className="mz-faint">—</span>}</div>
    </div>
  );
}

function Person({ person }) {
  if (!person) return <span className="mz-faint">Por asignar</span>;
  return (
    <>
      {person.full_name}
      <br />
      <span className="mz-faint mz-small">{person.email}</span>
    </>
  );
}

/** Panel lateral con el expediente completo de un período (sección 5.5). */
export function PeriodDrawer({ periodId, onClose }) {
  const notify = useToast();
  const { refreshData } = useCompany();
  const [period, setPeriod] = useState(null);
  const [tab, setTab] = useState("general");
  const [error, setError] = useState(null);
  const [modal, setModal] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError(null);
    return matrizService
      .period(periodId)
      .then(setPeriod)
      .catch((err) => setError(errorMessage(err, "No se pudo abrir el período.")));
  }, [periodId]);

  useEffect(() => {
    load();
  }, [load]);

  async function run(action, success, after) {
    setBusy(true);
    try {
      const updated = await action();
      if (updated?.id === periodId) setPeriod(updated);
      else await load();
      notify(...success);
      refreshData();
      after?.();
    } catch (err) {
      notify("Acción no disponible", errorMessage(err), "bad");
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <Overlay variant="drawer" title="Período" onClose={onClose}>
        <div className="mz-alert mz-alert--bad">{error}</div>
      </Overlay>
    );
  }
  if (!period) {
    return (
      <Overlay variant="drawer" title="Cargando…" onClose={onClose}>
        <p className="mz-faint">Cargando el expediente…</p>
      </Overlay>
    );
  }

  const tz = period.company.timezone;
  const actions = period.actions || {};

  return (
    <>
      <Overlay
        variant="drawer"
        wide
        subtitle={`${period.code} · ${period.label}`}
        title={period.obligation.name}
        onClose={onClose}
        header={
          <div className="mz-pill-row">
            <StatusPill status={period.status} />
            {!period.is_closed && period.status.label !== period.stage_label && (
              <NeutralPill>{period.stage_label}</NeutralPill>
            )}
            <NeutralPill>{period.obligation.type_label}</NeutralPill>
            <NeutralPill>{period.company.short_name}</NeutralPill>
          </div>
        }
      >
        <div className="mz-tabs" role="tablist">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              className={tab === key ? "is-active" : ""}
              onClick={() => setTab(key)}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "general" && (
          <GeneralTab
            period={period}
            tz={tz}
            actions={actions}
            busy={busy}
            onEditDue={() => setModal("due")}
            onEdit={() => setModal("edit")}
            onUpload={() => setModal("upload")}
            onSubmit={() =>
              run(() => matrizService.submit(period.id), [
                "Enviado a validación",
                "El supervisor/aprobador ya puede validar el cierre.",
              ])
            }
            onValidate={() =>
              run(() => matrizService.validate(period.id), [
                "Obligación finalizada",
                "Se suspendieron sus recordatorios.",
              ])
            }
            onReturn={() => setModal("return")}
          />
        )}
        {tab === "documentos" && (
          <DocumentsTab period={period} actions={actions} onUpload={() => setModal("upload")} onChanged={load} />
        )}
        {tab === "recordatorios" && <RemindersTab period={period} tz={tz} actions={actions} />}
        {tab === "historial" && <HistoryTab periodId={period.id} tz={tz} />}
      </Overlay>

      {modal === "due" && (
        <DueDateModal
          period={period}
          onClose={() => setModal(null)}
          onSave={(payload) =>
            run(() => matrizService.changeDueDate(period.id, payload), [
              "Fecha actualizada",
              "Se conservó el valor anterior en el historial.",
            ], () => setModal(null))
          }
        />
      )}
      {modal === "edit" && (
        <PeriodEditModal
          period={period}
          onClose={() => setModal(null)}
          onSave={(payload) =>
            run(() => matrizService.updatePeriod(period.id, payload), ["Cambios guardados", ""], () =>
              setModal(null)
            )
          }
        />
      )}
      {modal === "return" && (
        <ReasonModal
          title="Devolver a preparación"
          description="Indique qué falta o qué debe corregirse. El responsable lo verá en el historial."
          confirmLabel="Devolver"
          onClose={() => setModal(null)}
          onConfirm={(reason) =>
            run(() => matrizService.returnToPreparation(period.id, reason), [
              "Período devuelto",
              "Volvió a En preparación.",
            ], () => setModal(null))
          }
        />
      )}
      {modal === "upload" && (
        <UploadModal
          period={period}
          onClose={() => setModal(null)}
          onUploaded={() => {
            setModal(null);
            load();
            refreshData();
          }}
        />
      )}
    </>
  );
}

function GeneralTab({ period, tz, actions, busy, onEditDue, onEdit, onUpload, onSubmit, onValidate, onReturn }) {
  const obligation = period.obligation;
  return (
    <>
      <section className="mz-section">
        <h4>Identificación</h4>
        <div className="mz-kv-grid">
          <Field label="Código">
            <span className="mz-mono">{period.code}</span>
          </Field>
          <Field label="Empresa / sucursal">
            {period.company.short_name}
            {period.branch ? ` — ${period.branch.name}` : ""}
          </Field>
          <Field label="Área responsable">{period.area.name}</Field>
          <Field label="Entidad de control">{period.control_entity.name}</Field>
          <Field label="Tipo">{obligation.type_label}</Field>
          <Field label="Periodicidad">{obligation.periodicity_label}</Field>
          <Field label="Descripción" full>
            {obligation.description}
          </Field>
          <Field label="Fuente / fundamento" full>
            {obligation.legal_basis}
            {obligation.legal_basis_url && (
              <>
                {" "}
                <a href={obligation.legal_basis_url} target="_blank" rel="noreferrer noopener">
                  <Icon name="link-45deg" /> ver documento de referencia
                </a>
              </>
            )}
          </Field>
          <Field label="Evidencia esperada" full>
            {obligation.expected_evidence}
          </Field>
        </div>
      </section>

      <section className="mz-section">
        <h4>Fechas del período</h4>
        <div className="mz-kv-grid">
          <Field label="Período">{period.label}</Field>
          <Field label="Fecha de inicio">{fmtDate(period.start_date)}</Field>
          <Field label="Fecha interna de preparación">{fmtDate(period.preparation_date)}</Field>
          <Field label="Fecha y hora de vencimiento">
            <b>{fmtDateTime(period.due_at, tz)}</b>
            {actions.change_due_date && (
              <button type="button" className="mz-icon-btn mz-inline-btn" onClick={onEditDue} title="Cambiar fecha (requiere justificación)">
                <Icon name="pencil" />
              </button>
            )}
          </Field>
          {period.submitted_at && (
            <Field label="Enviado a validación">
              {fmtDateTime(period.submitted_at, tz)} · {period.submitted_by?.full_name}
            </Field>
          )}
          {period.is_closed && (
            <>
              <Field label="Fecha de cumplimiento">{fmtDateTime(period.completed_at, tz)}</Field>
              <Field label="Fecha de validación">
                {fmtDateTime(period.validated_at, tz)} · {period.validated_by?.full_name}
              </Field>
            </>
          )}
        </div>
      </section>

      <section className="mz-section">
        <h4>Responsables</h4>
        <div className="mz-kv-grid">
          <Field label="Responsable principal">
            <Person person={period.responsible} />
          </Field>
          <Field label="Suplente">
            <Person person={period.backup} />
          </Field>
          <Field label="Supervisor">
            <Person person={period.supervisor} />
          </Field>
          <Field label="Aprobador">
            <Person person={period.approver} />
          </Field>
        </div>
      </section>

      <section className="mz-section">
        <h4>Seguimiento</h4>
        <div className="mz-kv-grid">
          <Field label="Prioridad">
            <span className={`mz-prio mz-prio--${period.priority}`}>{period.priority_label}</span>
          </Field>
          <Field label="Avance">
            {period.progress}%
            <div className="mz-progress">
              <div style={{ width: `${period.progress}%` }} />
            </div>
          </Field>
          <Field label="Observaciones" full>
            {period.notes}
          </Field>
        </div>
      </section>

      <div className="mz-actions">
        {actions.submit && (
          <button type="button" className="btn btn-outline-primary btn-sm" disabled={busy} onClick={onSubmit}>
            <Icon name="send-check" /> Enviar a validación
          </button>
        )}
        {actions.validate && (
          <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={onValidate}>
            <Icon name="check2-circle" /> Validar y finalizar
          </button>
        )}
        {actions.return && (
          <button type="button" className="btn btn-outline-secondary btn-sm" disabled={busy} onClick={onReturn}>
            <Icon name="arrow-counterclockwise" /> Devolver a preparación
          </button>
        )}
        {actions.upload && (
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={onUpload}>
            <Icon name="upload" /> Cargar evidencia
          </button>
        )}
        {actions.edit && (
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={onEdit}>
            <Icon name="pencil-square" /> Editar seguimiento
          </button>
        )}
      </div>
      {period.reminders_suspended && (
        <div className="mz-alert mz-alert--info">
          <Icon name="envelope" /> Los recordatorios de este período están suspendidos porque el cierre ya fue validado.
        </div>
      )}
    </>
  );
}

function DocumentsTab({ period, actions, onUpload, onChanged }) {
  const notify = useToast();
  const { refreshData } = useCompany();
  const [documents, setDocuments] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [rejecting, setRejecting] = useState(null);

  const load = useCallback(() => matrizService.documents(period.id).then(setDocuments), [period.id]);

  useEffect(() => {
    load();
  }, [load, period]);

  async function handle(action, success) {
    try {
      await action();
      notify(...success);
      await load();
      onChanged();
      refreshData();
    } catch (err) {
      notify("Acción no disponible", errorMessage(err), "bad");
    }
  }

  async function download(document) {
    try {
      saveBlob(await matrizService.documentFile(document.id, true));
    } catch (err) {
      notify("No se pudo descargar", errorMessage(err), "bad");
    }
  }

  if (documents === null) return <p className="mz-faint">Cargando documentos…</p>;
  const valid = documents.filter((doc) => doc.status === "valido");

  return (
    <>
      <div className="mz-row-between">
        <h4 className="mz-subtitle">Documentos del período ({documents.length})</h4>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={!actions.upload}
          title={actions.upload ? "" : "Sin permisos para cargar documentos en este período"}
          onClick={onUpload}
        >
          <Icon name="upload" /> Cargar PDF
        </button>
      </div>
      {documents.length === 0 && (
        <div className="mz-empty">
          <Icon name="folder2" />
          <p>
            <b>Sin documentos.</b>
            <br />
            Aún no se ha cargado evidencia para este período.
          </p>
        </div>
      )}
      {documents.map((doc) =>
        doc.status === "rechazado" ? (
          <div key={doc.id} className="mz-doc mz-doc--rejected">
            <div className="mz-doc-ic">
              <Icon name="exclamation-triangle" />
            </div>
            <div className="mz-doc-info">
              <strong>{doc.original_name}</strong>
              <span>
                Cargado por {doc.uploaded_by?.full_name} · {fmtDate(doc.created_at)} · <b>Archivo rechazado</b>
              </span>
              <div className="mz-small mz-bad">{doc.rejection_reason}</div>
            </div>
            {actions.upload && (
              <div className="mz-doc-actions">
                <button
                  type="button"
                  title="Eliminar"
                  aria-label="Eliminar documento rechazado"
                  onClick={() => handle(() => matrizService.deleteDocument(doc.id), ["Documento eliminado", ""])}
                >
                  <Icon name="trash" />
                </button>
              </div>
            )}
          </div>
        ) : (
          <div key={doc.id} className="mz-doc">
            <div className="mz-doc-ic">
              <Icon name="file-earmark-pdf" />
            </div>
            <div className="mz-doc-info">
              <strong>{doc.original_name}</strong>
              <span>
                v{doc.version} · {fileSize(doc.size)} · {fmtDate(doc.created_at)} · cargado por{" "}
                {doc.uploaded_by?.full_name}
              </span>
            </div>
            <div className="mz-doc-actions">
              <button type="button" title="Ver" aria-label="Ver documento" onClick={() => setViewing(doc.id)}>
                <Icon name="eye" />
              </button>
              <button type="button" title="Descargar" aria-label="Descargar documento" onClick={() => download(doc)}>
                <Icon name="download" />
              </button>
              {actions.reject_document && (
                <button type="button" title="Rechazar" aria-label="Rechazar documento" onClick={() => setRejecting(doc)}>
                  <Icon name="x-octagon" />
                </button>
              )}
            </div>
          </div>
        )
      )}
      {!actions.upload && (
        <div className="mz-alert mz-alert--info">
          <Icon name="lock" /> Su rol tiene acceso de solo lectura a los documentos de este período.
        </div>
      )}
      {viewing && <PdfViewerModal documents={valid} initialId={viewing} title={period.obligation.name} onClose={() => setViewing(null)} />}
      {rejecting && (
        <ReasonModal
          title="Rechazar evidencia"
          description={`Indique por qué se rechaza "${rejecting.original_name}".`}
          confirmLabel="Rechazar"
          onClose={() => setRejecting(null)}
          onConfirm={(reason) =>
            handle(() => matrizService.rejectDocument(rejecting.id, reason), ["Evidencia rechazada", ""]).then(() =>
              setRejecting(null)
            )
          }
        />
      )}
    </>
  );
}

const STATE_LABELS = {
  enviado: ["Enviado", "ok"],
  fallido: ["Fallido", "bad"],
  reintentado: ["Reintentado", "neutral"],
  programado: ["Programado", "neutral"],
  no_enviado: ["No enviado", "neutral"],
  suspendido: ["Suspendido", "neutral"],
};

function RemindersTab({ period, tz, actions }) {
  const notify = useToast();
  const [data, setData] = useState(null);
  const [preview, setPreview] = useState(null);

  const load = useCallback(() => matrizService.reminders(period.id).then(setData), [period.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function send() {
    try {
      const sent = await matrizService.sendReminder(period.id);
      notify("Recordatorio enviado", `${sent.length} destinatario(s).`);
      load();
    } catch (err) {
      notify("Sin envío", errorMessage(err), "bad");
    }
  }

  async function retry(notification) {
    try {
      await matrizService.retryNotification(notification.id);
      notify("Reintento enviado", "No se duplicó el aviso original.");
      load();
    } catch (err) {
      notify("No se pudo reintentar", errorMessage(err), "bad");
    }
  }

  if (!data) return <p className="mz-faint">Cargando recordatorios…</p>;

  return (
    <>
      <div className="mz-alert mz-alert--info">
        <Icon name="envelope" /> Los avisos se envían automáticamente por correo al responsable (y a su suplente), y
        al supervisor en caso de atraso, aunque nadie tenga la aplicación abierta.
      </div>
      <section className="mz-section">
        <h4>Avisos de este período</h4>
        {data.suspended && (
          <div className="mz-alert mz-alert--warn">
            <Icon name="clock" /> Suspendidos: el cierre de este período ya fue validado.
          </div>
        )}
        {data.schedule.map((item) => {
          const [label, tone] = STATE_LABELS[item.state] || [item.state, "neutral"];
          return (
            <div key={item.offset_days} className="mz-doc mz-doc--plain">
              <div className="mz-doc-ic mz-doc-ic--info">
                <Icon name="envelope" />
              </div>
              <div className="mz-doc-info">
                <strong>{item.offset_days === 0 ? "El día de vencimiento" : `Aviso ${item.offset_days} día(s) antes`}</strong>
                <span>{fmtDateTime(item.send_at, tz)}</span>
              </div>
              <span className={`mz-pill mz-pill--${tone}`}>{label}</span>
            </div>
          );
        })}
      </section>
      <section className="mz-section">
        <h4>Historial de notificaciones</h4>
        {data.notifications.length === 0 && <p className="mz-faint">Sin notificaciones registradas todavía.</p>}
        {data.notifications.map((notification) => {
          const [, tone] = STATE_LABELS[notification.status] || ["", "neutral"];
          return (
            <div key={notification.id} className="mz-doc mz-doc--plain">
              <div className={`mz-doc-ic mz-doc-ic--${tone}`}>
                <Icon name="envelope" />
              </div>
              <div className="mz-doc-info">
                <strong>{notification.kind_label}</strong>
                <span>
                  Para {notification.recipient_email} · {fmtDateTime(notification.created_at, tz)}
                  {notification.attempts > 1 ? ` · intento ${notification.attempts}` : ""}
                </span>
              </div>
              <span className={`mz-pill mz-pill--${tone}`}>{notification.status_label}</span>
              {notification.status === "fallido" && actions.remind && (
                <button type="button" className="btn btn-outline-secondary btn-sm ms-2" onClick={() => retry(notification)}>
                  Reintentar
                </button>
              )}
            </div>
          );
        })}
      </section>
      <div className="mz-actions">
        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setPreview("recordatorio")}>
          <Icon name="eye" /> Vista previa del correo
        </button>
        {actions.remind && (
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={send}>
            <Icon name="envelope-arrow-up" /> Reenviar recordatorio ahora
          </button>
        )}
      </div>
      {preview && <EmailPreviewModal periodId={period.id} kind={preview} onClose={() => setPreview(null)} />}
    </>
  );
}

function HistoryTab({ periodId, tz }) {
  const [events, setEvents] = useState(null);

  useEffect(() => {
    matrizService.history(periodId).then(setEvents);
  }, [periodId]);

  if (!events) return <p className="mz-faint">Cargando historial…</p>;
  return (
    <section className="mz-section">
      <h4>Historial de cambios</h4>
      <div className="mz-timeline">
        {events.map((event) => (
          <div key={event.id} className="mz-tl-item">
            <div className="mz-tl-when">{fmtDateTime(event.created_at, tz)}</div>
            <div className="mz-tl-what">
              {event.description} — <span className="mz-faint">{event.actor}</span>
            </div>
            {event.reason && <div className="mz-tl-why">Motivo: {event.reason}</div>}
            {event.previous_value && (
              <div className="mz-tl-why">
                Valor anterior: <span className="mz-mono">{event.previous_value}</span> → Nuevo:{" "}
                <span className="mz-mono">{event.new_value}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
