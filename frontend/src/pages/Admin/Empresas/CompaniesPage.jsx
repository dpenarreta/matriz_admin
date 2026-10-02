import { useEffect, useState } from "react";

import { adminMatrizService } from "../../../api/adminMatrizService";
import { errorMessage } from "../../../api/matrizService";
import { Breadcrumbs } from "../../../components/common/Breadcrumbs/Breadcrumbs";
import { usePermission } from "../../../hooks/usePermission";

const BREADCRUMB_ITEMS = [{ label: "Configuración" }, { label: "Empresas" }];
const TIMEZONES = [
  "America/Guayaquil",
  "America/Bogota",
  "America/Lima",
  "America/Panama",
  "America/Mexico_City",
  "America/Santiago",
];
const EMPTY = {
  code: "",
  legal_name: "",
  short_name: "",
  country: "Ecuador",
  activity: "",
  timezone: "America/Guayaquil",
  color: "#164b86",
  compliance_date_basis: "validation",
  is_active: true,
  branch: "",
};

/**
 * Empresas (tableros) y sucursales. Exige `empresas.ver`; crear y editar,
 * `empresas.editar`. Las empresas no se eliminan: se desactivan, para
 * conservar su historial.
 */
export function CompaniesPage() {
  const canEdit = usePermission("empresas.editar");
  const [companies, setCompanies] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [newBranch, setNewBranch] = useState("");
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  function load() {
    return adminMatrizService
      .companies()
      .then(setCompanies)
      .catch(() => setError("No se pudo cargar el listado de empresas."));
  }

  useEffect(() => {
    load();
  }, []);

  function startEdit(company) {
    setEditing(company ? company.id : "new");
    setForm(company ? { ...EMPTY, ...company, branch: "" } : EMPTY);
    setMessage(null);
    setError(null);
  }

  const set = (key) => (event) =>
    setForm({ ...form, [key]: event.target.type === "checkbox" ? event.target.checked : event.target.value });

  async function save(event) {
    event.preventDefault();
    setError(null);
    const payload = {
      code: form.code,
      legal_name: form.legal_name,
      short_name: form.short_name,
      country: form.country,
      activity: form.activity,
      timezone: form.timezone,
      color: form.color,
      compliance_date_basis: form.compliance_date_basis,
      is_active: form.is_active,
    };
    try {
      if (editing === "new") {
        const created = await adminMatrizService.createCompany({
          ...payload,
          branches: form.branch ? [form.branch] : [],
        });
        setEditing(created.id);
        setForm({ ...EMPTY, ...created, branch: "" });
      } else {
        const updated = await adminMatrizService.updateCompany(editing, payload);
        setForm({ ...EMPTY, ...updated, branch: "" });
      }
      setMessage("Empresa guardada.");
      load();
    } catch (err) {
      setError(errorMessage(err, "No se pudo guardar la empresa."));
    }
  }

  async function addBranch() {
    try {
      await adminMatrizService.addBranch(editing, { name: newBranch });
      setNewBranch("");
      const updated = await adminMatrizService.company(editing);
      setForm({ ...EMPTY, ...updated, branch: "" });
      load();
    } catch (err) {
      setError(errorMessage(err, "No se pudo agregar la sucursal."));
    }
  }

  async function toggleBranch(branch) {
    try {
      await adminMatrizService.updateBranch(editing, branch.id, { is_active: !branch.is_active });
      const updated = await adminMatrizService.company(editing);
      setForm({ ...EMPTY, ...updated, branch: "" });
    } catch (err) {
      setError(errorMessage(err, "No se pudo actualizar la sucursal."));
    }
  }

  return (
    <div className="companies-page">
      <Breadcrumbs items={BREADCRUMB_ITEMS} />
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2>Empresas</h2>
        {canEdit && (
          <button type="button" className="btn btn-primary btn-sm" onClick={() => startEdit(null)}>
            Nueva empresa
          </button>
        )}
      </div>
      {error && <div className="alert alert-danger">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}

      <div className="table-responsive mb-4">
        <table className="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th>Código</th>
              <th>Empresa</th>
              <th>Zona horaria</th>
              <th>Sucursales</th>
              <th>Personas con rol</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {companies.map((company) => (
              <tr key={company.id}>
                <td>
                  <span className="d-inline-block me-2 rounded" style={{ width: 10, height: 10, background: company.color }} />
                  {company.code}
                </td>
                <td>
                  {company.short_name}
                  <div className="small text-muted">{company.legal_name}</div>
                </td>
                <td>{company.timezone}</td>
                <td>{company.branches.filter((branch) => branch.is_active).length}</td>
                <td>{company.member_count}</td>
                <td>{company.is_active ? "Activa" : "Inactiva"}</td>
                <td>
                  <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => startEdit(company)}>
                    {canEdit ? "Editar" : "Ver"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <div className="card">
          <div className="card-body">
            <h5 className="card-title">{editing === "new" ? "Nueva empresa" : `Editar ${form.short_name}`}</h5>
            <form onSubmit={save}>
              <fieldset disabled={!canEdit} className="row g-3">
                <div className="col-md-2">
                  <label className="form-label" htmlFor="co-code">Código</label>
                  <input id="co-code" className="form-control" value={form.code} onChange={set("code")} required maxLength={10} />
                </div>
                <div className="col-md-5">
                  <label className="form-label" htmlFor="co-legal">Razón social</label>
                  <input id="co-legal" className="form-control" value={form.legal_name} onChange={set("legal_name")} required />
                </div>
                <div className="col-md-5">
                  <label className="form-label" htmlFor="co-short">Nombre corto</label>
                  <input id="co-short" className="form-control" value={form.short_name} onChange={set("short_name")} required />
                </div>
                <div className="col-md-3">
                  <label className="form-label" htmlFor="co-country">País</label>
                  <input id="co-country" className="form-control" value={form.country} onChange={set("country")} />
                </div>
                <div className="col-md-5">
                  <label className="form-label" htmlFor="co-activity">Actividad económica</label>
                  <input id="co-activity" className="form-control" value={form.activity} onChange={set("activity")} />
                </div>
                <div className="col-md-4">
                  <label className="form-label" htmlFor="co-tz">Zona horaria</label>
                  <select id="co-tz" className="form-select" value={form.timezone} onChange={set("timezone")}>
                    {[...new Set([form.timezone, ...TIMEZONES])].map((tz) => (
                      <option key={tz}>{tz}</option>
                    ))}
                  </select>
                </div>
                <div className="col-md-5">
                  <label className="form-label" htmlFor="co-basis">Fecha que cuenta como cumplimiento</label>
                  <select id="co-basis" className="form-select" value={form.compliance_date_basis} onChange={set("compliance_date_basis")}>
                    <option value="validation">La fecha de validación del cierre</option>
                    <option value="submission">La fecha de envío a validación</option>
                  </select>
                </div>
                <div className="col-md-2">
                  <label className="form-label" htmlFor="co-color">Color</label>
                  <input id="co-color" type="color" className="form-control form-control-color" value={form.color} onChange={set("color")} />
                </div>
                <div className="col-md-3 d-flex align-items-end">
                  <div className="form-check">
                    <input id="co-active" type="checkbox" className="form-check-input" checked={form.is_active} onChange={set("is_active")} />
                    <label className="form-check-label" htmlFor="co-active">Empresa activa</label>
                  </div>
                </div>
                {editing === "new" && (
                  <div className="col-md-6">
                    <label className="form-label" htmlFor="co-branch">Sucursal principal</label>
                    <input id="co-branch" className="form-control" value={form.branch} onChange={set("branch")} placeholder="Ej. Matriz Quito" />
                  </div>
                )}
              </fieldset>
              <div className="mt-3 d-flex gap-2">
                {canEdit && (
                  <button type="submit" className="btn btn-primary btn-sm">
                    Guardar
                  </button>
                )}
                <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setEditing(null)}>
                  Cerrar
                </button>
              </div>
            </form>

            {editing !== "new" && (
              <div className="mt-4">
                <h6>Sucursales</h6>
                <ul className="list-group mb-2">
                  {(form.branches || []).map((branch) => (
                    <li key={branch.id} className="list-group-item d-flex justify-content-between align-items-center">
                      <span className={branch.is_active ? "" : "text-muted text-decoration-line-through"}>{branch.name}</span>
                      {canEdit && (
                        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => toggleBranch(branch)}>
                          {branch.is_active ? "Desactivar" : "Activar"}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                {canEdit && (
                  <div className="d-flex gap-2 col-md-6">
                    <input
                      className="form-control form-control-sm"
                      placeholder="Nueva sucursal"
                      aria-label="Nueva sucursal"
                      value={newBranch}
                      onChange={(event) => setNewBranch(event.target.value)}
                    />
                    <button type="button" className="btn btn-outline-primary btn-sm" disabled={!newBranch.trim()} onClick={addBranch}>
                      Agregar
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
