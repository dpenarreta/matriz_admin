import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { errorMessage, matrizService, saveBlob } from "../../api/matrizService";
import { Icon } from "../../components/common/Icon/Icon";
import { useShell } from "../../components/matriz/AppShell";
import { StatusPill } from "../../components/matriz/StatusPill";
import { useCompany } from "../../context/CompanyContext";
import { useToast } from "../../context/ToastContext";
import { daysText, fmtDate, fmtTime, initials } from "../../utils/matrizFormat";

const FILTER_KEYS = ["q", "area", "entity", "responsible", "priority", "status", "stage"];
const COLUMNS = [
  ["name", "Obligación"],
  ["area", "Área"],
  ["entity", "Entidad"],
  [null, "Período"],
  ["responsible", "Responsable"],
  ["due", "Vencimiento"],
  [null, "Días"],
  ["urgency", "Estado"],
];

function daysClass(status) {
  if (status.group === "incumplido") return "mz-days mz-bad";
  if (status.group === "finalizado") return "mz-days mz-faint";
  return status.is_due_today ? "mz-days mz-warn" : "mz-days mz-info";
}

export function MatrizPage() {
  const { company, can, dataVersion } = useCompany();
  const { openPeriod, openNewObligation } = useShell();
  const notify = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [catalogs, setCatalogs] = useState(null);
  const [people, setPeople] = useState([]);
  const [data, setData] = useState(null);
  const [group, setGroup] = useState("none");

  const filters = useMemo(() => {
    const result = {};
    FILTER_KEYS.forEach((key) => {
      if (searchParams.get(key)) result[key] = searchParams.get(key);
    });
    return result;
  }, [searchParams]);
  const sort = searchParams.get("sort") || "urgency";
  const page = Number(searchParams.get("page")) || 1;

  useEffect(() => {
    matrizService.catalogs(company.id).then(setCatalogs);
    matrizService.people(company.id).then(setPeople);
  }, [company.id]);

  useEffect(() => {
    setData(null);
    matrizService.periods(company.id, { ...filters, sort, page, page_size: 50 }).then(setData);
  }, [company.id, filters, sort, page, dataVersion]);

  function setParam(key, value) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setSearchParams(next);
  }

  function toggleSort(key) {
    if (!key) return;
    setParam("sort", sort === key ? `-${key}` : key);
  }

  async function exportAs(format) {
    try {
      saveBlob(await matrizService.exportPeriods(company.id, { ...filters, sort }, format));
    } catch (err) {
      notify("Exportación no disponible", errorMessage(err), "bad");
    }
  }

  const rows = useMemo(() => data?.results || [], [data]);
  const grouped = useMemo(() => {
    if (group === "none") return [[null, rows]];
    const map = new Map();
    rows.forEach((row) => {
      const key = group === "area" ? row.area.name : row.control_entity.name;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(row);
    });
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [rows, group]);

  const hasFilters = Object.keys(filters).length > 0;
  const totalPages = data ? Math.max(1, Math.ceil(data.count / 50)) : 1;

  return (
    <>
      <div className="mz-view-head">
        <div>
          <h2>Matriz de obligaciones</h2>
          <p className="mz-desc">
            Vista consolidada por período. Cada fila es un vencimiento independiente de su obligación recurrente, con
            evidencias y estado propios.
          </p>
        </div>
        <div className="mz-view-actions">
          {can("exportar") && (
            <>
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => exportAs("xlsx")}>
                <Icon name="file-earmark-excel" /> Excel
              </button>
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => exportAs("pdf")}>
                <Icon name="file-earmark-pdf" /> PDF
              </button>
            </>
          )}
          {can("crear") && (
            <button type="button" className="btn btn-primary btn-sm" onClick={openNewObligation}>
              <Icon name="plus-lg" /> Nueva obligación
            </button>
          )}
        </div>
      </div>

      <div className="mz-filter-bar">
        <label className="mz-fb-search">
          <Icon name="search" />
          <span className="visually-hidden">Buscar</span>
          <input
            type="search"
            placeholder="Buscar…"
            defaultValue={filters.q || ""}
            key={filters.q || ""}
            onKeyDown={(e) => e.key === "Enter" && setParam("q", e.target.value)}
            onBlur={(e) => e.target.value !== (filters.q || "") && setParam("q", e.target.value)}
          />
        </label>
        <select aria-label="Área" className="form-select form-select-sm" value={filters.area || ""} onChange={(e) => setParam("area", e.target.value)}>
          <option value="">Área: todas</option>
          {catalogs?.areas.map((area) => (
            <option key={area.id} value={area.id}>
              {area.name}
            </option>
          ))}
        </select>
        <select aria-label="Entidad" className="form-select form-select-sm" value={filters.entity || ""} onChange={(e) => setParam("entity", e.target.value)}>
          <option value="">Entidad: todas</option>
          {catalogs?.control_entities.map((entity) => (
            <option key={entity.id} value={entity.id}>
              {entity.name}
            </option>
          ))}
        </select>
        <select aria-label="Responsable" className="form-select form-select-sm" value={filters.responsible || ""} onChange={(e) => setParam("responsible", e.target.value)}>
          <option value="">Responsable: todos</option>
          {people.map((person) => (
            <option key={person.id} value={person.id}>
              {person.full_name}
            </option>
          ))}
        </select>
        <select aria-label="Prioridad" className="form-select form-select-sm" value={filters.priority || ""} onChange={(e) => setParam("priority", e.target.value)}>
          <option value="">Prioridad: todas</option>
          <option value="alta">Alta</option>
          <option value="media">Media</option>
          <option value="baja">Baja</option>
        </select>
        <select aria-label="Estado" className="form-select form-select-sm" value={filters.status || ""} onChange={(e) => setParam("status", e.target.value)}>
          <option value="">Estado: todos</option>
          <option value="incumplido">Incumplido</option>
          <option value="en_progreso">En progreso</option>
          <option value="finalizado">Finalizado</option>
        </select>
        <select aria-label="Etapa" className="form-select form-select-sm" value={filters.stage || ""} onChange={(e) => setParam("stage", e.target.value)}>
          <option value="">Etapa: todas</option>
          {catalogs?.stages.map((stage) => (
            <option key={stage.value} value={stage.value}>
              {stage.label}
            </option>
          ))}
        </select>
        <div className="mz-chips" role="group" aria-label="Agrupar">
          {[
            ["none", "Sin agrupar"],
            ["area", "Por área"],
            ["entity", "Por entidad"],
          ].map(([key, label]) => (
            <button key={key} type="button" className={group === key ? "is-on" : ""} onClick={() => setGroup(key)}>
              {label}
            </button>
          ))}
        </div>
        {hasFilters && (
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setSearchParams({})}>
            Limpiar filtros
          </button>
        )}
      </div>

      {!data ? (
        <p className="mz-faint">Cargando…</p>
      ) : (
        <>
          <div className="mz-table-wrap">
            <table className="mz-table">
              <thead>
                <tr>
                  {COLUMNS.map(([key, label]) => (
                    <th
                      key={label}
                      className={key ? "is-sortable" : ""}
                      aria-sort={sort.replace("-", "") === key ? (sort.startsWith("-") ? "descending" : "ascending") : undefined}
                      onClick={() => toggleSort(key)}
                    >
                      {label}
                      {sort.replace("-", "") === key && <Icon name={sort.startsWith("-") ? "caret-up-fill" : "caret-down-fill"} />}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={COLUMNS.length}>
                      <div className="mz-empty">No hay obligaciones que coincidan con los filtros aplicados.</div>
                    </td>
                  </tr>
                )}
                {grouped.map(([name, items]) => (
                  <GroupRows key={name || "all"} name={name} items={items} tz={company.timezone} onOpen={openPeriod} />
                ))}
              </tbody>
            </table>
          </div>
          <div className="mz-cards">
            {rows.map((row) => (
              <button key={row.id} type="button" className="mz-card-row" onClick={() => openPeriod(row.id)}>
                <div className="mz-row-between">
                  <div>
                    <div className="mz-strong">{row.obligation_name}</div>
                    <div className="mz-code">
                      {row.code} · {row.label}
                    </div>
                  </div>
                  <StatusPill status={row.status} />
                </div>
                <div className="mz-card-meta">
                  <span>
                    <b>Área:</b> {row.area.name}
                  </span>
                  <span>
                    <b>Responsable:</b> {row.responsible.full_name}
                  </span>
                  <span>
                    <b>Vence:</b> {fmtDate(row.due_at, company.timezone)}
                  </span>
                  <span className={daysClass(row.status)}>{daysText(row.status)}</span>
                </div>
              </button>
            ))}
          </div>
          <div className="mz-pager">
            <span className="mz-faint">
              {data.count} período(s) · página {page} de {totalPages}
            </span>
            <button type="button" className="btn btn-outline-secondary btn-sm" disabled={page <= 1} onClick={() => setParam("page", String(page - 1))}>
              Anterior
            </button>
            <button type="button" className="btn btn-outline-secondary btn-sm" disabled={page >= totalPages} onClick={() => setParam("page", String(page + 1))}>
              Siguiente
            </button>
          </div>
        </>
      )}
    </>
  );
}

function GroupRows({ name, items, tz, onOpen }) {
  return (
    <>
      {name && (
        <tr className="mz-group-row">
          <td colSpan={COLUMNS.length}>
            {name} <span className="mz-faint">({items.length})</span>
          </td>
        </tr>
      )}
      {items.map((row) => (
        <tr key={row.id} onClick={() => onOpen(row.id)} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && onOpen(row.id)}>
          <td>
            <span className="mz-strong">{row.obligation_name}</span>
            <br />
            <span className="mz-code">{row.code}</span>
          </td>
          <td>{row.area.name}</td>
          <td>{row.control_entity.name}</td>
          <td>{row.label}</td>
          <td>
            <span className="mz-avatar-xs">{initials(row.responsible.full_name)}</span>
            {row.responsible.full_name}
          </td>
          <td className="mz-mono">
            {fmtDate(row.due_at, tz)}
            <br />
            <span className="mz-faint mz-small">{fmtTime(row.due_at, tz)}</span>
          </td>
          <td>
            <span className={daysClass(row.status)}>{daysText(row.status)}</span>
          </td>
          <td>
            <StatusPill status={row.status} />
            {row.status.group === "en_progreso" && row.status.is_due_today && (
              <div className="mz-small mz-faint mt-1">{row.stage_label}</div>
            )}
          </td>
        </tr>
      ))}
    </>
  );
}
