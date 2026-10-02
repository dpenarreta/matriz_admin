import { useEffect, useMemo, useState } from "react";

import { matrizService } from "../../api/matrizService";
import { Icon } from "../../components/common/Icon/Icon";
import { useShell } from "../../components/matriz/AppShell";
import { useCompany } from "../../context/CompanyContext";
import { monthName, STATUS_TONE, toDateInput } from "../../utils/matrizFormat";

const DOW = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
const MAX_CHIPS = 3;

export function CalendarioPage() {
  const { company, dataVersion } = useCompany();
  const { openPeriod } = useShell();
  const today = new Date();
  const [cursor, setCursor] = useState({ year: today.getFullYear(), month: today.getMonth() });
  const [periods, setPeriods] = useState([]);
  const [expandedDay, setExpandedDay] = useState(null);

  useEffect(() => {
    matrizService.calendar(company.id, cursor.year, cursor.month + 1).then(setPeriods);
  }, [company.id, cursor, dataVersion]);

  const byDay = useMemo(() => {
    const map = {};
    periods.forEach((period) => {
      const key = toDateInput(period.due_at, company.timezone);
      (map[key] = map[key] || []).push(period);
    });
    return map;
  }, [periods, company.timezone]);

  function move(delta) {
    setExpandedDay(null);
    setCursor(({ year, month }) => {
      const index = month + delta;
      return { year: year + Math.floor(index / 12), month: ((index % 12) + 12) % 12 };
    });
  }

  const first = new Date(cursor.year, cursor.month, 1);
  const daysInMonth = new Date(cursor.year, cursor.month + 1, 0).getDate();
  const todayKey = toDateInput(today, company.timezone);
  const cells = [];
  for (let i = 0; i < first.getDay(); i += 1) cells.push(null);
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(`${cursor.year}-${String(cursor.month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
  }

  return (
    <>
      <div className="mz-view-head">
        <div>
          <h2>Calendario de vencimientos</h2>
          <p className="mz-desc">Vista mensual de todos los períodos con vencimiento en {company.short_name}.</p>
        </div>
        <div className="mz-view-actions">
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => move(-1)} aria-label="Mes anterior">
            <Icon name="chevron-left" />
          </button>
          <span className="mz-cal-label">
            {monthName(cursor.month)} {cursor.year}
          </span>
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => move(1)} aria-label="Mes siguiente">
            <Icon name="chevron-right" />
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={() => setCursor({ year: today.getFullYear(), month: today.getMonth() })}
          >
            Hoy
          </button>
        </div>
      </div>
      <div className="mz-cal-grid">
        {DOW.map((dow) => (
          <div key={dow} className="mz-cal-dow">
            {dow}
          </div>
        ))}
        {cells.map((key, index) => {
          if (!key) return <div key={`empty-${index}`} className="mz-cal-day is-other" />;
          const items = byDay[key] || [];
          const expanded = expandedDay === key;
          const visible = expanded ? items : items.slice(0, MAX_CHIPS);
          return (
            <div key={key} className={`mz-cal-day ${key === todayKey ? "is-today" : ""}`}>
              <div className="mz-cal-num">{Number(key.slice(-2))}</div>
              {visible.map((period) => (
                <button
                  key={period.id}
                  type="button"
                  className={`mz-cal-chip mz-cal-chip--${STATUS_TONE[period.status.group]}`}
                  title={`${period.obligation_name} · ${period.status.label}`}
                  onClick={() => openPeriod(period.id)}
                >
                  {period.obligation_name}
                </button>
              ))}
              {items.length > MAX_CHIPS && (
                <button type="button" className="mz-cal-more" onClick={() => setExpandedDay(expanded ? null : key)}>
                  {expanded ? "Ver menos" : `+${items.length - MAX_CHIPS} más`}
                </button>
              )}
            </div>
          );
        })}
      </div>
      <div className="mz-legend">
        <span>
          <i className="mz-legend-bad" /> Incumplido
        </span>
        <span>
          <i className="mz-legend-warn" /> En progreso
        </span>
        <span>
          <i className="mz-legend-ok" /> Finalizado
        </span>
      </div>
    </>
  );
}
