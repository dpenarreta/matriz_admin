import { useEffect, useState } from "react";

import { adminMatrizService } from "../../../api/adminMatrizService";
import { adminUsersService } from "../../../api/adminUsersService";
import { errorMessage } from "../../../api/matrizService";
import { rolesService } from "../../../api/rolesService";
import { PermissionsCheckboxGroup } from "../../../components/common/PermissionsCheckboxGroup/PermissionsCheckboxGroup";
import { usePermission } from "../../../hooks/usePermission";
import { usePermissionsCatalog } from "../../../hooks/usePermissionsCatalog";

function Feedback({ state }) {
  if (!state) return null;
  return <div className={`alert alert-${state.ok ? "success" : "danger"} py-2`}>{state.text}</div>;
}

/**
 * Accesos de un usuario, en tres niveles (ver docs/matriz/roles-y-permisos.md):
 *
 * 1. Roles del sistema (`user.groups`): permisos de Administración del
 *    sistema (usuarios, roles, empresas, catálogos…).
 * 2. Permisos directos (`user.user_permissions`), además de los del rol.
 * 3. Roles por empresa (membresías): lo que puede hacer en la matriz de cada
 *    empresa. Un mismo rol puede usarse en el nivel 1 y en el 3.
 */
export function UserAccessSections({ userId }) {
  const canEdit = usePermission("usuarios.editar");
  const canSeeRoles = usePermission("roles.ver");
  const canSeeCompanies = usePermission("empresas.ver");
  const { catalog } = usePermissionsCatalog();
  const [user, setUser] = useState(null);
  const [roles, setRoles] = useState([]);
  const [systemRoles, setSystemRoles] = useState(new Set());
  const [direct, setDirect] = useState(new Set());
  const [feedback, setFeedback] = useState({});

  useEffect(() => {
    adminUsersService.get(userId).then((data) => {
      setUser(data);
      setSystemRoles(new Set(data.roles.map((role) => role.id)));
      setDirect(new Set(data.direct_permissions));
    });
    if (canSeeRoles) rolesService.list().then(setRoles);
  }, [userId, canSeeRoles]);

  async function save(key, action, okText) {
    try {
      await action();
      setFeedback({ ...feedback, [key]: { ok: true, text: okText } });
    } catch (err) {
      setFeedback({ ...feedback, [key]: { ok: false, text: errorMessage(err) } });
    }
  }

  if (!user) return null;

  return (
    <div className="user-access mt-4">
      {user.is_superuser && (
        <div className="alert alert-info">
          Este usuario es superusuario: tiene todos los permisos del sistema y de la matriz en todas las empresas.
        </div>
      )}

      <section className="mb-4">
        <h5>Roles del sistema</h5>
        <p className="text-muted small">
          Dan acceso a Administración del sistema. Los roles se crean y se editan en Administración → Roles.
        </p>
        <Feedback state={feedback.roles} />
        {canSeeRoles ? (
          <fieldset disabled={!canEdit}>
            <div className="d-flex flex-wrap gap-3 mb-2">
              {roles.map((role) => (
                <div key={role.id} className="form-check">
                  <input
                    id={`sys-role-${role.id}`}
                    type="checkbox"
                    className="form-check-input"
                    checked={systemRoles.has(role.id)}
                    onChange={(event) => {
                      const next = new Set(systemRoles);
                      if (event.target.checked) next.add(role.id);
                      else next.delete(role.id);
                      setSystemRoles(next);
                    }}
                  />
                  <label className="form-check-label" htmlFor={`sys-role-${role.id}`}>
                    {role.name} <span className="text-muted small">({role.permission_codenames.length})</span>
                  </label>
                </div>
              ))}
            </div>
            {canEdit && (
              <button
                type="button"
                className="btn btn-outline-primary btn-sm"
                onClick={() =>
                  save("roles", () => adminUsersService.assignRoles(userId, [...systemRoles]), "Roles del sistema guardados.")
                }
              >
                Guardar roles del sistema
              </button>
            )}
          </fieldset>
        ) : (
          <p className="small">{user.roles.map((role) => role.name).join(", ") || "Sin roles del sistema."}</p>
        )}
      </section>

      {catalog && (
        <section className="mb-4">
          <h5>Permisos directos</h5>
          <p className="text-muted small">Permisos adicionales a los de sus roles del sistema. Úselos con moderación.</p>
          <Feedback state={feedback.permissions} />
          <fieldset disabled={!canEdit}>
            <PermissionsCheckboxGroup catalog={catalog} selected={direct} onChange={setDirect} />
            {canEdit && (
              <button
                type="button"
                className="btn btn-outline-primary btn-sm mt-2"
                onClick={() =>
                  save(
                    "permissions",
                    () => adminUsersService.assignPermissions(userId, [...direct]),
                    "Permisos directos guardados."
                  )
                }
              >
                Guardar permisos directos
              </button>
            )}
          </fieldset>
        </section>
      )}

      {canSeeCompanies && <CompanyRolesSection userId={userId} canEdit={canEdit} />}
    </div>
  );
}

function CompanyRolesSection({ userId, canEdit }) {
  const [companies, setCompanies] = useState([]);
  const [roles, setRoles] = useState([]);
  const [areas, setAreas] = useState([]);
  const [rows, setRows] = useState(null);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    Promise.all([
      adminMatrizService.companies(),
      adminMatrizService.matrixRoles(),
      adminMatrizService.catalog("areas").catch(() => []),
      adminMatrizService.userMemberships(userId),
    ]).then(([companyList, roleList, areaList, memberships]) => {
      setCompanies(companyList);
      setRoles(roleList);
      setAreas(areaList);
      setRows(
        memberships.map((membership) => ({
          company_id: membership.company.id,
          role_id: membership.role.id,
          area_ids: membership.areas.map((area) => area.id),
        }))
      );
    });
  }, [userId]);

  if (rows === null) return null;
  const used = new Set(rows.map((row) => row.company_id));
  const available = companies.filter((company) => company.is_active && !used.has(company.id));

  function update(index, patch) {
    setRows(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  async function save() {
    try {
      await adminMatrizService.replaceUserMemberships(userId, rows);
      setFeedback({ ok: true, text: "Roles por empresa guardados." });
    } catch (err) {
      setFeedback({ ok: false, text: errorMessage(err) });
    }
  }

  return (
    <section className="mb-4">
      <h5>Roles por empresa (matriz de obligaciones)</h5>
      <p className="text-muted small">
        Qué puede hacer en la matriz de cada empresa: los permisos <code>matriz.*</code> del rol elegido. Sin el
        permiso «Ver todas», solo ve sus propias obligaciones; en ese caso puede limitar las áreas donde crea.
      </p>
      <Feedback state={feedback} />
      <fieldset disabled={!canEdit}>
        {rows.length === 0 && <p className="small">Sin roles en ninguna empresa.</p>}
        {rows.map((row, index) => {
          const company = companies.find((item) => item.id === row.company_id);
          const role = roles.find((item) => item.id === row.role_id);
          const scoped = role && !role.permission_codenames.includes("matriz.ver_todas");
          return (
            <div key={row.company_id} className="row g-2 align-items-start mb-2">
              <div className="col-md-3 pt-1">
                <strong>{company?.short_name || "Empresa"}</strong>
              </div>
              <div className="col-md-3">
                <select
                  className="form-select form-select-sm"
                  aria-label={`Rol en ${company?.short_name}`}
                  value={row.role_id}
                  onChange={(event) => update(index, { role_id: Number(event.target.value) })}
                >
                  {roles.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-md-5">
                {scoped && (
                  <select
                    multiple
                    className="form-select form-select-sm"
                    aria-label="Áreas donde puede crear (vacío = todas)"
                    value={row.area_ids.map(String)}
                    onChange={(event) =>
                      update(index, { area_ids: [...event.target.selectedOptions].map((option) => Number(option.value)) })
                    }
                    size={Math.min(4, areas.length || 1)}
                  >
                    {areas.map((area) => (
                      <option key={area.id} value={area.id}>
                        {area.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <div className="col-md-1">
                <button
                  type="button"
                  className="btn btn-outline-danger btn-sm"
                  aria-label={`Quitar rol en ${company?.short_name}`}
                  onClick={() => setRows(rows.filter((_, i) => i !== index))}
                >
                  ×
                </button>
              </div>
            </div>
          );
        })}
        {canEdit && (
          <div className="d-flex gap-2 mt-2">
            {available.length > 0 && roles.length > 0 && (
              <select
                className="form-select form-select-sm w-auto"
                aria-label="Agregar empresa"
                value=""
                onChange={(event) =>
                  setRows([...rows, { company_id: Number(event.target.value), role_id: roles[0].id, area_ids: [] }])
                }
              >
                <option value="">Agregar empresa…</option>
                {available.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.short_name}
                  </option>
                ))}
              </select>
            )}
            <button type="button" className="btn btn-outline-primary btn-sm" onClick={save}>
              Guardar roles por empresa
            </button>
          </div>
        )}
      </fieldset>
    </section>
  );
}
