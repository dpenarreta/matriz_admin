import { useEffect, useState } from "react";

import { errorMessage, matrizService, saveBlob } from "../../api/matrizService";
import { Icon } from "../../components/common/Icon/Icon";
import { useCompany } from "../../context/CompanyContext";
import { useToast } from "../../context/ToastContext";

function Bars({ items }) {
  if (!items.length) return <div className="mz-empty">Sin datos en el rango seleccionado.</div>;
  return items.map((item) => {
    const total = item.total || 1;
    return (
      <div key={item.code} className="mz-bar-row">
        <span className="mz-bar-label" title={item.name}>
          {item.name}
        </span>
        <div
          className="mz-bar-track"
          role="img"
          aria-label={`${item.name}: ${item.done} finalizadas, ${item.in_progress} en progreso, ${item.overdue} incumplidas`}
        >
          <div className="mz-seg mz-seg--ok" style={{ width: `${(item.done / total) * 100}%` }} />
          <div className="mz-seg mz-seg--warn" style={{ width: `${(item.in_progress / total) * 100}%` }} />
          <div className="mz-seg mz-seg--bad" style={{ width: `${(item.overdue / total) * 100}%` }} />
        </div>
        <span className="mz-bar-num">{item.total}</span>
      </div>
    );
  });
}

function Legend() {
  return (
    <div className="mz-legend">
      <span>
        <i className="mz-legend-ok" /> Finalizado
      </span>
      <span>
        <i className="mz-legend-warn" /> En progreso
      </span>
      <span>
        <i className="mz-legend-bad" /> Incumplido
      </span>
    </div>
  );
}

export function ReportesPage() {
  const { company, can, dataVersion } = useCompany();
  const notify = useToast();
  const thisYear = new Date().getFullYear();
  const [range, setRange] = useState({ due_from: `${thisYear}-01-01`, due_to: `${thisYear}-12-31` });
  const [report, setReport] = useState(null);

  useEffect(() => {
    setReport(null);
    matrizService.report(company.id, range).then(setReport);
  }, [company.id, range, dataVersion]);

  async function exportAs(format) {
    try {
      saveBlob(await matrizService.exportReport(company.id, range, format));
    } catch (err) {
      notify("Exportación no disponible", errorMessage(err), "bad");
    }
  }

  return (
    <>
      <div className="mz-view-head">
        <div>
          <h2>Reportes</h2>
          <p className="mz-desc">Cumplimiento consolidado de {company.short_name} para los vencimientos del rango elegido.</p>
        </div>
        <div className="mz-view-actions">
          <label className="mz-inline-field">
            Desde
            <input type="date" className="form-control form-control-sm" value={range.due_from} onChange={(e) => setRange({ ...range, due_from: e.target.value })} />
          </label>
          <label className="mz-inline-field">
            Hasta
            <input type="date" className="form-control form-control-sm" value={range.due_to} onChange={(e) => setRange({ ...range, due_to: e.target.value })} />
          </label>
          {can("exportar") && (
            <>
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => exportAs("pdf")}>
                <Icon name="file-earmark-pdf" /> PDF
              </button>
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => exportAs("xlsx")}>
                <Icon name="file-earmark-excel" /> Excel
              </button>
            </>
          )}
        </div>
      </div>
      {!report ? (
        <p className="mz-faint">Cargando reporte…</p>
      ) : (
        <>
          <div className="mz-kpi-grid">
            <div className="mz-kpi mz-kpi--ok">
              <span className="mz-kpi-label">Cumplimiento a tiempo</span>
              <div className="mz-kpi-value">{report.kpis.on_time_pct}%</div>
              <div className="mz-kpi-sub">
                {report.kpis.on_time} de {report.kpis.closed} cierres
              </div>
            </div>
            <div className="mz-kpi mz-kpi--warn">
              <span className="mz-kpi-label">Cumplimiento tardío</span>
              <div className="mz-kpi-value">{report.kpis.late_pct}%</div>
              <div className="mz-kpi-sub">{report.kpis.late} cierres fuera de plazo</div>
            </div>
            <div className="mz-kpi mz-kpi--bad">
              <span className="mz-kpi-label">Incumplidas actuales</span>
              <div className="mz-kpi-value">{report.kpis.overdue}</div>
              <div className="mz-kpi-sub">Vencidas sin cierre validado</div>
            </div>
            <div className="mz-kpi mz-kpi--info">
              <span className="mz-kpi-label">En progreso</span>
              <div className="mz-kpi-value">{report.kpis.in_progress}</div>
              <div className="mz-kpi-sub">Abiertas dentro del plazo</div>
            </div>
          </div>
          <div className="mz-grid-2 mz-grid-2--even">
            <div className="mz-card">
              <div className="mz-card-head">
                <h3>Estado por área</h3>
              </div>
              <div className="mz-card-body">
                <Bars items={report.by_area} />
                <Legend />
              </div>
            </div>
            <div className="mz-card">
              <div className="mz-card-head">
                <h3>Estado por entidad de control</h3>
              </div>
              <div className="mz-card-body">
                <Bars items={report.by_entity} />
                <Legend />
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
