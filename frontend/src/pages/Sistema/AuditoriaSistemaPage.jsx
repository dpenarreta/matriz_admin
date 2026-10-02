import { useEffect, useState } from "react";

import { apiClient } from "../../api/client";
import { errorMessage, saveBlob } from "../../api/matrizService";
import { Icon } from "../../components/common/Icon/Icon";
import { useToast } from "../../context/ToastContext";
import { usePermission } from "../../hooks/usePermission";

const MODULES = [
  ["", "Todos los módulos"],
  ["usuarios", "Usuarios"],
  ["roles", "Roles"],
  ["configuracion", "Configuración"],
  ["matriz", "Matriz"],
  ["empresas", "Empresas"],
  ["catalogos", "Catálogos"],
];

function fmt(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleString("es-EC", { dateStyle: "medium", timeStyle: "short" });
}

/**
 * Bitácora técnica del template base (`AuditLog`): toda operación
 * administrativa y cada acceso denegado. El detalle (valores anteriores y
 * nuevos) solo se ve con `auditoria.ver_detalle`. Exige `auditoria.ver`.
 */
export function AuditoriaSistemaPage() {
  const notify = useToast();
  const canExport = usePermission("auditoria.exportar");
  const [filters, setFilters] = useState({ action: "", module: "", result: "", created_from: "", created_to: "" });
  const [applied, setApplied] = useState(filters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    const params = { page };
    Object.entries(applied).forEach(([key, value]) => {
      if (value) params[key] = value;
    });
    setData(null);
    apiClient
      .get("/admin/audit-logs/", { params })
      .then((res) => setData(res.data))
      .catch((err) => notify("No se pudo cargar la auditoría", errorMessage(err), "bad"));
  }, [applied, page, notify]);

  async function exportCsv() {
    try {
      const params = {};
      Object.entries(applied).forEach(([key, value]) => {
        if (value) params[key] = value;
      });
      const res = await apiClient.get("/admin/audit-logs/export/", { params, responseType: "blob" });
      saveBlob({ blob: res.data, filename: "auditoria-sistema.csv" });
    } catch (err) {
      notify("Exportación no disponible", errorMessage(err), "bad");
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.count / 20)) : 1;

  return (
    <>
      <div className="mz-view-head">
        <div>
          <h2>Auditoría del sistema</h2>
          <p className="mz-desc">
            Registro de solo lectura de toda operación administrativa: usuarios, roles, empresas, catálogos, matriz y
            accesos denegados.
          </p>
        </div>
        {canExport && (
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={exportCsv}>
            <Icon name="filetype-csv" /> Exportar CSV
          </button>
        )}
      </div>

      <form
        className="mz-filter-bar"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setApplied(filters);
        }}
      >
        <input
          className="form-control form-control-sm"
          style={{ maxWidth: 200 }}
          placeholder="Acción (p. ej. role, login)"
          aria-label="Acción"
          value={filters.action}
          onChange={(e) => setFilters({ ...filters, action: e.target.value })}
        />
        <select
          className="form-select form-select-sm"
          aria-label="Módulo"
          value={filters.module}
          onChange={(e) => setFilters({ ...filters, module: e.target.value })}
        >
          {MODULES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          className="form-select form-select-sm"
          aria-label="Resultado"
          value={filters.result}
          onChange={(e) => setFilters({ ...filters, result: e.target.value })}
        >
          <option value="">Todos los resultados</option>
          <option value="success">Éxito</option>
          <option value="failure">Fallido</option>
        </select>
        <label className="mz-inline-field">
          Desde
          <input type="date" className="form-control form-control-sm" value={filters.created_from} onChange={(e) => setFilters({ ...filters, created_from: e.target.value })} />
        </label>
        <label className="mz-inline-field">
          Hasta
          <input type="date" className="form-control form-control-sm" value={filters.created_to} onChange={(e) => setFilters({ ...filters, created_to: e.target.value })} />
        </label>
        <button type="submit" className="btn btn-primary btn-sm">
          Filtrar
        </button>
      </form>

      <div className="mz-card">
        <div className="mz-card-head">
          <h3>Eventos ({data ? data.count : "…"})</h3>
        </div>
        {!data && <div className="mz-empty">Cargando…</div>}
        {data?.results.length === 0 && <div className="mz-empty">Sin eventos con esos filtros.</div>}
        {data?.results.map((entry) => (
          <div key={entry.id}>
            <button type="button" className="mz-row" onClick={() => setOpen(open === entry.id ? null : entry.id)}>
              <span className={`mz-row-ic ${entry.result === "failure" ? "mz-row-ic--pdf" : ""}`}>
                <Icon name={entry.result === "failure" ? "shield-exclamation" : "clock-history"} />
              </span>
              <span className="mz-row-info">
                <strong>
                  {entry.action} <span className="mz-faint">· {entry.module || "—"}</span>
                </strong>
                <span>
                  {entry.actor_username || "Sistema"} · {entry.target_type} {entry.target_id} · {fmt(entry.created_at_local)}
                  {entry.ip_address ? ` · ${entry.ip_address}` : ""}
                </span>
              </span>
              <span className={`mz-pill mz-pill--${entry.result === "failure" ? "bad" : "ok"}`}>
                {entry.result === "failure" ? "Fallido" : "Éxito"}
              </span>
            </button>
            {open === entry.id && (
              <div className="mz-card-body mz-small">
                {"new_values" in entry ? (
                  <div className="mz-field-grid">
                    <div>
                      <b>Valores anteriores</b>
                      <pre className="mz-code">{JSON.stringify(entry.previous_values, null, 2)}</pre>
                    </div>
                    <div>
                      <b>Valores nuevos</b>
                      <pre className="mz-code">{JSON.stringify(entry.new_values, null, 2)}</pre>
                    </div>
                  </div>
                ) : (
                  <p className="mz-faint">Ver el detalle requiere el permiso auditoria.ver_detalle.</p>
                )}
                <p className="mz-faint mb-0">
                  {entry.browser} · {entry.operating_system} · {entry.device} · correlación {entry.correlation_id || "—"}
                </p>
              </div>
            )}
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
    </>
  );
}
