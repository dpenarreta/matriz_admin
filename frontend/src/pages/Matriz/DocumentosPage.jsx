import { useEffect, useState } from "react";

import { matrizService } from "../../api/matrizService";
import { Icon } from "../../components/common/Icon/Icon";
import { useShell } from "../../components/matriz/AppShell";
import { StatusPill } from "../../components/matriz/StatusPill";
import { useCompany } from "../../context/CompanyContext";

function DocRow({ period, withEvidence }) {
  const { openPeriod } = useShell();
  return (
    <button type="button" className="mz-row" onClick={() => openPeriod(period.id)}>
      <span className={`mz-row-ic ${withEvidence ? "mz-row-ic--pdf" : ""}`}>
        <Icon name={withEvidence ? "file-earmark-pdf" : "folder2"} />
      </span>
      <span className="mz-row-info">
        <strong>{period.obligation_name}</strong>
        <span>
          {period.label} · {withEvidence ? `${period.valid_document_count} documento(s) · ` : ""}
          {period.responsible.full_name}
        </span>
      </span>
      <span className="mz-row-end">
        <StatusPill status={period.status} />
      </span>
    </button>
  );
}

export function DocumentosPage() {
  const { company, dataVersion } = useCompany();
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => {
    setData(null);
    matrizService.documentsOverview(company.id, query ? { q: query } : {}).then(setData);
  }, [company.id, query, dataVersion]);

  return (
    <>
      <div className="mz-view-head">
        <div>
          <h2>Documentos</h2>
          <p className="mz-desc">
            Repositorio de evidencias en PDF por obligación y período. Un período con solo documentos rechazados cuenta
            como pendiente.
          </p>
        </div>
        <label className="mz-fb-search mz-fb-search--compact">
          <Icon name="search" />
          <span className="visually-hidden">Buscar</span>
          <input type="search" placeholder="Filtrar por obligación o período…" onKeyDown={(e) => e.key === "Enter" && setQuery(e.target.value)} />
        </label>
      </div>
      {!data ? (
        <p className="mz-faint">Cargando…</p>
      ) : (
        <>
          <div className="mz-card mb-3">
            <div className="mz-card-head">
              <h3>Expedientes con evidencia ({data.with_evidence.length})</h3>
            </div>
            {data.with_evidence.length ? (
              data.with_evidence.map((period) => <DocRow key={period.id} period={period} withEvidence />)
            ) : (
              <div className="mz-empty">Sin documentos cargados todavía.</div>
            )}
          </div>
          <div className="mz-card">
            <div className="mz-card-head">
              <h3>Pendientes de evidencia ({data.pending.length})</h3>
            </div>
            {data.pending.length ? (
              data.pending.map((period) => <DocRow key={period.id} period={period} />)
            ) : (
              <div className="mz-empty">Todos los períodos cuentan con evidencia registrada.</div>
            )}
          </div>
        </>
      )}
    </>
  );
}
