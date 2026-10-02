import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { matrizService } from "../../api/matrizService";
import { Icon } from "../../components/common/Icon/Icon";
import { useShell } from "../../components/matriz/AppShell";
import { StatusPill } from "../../components/matriz/StatusPill";
import { useCompany } from "../../context/CompanyContext";
import { fmtDate } from "../../utils/matrizFormat";

function Kpi({ label, tone, icon, value, sub }) {
  return (
    <div className={`mz-kpi mz-kpi--${tone}`}>
      <div className="mz-kpi-top">
        <span className="mz-kpi-label">{label}</span>
        <span className="mz-kpi-icon">
          <Icon name={icon} />
        </span>
      </div>
      <div className="mz-kpi-value">{value}</div>
      <div className="mz-kpi-sub">{sub}</div>
    </div>
  );
}

export function PeriodRow({ period, tz, showDate = true }) {
  const { openPeriod } = useShell();
  return (
    <button type="button" className="mz-row" onClick={() => openPeriod(period.id)}>
      <span className="mz-row-ic">
        <Icon name="building" />
      </span>
      <span className="mz-row-info">
        <strong>{period.obligation_name}</strong>
        <span>
          {period.label} · {period.responsible.full_name}
        </span>
      </span>
      <span className="mz-row-end">
        <StatusPill status={period.status} />
        {showDate && <small>{fmtDate(period.due_at, tz)}</small>}
      </span>
    </button>
  );
}

export function ResumenPage() {
  const { company, can, dataVersion } = useCompany();
  const { openNewObligation } = useShell();
  const [data, setData] = useState(null);

  useEffect(() => {
    setData(null);
    matrizService.dashboard(company.id).then(setData);
  }, [company.id, dataVersion]);

  return (
    <>
      <div className="mz-view-head">
        <div>
          <h2>Resumen — {company.short_name}</h2>
          <p className="mz-desc">
            {company.activity} · {company.country} · Zona horaria {company.timezone}
          </p>
        </div>
        {can("crear") && (
          <button type="button" className="btn btn-primary btn-sm" onClick={openNewObligation}>
            <Icon name="plus-lg" /> Nueva obligación
          </button>
        )}
      </div>
      {!data ? (
        <p className="mz-faint">Cargando indicadores…</p>
      ) : (
        <>
          <div className="mz-kpi-grid">
            <Kpi label="Incumplidas" tone="bad" icon="exclamation-triangle" value={data.counts.overdue} sub="Vencidas sin cierre validado" />
            <Kpi label="En progreso" tone="warn" icon="clock" value={data.counts.in_progress} sub="Abiertas dentro del plazo" />
            <Kpi label="Próximas a vencer" tone="info" icon="hourglass-split" value={data.counts.due_soon} sub="En los próximos 7 días" />
            <Kpi
              label="Finalizadas"
              tone="ok"
              icon="check2-circle"
              value={data.counts.done}
              sub={`${data.counts.done_on_time} a tiempo · ${data.counts.done_late} fuera de plazo`}
            />
          </div>
          <div className="mz-grid-2">
            <div className="mz-card">
              <div className="mz-card-head">
                <h3>Próximos vencimientos</h3>
                <Link to="/matriz" className="btn btn-outline-secondary btn-sm">
                  Ver matriz completa
                </Link>
              </div>
              {data.upcoming.length ? (
                data.upcoming.map((period) => <PeriodRow key={period.id} period={period} tz={company.timezone} />)
              ) : (
                <div className="mz-empty">No hay vencimientos próximos registrados.</div>
              )}
            </div>
            <div className="mz-card">
              <div className="mz-card-head">
                <h3>Cierres recientes</h3>
              </div>
              {data.recent_closures.length ? (
                data.recent_closures.map((period) => (
                  <PeriodRow key={period.id} period={period} tz={company.timezone} showDate={false} />
                ))
              ) : (
                <div className="mz-empty">Aún no se registran cierres.</div>
              )}
            </div>
          </div>
          <div className="mz-note">
            <Icon name="info-circle" /> Los indicadores se calculan en el servidor con la hora actual en la zona horaria de
            la empresa: un período vencido sin cierre validado pasa a «Incumplido» automáticamente.
          </div>
        </>
      )}
    </>
  );
}
