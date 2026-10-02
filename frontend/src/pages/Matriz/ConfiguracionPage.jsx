import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { errorMessage, matrizService } from "../../api/matrizService";
import { Icon } from "../../components/common/Icon/Icon";
import { useCompany } from "../../context/CompanyContext";
import { useToast } from "../../context/ToastContext";
import { useAuth } from "../../hooks/useAuth";
import { fmtDateTime } from "../../utils/matrizFormat";

const TIMEZONES = [
  "America/Guayaquil",
  "America/Bogota",
  "America/Lima",
  "America/Mexico_City",
  "America/Santiago",
  "America/Panama",
];

export function ConfiguracionPage() {
  const { can } = useCompany();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabs = [
    ["empresa", "Empresa", true],
    ["recordatorios", "Recordatorios", true],
    ["miembros", "Usuarios y roles", can("gestionar_miembros")],
    ["auditoria", "Auditoría", can("ver_auditoria")],
  ].filter(([, , visible]) => visible);
  const tab = tabs.some(([key]) => key === searchParams.get("tab")) ? searchParams.get("tab") : "empresa";

  return (
    <>
      <div className="mz-view-head">
        <div>
          <h2>Configuración</h2>
          <p className="mz-desc">Parámetros del tablero, recordatorios automáticos, roles por empresa y trazabilidad.</p>
        </div>
      </div>
      <div className="mz-tabs" role="tablist">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={tab === key ? "is-active" : ""}
            onClick={() => setSearchParams({ tab: key })}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "empresa" && <CompanyTab />}
      {tab === "recordatorios" && <RemindersConfigTab />}
      {tab === "miembros" && <MembersTab />}
      {tab === "auditoria" && <AuditTab />}
    </>
  );
}

function LockedNote({ locked, text }) {
  if (!locked) return null;
  return (
    <div className="mz-alert mz-alert--info">
      <Icon name="lock" /> {text}
    </div>
  );
}

function CompanyTab() {
  const { company, can, reload } = useCompany();
  const notify = useToast();
  const locked = !can("configurar");
  const [form, setForm] = useState(null);
  const [people, setPeople] = useState([]);

  useEffect(() => {
    matrizService.company(company.id).then((data) =>
      setForm({
        legal_name: data.legal_name,
        short_name: data.short_name,
        country: data.country,
        activity: data.activity,
        timezone: data.timezone,
        color: data.color,
        compliance_date_basis: data.compliance_date_basis,
        general_manager_id: data.general_manager?.id ?? null,
      })
    );
    matrizService.people(company.id).then(setPeople);
  }, [company.id]);

  async function save() {
    try {
      await matrizService.updateCompany(company.id, form);
      notify("Configuración guardada", "Los cambios se aplicaron a este tablero.");
      reload();
    } catch (err) {
      notify("No se pudo guardar", errorMessage(err), "bad");
    }
  }

  if (!form) return <p className="mz-faint">Cargando…</p>;
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  return (
    <div className="mz-card">
      <div className="mz-card-body">
        <LockedNote locked={locked} text={`Su rol (${company.role_label}) puede consultar esta configuración; modificarla requiere el permiso matriz.configurar.`} />
        <fieldset disabled={locked} className="mz-field-grid">
          <div className="mz-field">
            <label htmlFor="cf-legal">Razón social</label>
            <input id="cf-legal" className="form-control" value={form.legal_name} onChange={set("legal_name")} />
          </div>
          <div className="mz-field">
            <label htmlFor="cf-short">Nombre corto</label>
            <input id="cf-short" className="form-control" value={form.short_name} onChange={set("short_name")} />
          </div>
          <div className="mz-field">
            <label htmlFor="cf-country">País</label>
            <input id="cf-country" className="form-control" value={form.country} onChange={set("country")} />
          </div>
          <div className="mz-field">
            <label htmlFor="cf-tz">Zona horaria</label>
            <select id="cf-tz" className="form-select" value={form.timezone} onChange={set("timezone")}>
              {[...new Set([form.timezone, ...TIMEZONES])].map((tz) => (
                <option key={tz}>{tz}</option>
              ))}
            </select>
          </div>
          <div className="mz-field mz-field--full">
            <label htmlFor="cf-activity">Actividad económica</label>
            <input id="cf-activity" className="form-control" value={form.activity} onChange={set("activity")} />
          </div>
          <div className="mz-field">
            <label htmlFor="cf-gm">Gerente general (aprobador por defecto)</label>
            <select
              id="cf-gm"
              className="form-select"
              value={form.general_manager_id ?? ""}
              onChange={(e) => setForm({ ...form, general_manager_id: e.target.value ? Number(e.target.value) : null })}
            >
              <option value="">Sin asignar</option>
              {people.map((person) => (
                <option key={person.id} value={person.id}>
                  {person.full_name}
                </option>
              ))}
            </select>
          </div>
          <div className="mz-field">
            <label htmlFor="cf-basis">Fecha que cuenta como cumplimiento</label>
            <select id="cf-basis" className="form-select" value={form.compliance_date_basis} onChange={set("compliance_date_basis")}>
              <option value="validation">La fecha de validación del cierre</option>
              <option value="submission">La fecha de envío a validación</option>
            </select>
          </div>
          <div className="mz-field">
            <label htmlFor="cf-color">Color institucional</label>
            <input id="cf-color" type="color" className="form-control form-control-color" value={form.color} onChange={set("color")} />
          </div>
        </fieldset>
        {!locked && (
          <button type="button" className="btn btn-primary btn-sm mt-2" onClick={save}>
            Guardar cambios
          </button>
        )}
      </div>
    </div>
  );
}

function RemindersConfigTab() {
  const { company, can } = useCompany();
  const notify = useToast();
  const locked = !can("configurar");
  const [config, setConfig] = useState(null);
  const [newOffset, setNewOffset] = useState("");
  const [notifications, setNotifications] = useState(null);

  const loadNotifications = useCallback(() => {
    if (can("ver_auditoria")) matrizService.notifications(company.id, { page_size: 25 }).then(setNotifications);
  }, [company.id, can]);

  useEffect(() => {
    matrizService.reminderConfig(company.id).then(setConfig);
    loadNotifications();
  }, [company.id, loadNotifications]);

  async function save() {
    try {
      setConfig(await matrizService.updateReminderConfig(company.id, config));
      notify("Recordatorios actualizados", "Los nuevos plazos aplican a partir del próximo ciclo.");
    } catch (err) {
      notify("No se pudo guardar", errorMessage(err), "bad");
    }
  }

  async function retry(notification) {
    try {
      await matrizService.retryNotification(notification.id);
      notify("Reintento enviado", "No se duplicó el aviso original.");
      loadNotifications();
    } catch (err) {
      notify("No se pudo reintentar", errorMessage(err), "bad");
    }
  }

  if (!config) return <p className="mz-faint">Cargando…</p>;
  const offsets = [...new Set([...config.offsets, 0])].sort((a, b) => b - a);

  function addOffset() {
    const value = Number(newOffset);
    if (!Number.isInteger(value) || value < 1 || value > 90 || offsets.includes(value)) {
      notify("Anticipación inválida", "Use un número entero entre 1 y 90 que no esté repetido.", "bad");
      return;
    }
    setConfig({ ...config, offsets: [...offsets, value] });
    setNewOffset("");
  }

  return (
    <>
      <div className="mz-card">
        <div className="mz-card-head">
          <h3>Anticipación de los avisos</h3>
        </div>
        <div className="mz-card-body">
          <LockedNote locked={locked} text="Editar estos parámetros requiere el permiso matriz.configurar." />
          {offsets.map((offset) => (
            <div key={offset} className="mz-reminder-row">
              <Icon name="envelope" />
              <span className="flex-grow-1">{offset === 0 ? "El día del vencimiento" : `${offset} día(s) antes`}</span>
              {!locked && offset !== 0 && (
                <button
                  type="button"
                  className="mz-icon-btn"
                  aria-label={`Quitar aviso de ${offset} días`}
                  onClick={() => setConfig({ ...config, offsets: offsets.filter((item) => item !== offset) })}
                >
                  <Icon name="trash" />
                </button>
              )}
            </div>
          ))}
          {!locked && (
            <div className="mz-inline-add">
              <input
                type="number"
                min={1}
                max={90}
                className="form-control form-control-sm"
                placeholder="Días"
                value={newOffset}
                onChange={(e) => setNewOffset(e.target.value)}
                aria-label="Nueva anticipación en días"
              />
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={addOffset}>
                <Icon name="plus-lg" /> Añadir anticipación
              </button>
            </div>
          )}
          <fieldset disabled={locked} className="mz-field-grid mt-3">
            <div className="mz-field">
              <label htmlFor="rc-time">Hora de envío (hora local de la empresa)</label>
              <input id="rc-time" type="time" className="form-control" value={config.send_time.slice(0, 5)} onChange={(e) => setConfig({ ...config, send_time: e.target.value })} />
            </div>
            <div className="mz-field mz-switch-field">
              <input id="rc-backup" type="checkbox" className="form-check-input" checked={config.copy_backup} onChange={(e) => setConfig({ ...config, copy_backup: e.target.checked })} />
              <label htmlFor="rc-backup">Enviar copia al suplente</label>
            </div>
            <div className="mz-field mz-switch-field">
              <input id="rc-esc" type="checkbox" className="form-check-input" checked={config.escalation_enabled} onChange={(e) => setConfig({ ...config, escalation_enabled: e.target.checked })} />
              <label htmlFor="rc-esc">Escalar al supervisor si vence sin finalizar</label>
            </div>
            <div className="mz-field">
              <label htmlFor="rc-days">Días de atraso antes de escalar (1–30)</label>
              <input id="rc-days" type="number" min={1} max={30} className="form-control" value={config.escalation_days} onChange={(e) => setConfig({ ...config, escalation_days: Number(e.target.value) })} />
            </div>
            <div className="mz-field">
              <label htmlFor="rc-repeat">Repetir el escalamiento cada N días (0 = una sola vez)</label>
              <input id="rc-repeat" type="number" min={0} max={30} className="form-control" value={config.escalation_repeat_days} onChange={(e) => setConfig({ ...config, escalation_repeat_days: Number(e.target.value) })} />
            </div>
          </fieldset>
          {!locked && (
            <button type="button" className="btn btn-primary btn-sm mt-2" onClick={save}>
              Guardar configuración de recordatorios
            </button>
          )}
        </div>
      </div>
      {notifications && (
        <div className="mz-card mt-3">
          <div className="mz-card-head">
            <h3>Historial de notificaciones ({notifications.count})</h3>
          </div>
          {notifications.results.length === 0 && <div className="mz-empty">Sin notificaciones registradas.</div>}
          {notifications.results.map((notification) => (
            <div key={notification.id} className="mz-doc mz-doc--plain mz-doc--flush">
              <div className={`mz-doc-ic mz-doc-ic--${notification.status === "fallido" ? "bad" : "ok"}`}>
                <Icon name="envelope" />
              </div>
              <div className="mz-doc-info">
                <strong>
                  {notification.obligation_name} · {notification.period_code}
                </strong>
                <span>
                  {notification.kind_label} · para {notification.recipient_email} · {fmtDateTime(notification.created_at, company.timezone)}
                </span>
              </div>
              <span className={`mz-pill mz-pill--${notification.status === "fallido" ? "bad" : notification.status === "enviado" ? "ok" : "neutral"}`}>
                {notification.status_label}
              </span>
              {notification.status === "fallido" && (
                <button type="button" className="btn btn-outline-secondary btn-sm ms-2" onClick={() => retry(notification)}>
                  Reintentar
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function MembersTab() {
  const { company, reload } = useCompany();
  const { user } = useAuth();
  const notify = useToast();
  const [members, setMembers] = useState(null);
  const [roles, setRoles] = useState([]);
  const [form, setForm] = useState({ identifier: "", role_id: "" });

  const load = useCallback(() => matrizService.members(company.id).then(setMembers), [company.id]);

  useEffect(() => {
    load();
    matrizService.roles(company.id).then((list) => {
      setRoles(list);
      setForm((current) => ({ ...current, role_id: current.role_id || list[0]?.id || "" }));
    });
  }, [load, company.id]);

  async function act(action, message) {
    try {
      await action();
      notify(message, "");
      load();
      reload();
    } catch (err) {
      notify("No se pudo completar", errorMessage(err), "bad");
    }
  }

  if (!members) return <p className="mz-faint">Cargando…</p>;
  const canEditRoles = user?.permissions?.includes("roles.editar");

  const roleSelect = (value, onChange, label) => (
    <select
      className="form-select form-select-sm mz-role-select"
      value={value}
      aria-label={label}
      onChange={(e) => onChange(Number(e.target.value))}
    >
      {roles.map((role) => (
        <option key={role.id} value={role.id}>
          {role.name}
        </option>
      ))}
    </select>
  );

  return (
    <div className="mz-card">
      <div className="mz-card-head">
        <h3>Usuarios con rol en {company.short_name}</h3>
      </div>
      <div className="mz-card-body">
        <div className="mz-inline-add mb-3">
          <input
            className="form-control form-control-sm"
            placeholder="Usuario o correo de una cuenta existente"
            value={form.identifier}
            onChange={(e) => setForm({ ...form, identifier: e.target.value })}
            aria-label="Usuario o correo"
          />
          {roleSelect(form.role_id, (roleId) => setForm({ ...form, role_id: roleId }), "Rol")}
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={!form.identifier.trim() || !form.role_id}
            onClick={() =>
              act(() => matrizService.addMember(company.id, form), "Usuario agregado").then(() =>
                setForm({ ...form, identifier: "" })
              )
            }
          >
            <Icon name="person-plus" /> Agregar
          </button>
        </div>
        <p className="mz-faint mz-small">
          Las cuentas se crean en Administración del sistema → Usuarios. Aquí se asigna su rol en esta empresa. Los roles
          y sus permisos se configuran en Administración del sistema → Roles.
        </p>
        {members.map((member) => (
          <div key={member.id} className="mz-doc mz-doc--plain">
            <div className="mz-avatar mz-avatar--sm">{member.user.full_name.slice(0, 2).toUpperCase()}</div>
            <div className="mz-doc-info">
              <strong>{member.user.full_name}</strong>
              <span>
                {member.user.email}
                {member.areas.length ? ` · Áreas: ${member.areas.map((area) => area.code).join(", ")}` : ""}
              </span>
            </div>
            {roleSelect(
              member.role.id,
              (roleId) => act(() => matrizService.updateMember(company.id, member.id, { role_id: roleId }), "Rol actualizado"),
              `Rol de ${member.user.full_name}`
            )}
            <button
              type="button"
              className="mz-icon-btn ms-2"
              aria-label={`Quitar a ${member.user.full_name} de la empresa`}
              onClick={() => act(() => matrizService.removeMember(company.id, member.id), "Usuario quitado de la empresa")}
            >
              <Icon name="person-dash" />
            </button>
          </div>
        ))}
        <PermissionMatrix roles={roles} />
        {canEditRoles && (
          <Link to="/admin/roles" className="btn btn-outline-secondary btn-sm mt-2">
            <Icon name="shield-lock" /> Configurar roles y permisos
          </Link>
        )}
      </div>
    </div>
  );
}

const MATRIX_PERMISSIONS = [
  ["matriz.ver_todas", "Ver todas las obligaciones (sin esto, solo las propias)"],
  ["matriz.crear", "Crear obligaciones"],
  ["matriz.editar", "Editar el seguimiento"],
  ["matriz.cambiar_fecha", "Cambiar la fecha de vencimiento"],
  ["matriz.cargar", "Cargar evidencia"],
  ["matriz.enviar", "Enviar a validación"],
  ["matriz.validar", "Validar, devolver y rechazar evidencia"],
  ["matriz.recordar", "Reenviar recordatorios"],
  ["matriz.exportar", "Exportar"],
  ["matriz.ver_auditoria", "Ver auditoría"],
  ["matriz.configurar", "Configurar la empresa y los recordatorios"],
  ["matriz.gestionar_miembros", "Gestionar usuarios y roles de la empresa"],
];

/** Tabla de permisos de los roles actuales, leída del backend (no fija). */
function PermissionMatrix({ roles }) {
  if (!roles.length) return null;
  return (
    <div className="table-responsive mt-3">
      <table className="mz-perm-table">
        <thead>
          <tr>
            <th>Permiso</th>
            {roles.map((role) => (
              <th key={role.id}>{role.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MATRIX_PERMISSIONS.map(([codename, label]) => (
            <tr key={codename}>
              <td>{label}</td>
              {roles.map((role) => {
                const has = role.permission_codenames.includes(codename);
                return (
                  <td key={role.id} className={has ? "mz-ok" : "mz-faint"}>
                    {has ? "✓" : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mz-faint mz-small mt-2">
        Quien carga la evidencia o envía un período no puede validar ese mismo cierre (separación de funciones).
      </p>
    </div>
  );
}

function AuditTab() {
  const { company } = useCompany();
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);

  useEffect(() => {
    matrizService.audit(company.id, { page }).then(setData);
  }, [company.id, page]);

  if (!data) return <p className="mz-faint">Cargando…</p>;
  const totalPages = Math.max(1, Math.ceil(data.count / 20));

  return (
    <div className="mz-card">
      <div className="mz-card-head">
        <h3>Historial de auditoría ({data.count} eventos)</h3>
      </div>
      {data.results.map((event) => (
        <div key={event.id} className="mz-doc mz-doc--plain mz-doc--flush">
          <div className="mz-doc-ic mz-doc-ic--info">
            <Icon name="clock-history" />
          </div>
          <div className="mz-doc-info">
            <strong>{event.description}</strong>
            <span>
              {event.obligation_name} · {event.period_label} ({event.period_code}) · {event.actor} ·{" "}
              {fmtDateTime(event.created_at, company.timezone)}
              {event.reason ? ` · Motivo: ${event.reason}` : ""}
            </span>
          </div>
        </div>
      ))}
      <div className="mz-pager">
        <span className="mz-faint">
          Página {page} de {totalPages}
        </span>
        <button type="button" className="btn btn-outline-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
          Anterior
        </button>
        <button type="button" className="btn btn-outline-secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
          Siguiente
        </button>
      </div>
    </div>
  );
}
